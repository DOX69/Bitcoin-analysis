import copy
from datetime import date, datetime, timedelta, timezone
import pytest

from forecast.storage import validate_emission


def test_postgres_publication_and_immutable_replay():
    import os
    from pathlib import Path
    import psycopg
    from psycopg.conninfo import conninfo_to_dict
    from forecast.storage import ForecastStore

    url = os.environ.get("FORECAST_TEST_DATABASE_URL")
    if not url:
        pytest.skip(
            "Set FORECAST_TEST_DATABASE_URL to isolated localhost forecast_test"
        )
    info = conninfo_to_dict(url)
    assert (
        info["host"] in ("127.0.0.1", "localhost") and info["dbname"] == "forecast_test"
    )
    with psycopg.connect(url, autocommit=True) as conn:
        conn.execute("DROP SCHEMA IF EXISTS forecast CASCADE")
        conn.execute(Path("forecast/migrations/001_storage.up.sql").read_text())
        store = ForecastStore(conn)
        from forecast.artifacts import FEATURES

        manifest = dict(
            schema_version=1,
            features=FEATURES,
            recalibration=None,
            quantiles=[0.1, 0.25, 0.5, 0.75, 0.9],
            horizons=list(range(1, 53)),
            files={"state.json": "test"},
        )
        store.register_version("a", manifest, "development/a")
        store.register_version("b", manifest, "development/b")
        store.activate_version("a", lambda *_: None)
        with pytest.raises(ValueError):
            store.activate_version(
                "b", lambda *_: (_ for _ in ()).throw(ValueError("bad artifact"))
            )
        assert (
            conn.execute("SELECT active_version FROM forecast.publication").fetchone()[
                0
            ]
            == "a"
        )
        now = datetime(2026, 9, 7, tzinfo=timezone.utc)
        identifier = store.publish_emission("a", emission(), now)
        assert store.publish_emission("a", emission(), now) == identifier
        store.activate_version("b", lambda *_: None)
        assert store.publish_emission("b", emission(), now) == identifier
        store.rollback(lambda *_: None)
        assert (
            conn.execute("SELECT active_version FROM forecast.publication").fetchone()[
                0
            ]
            == "a"
        )
        conn.execute("UPDATE forecast.versions SET withdrawn=true WHERE id='b'")
        with pytest.raises(ValueError):
            store.rollback(lambda *_: None)
        conflicting = copy.deepcopy(emission())
        conflicting["points"][0]["USD"] = [2, 3, 4, 5, 6]
        with pytest.raises(ValueError):
            store.publish_emission("a", conflicting, now)
        with pytest.raises(psycopg.Error):
            conn.execute("UPDATE forecast.versions SET manifest='{}'")
        conn.execute("UPDATE forecast.versions SET withdrawn=true WHERE id='a'")
        with pytest.raises(ValueError):
            store.publish_emission("a", emission(), now)
        assert store.record_score(identifier, 1, "source:revision1", 3, {"mae": 0})
        assert not store.record_score(identifier, 1, "source:revision1", 3, {"mae": 0})
        assert store.record_score(identifier, 1, "source:revision2", 4, {"mae": 1})
        with pytest.raises(psycopg.Error):
            conn.execute("UPDATE forecast.emissions SET payload='{}'")
        conn.execute("UPDATE forecast.emissions SET status='invalidated'")
        conn.execute(Path("forecast/migrations/001_storage.down.sql").read_text())


def emission():
    return {
        "emission_date": "2026-09-07",
        "origin_week": "2026-08-31",
        "quantiles": [0.1, 0.25, 0.5, 0.75, 0.9],
        "fx": {},
        "points": [
            {
                "horizon_weeks": h,
                "target_date": (date(2026, 9, 6) + timedelta(weeks=h)).isoformat(),
                "USD": [1, 2, 3, 4, 5],
            }
            for h in range(1, 53)
        ],
    }


def test_emission_contract():
    validate_emission(emission(), datetime(2026, 9, 7, tzinfo=timezone.utc))


@pytest.mark.parametrize("change", ["crossed", "target", "fx", "backdate", "missing"])
def test_rejects_invalid_emission(change):
    value = copy.deepcopy(emission())
    if change == "crossed":
        value["points"][0]["USD"] = [5, 4, 3, 2, 1]
    if change == "target":
        value["points"][0]["target_date"] = "2026-09-12"
    if change == "fx":
        value["fx"] = {"EUR": {"date": "2026-09-08", "rate": 0.9}}
    if change == "backdate":
        value["emission_date"] = "2026-09-06"
    if change == "missing":
        value["points"].pop()
    with pytest.raises(ValueError):
        validate_emission(value, datetime(2026, 9, 7, tzinfo=timezone.utc))
