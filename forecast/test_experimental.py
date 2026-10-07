from datetime import date, datetime, timezone
import json
from pathlib import Path
from unittest.mock import Mock

import pytest

from forecast import candidate_cloud as cloud
from forecast import experimental
from forecast.backups import digest, put_verified
from forecast.storage_artifacts import ArtifactRepository
from forecast.test_backups import Objects
from forecast.test_candidate_cloud import Candidate, weekly_rows


def emission():
    return cloud.make_emission(
        weekly_rows(), Candidate(), "a" * 64, datetime(2026, 9, 21, tzinfo=timezone.utc)
    )


def test_calendar_months_clamp_month_end_and_keep_original_quantiles():
    assert experimental.six_month_end(date(2026, 8, 31)) == date(2027, 2, 28)
    document = emission()
    fx = {
        "EUR": {"date": "2026-09-18", "rate": 0.9},
        "CHF": {"date": "2026-09-18", "rate": 0.8},
    }
    public = experimental.public_emission(document, fx)
    assert public["emissionDate"] == "2026-09-21"
    assert public["horizonEnd"] == "2027-03-21"
    assert len(public["points"]) == 26
    assert public["points"][-1]["targetDate"] == "2027-03-21"
    assert public["points"][0]["USD"] == document["points"][0]["USD"]
    assert public["points"][0]["EUR"] == [v * 0.9 for v in document["points"][0]["USD"]]


def test_future_fx_is_refused():
    fx = {
        "EUR": {"date": "2026-09-22", "rate": 0.9},
        "CHF": {"date": "2026-09-18", "rate": 0.8},
    }
    with pytest.raises(ValueError, match="FX"):
        experimental.public_emission(emission(), fx)


def test_failed_independent_copy_prevents_database_publication(monkeypatch):
    source = ArtifactRepository(Objects(), "source")
    destination = ArtifactRepository(Objects(), "destination")
    backup = ArtifactRepository(Objects(), "backup")
    document = emission()
    snapshot = b"[]"
    key = cloud.PREFIX + "/snapshots/" + digest(snapshot) + ".json"
    put_verified(source, key, snapshot)
    put_verified(
        source,
        cloud.PREFIX + "/emissions/" + document["origin_week"] + ".json",
        json.dumps(
            {
                "emission": document,
                "snapshot_key": key,
                "snapshot_sha256": digest(snapshot),
            }
        ).encode(),
    )
    connection = Mock()
    connection.execute.return_value.fetchone.side_effect = [(True,), None]
    monkeypatch.setattr(experimental, "mirror_model", lambda *_: None)
    monkeypatch.setattr(
        experimental.DatabaseSource,
        "fx",
        lambda *_: {
            "EUR": {"date": "2026-09-18", "rate": 0.9},
            "CHF": {"date": "2026-09-18", "rate": 0.8},
        },
    )
    real_put = experimental.put_verified

    def put(repository, *args):
        if repository is backup:
            raise ValueError("backup unavailable")
        return real_put(repository, *args)

    monkeypatch.setattr(experimental, "put_verified", put)
    with pytest.raises(ValueError, match="backup"):
        experimental.publish(
            connection,
            source,
            destination,
            backup,
            [document],
            "a" * 64,
            datetime(2026, 9, 23, tzinfo=timezone.utc),
        )
    assert not any(
        "INSERT" in call.args[0] for call in connection.execute.call_args_list
    )


def test_experimental_migration_replay_preserves_rows():
    import os
    import psycopg
    from psycopg.conninfo import conninfo_to_dict

    url = os.environ.get("FORECAST_TEST_DATABASE_URL")
    if not url:
        pytest.skip("Isolated PostgreSQL fixture required")
    info = conninfo_to_dict(url)
    assert info["dbname"] == "forecast_test" and info["host"] in (
        "localhost",
        "127.0.0.1",
    )
    migration = (
        Path(__file__).parent / "migrations/003_experimental.up.sql"
    ).read_text()
    with psycopg.connect(url, autocommit=True) as connection:
        connection.execute(migration)
        connection.execute(
            "INSERT INTO forecast_experimental.emissions VALUES ('2026-09-14','2026-09-21',%s,%s,%s,'{}',now()) ON CONFLICT DO NOTHING",
            ("a" * 64,) * 3,
        )
        connection.execute(migration)
        assert (
            connection.execute(
                "SELECT count(*) FROM forecast_experimental.emissions"
            ).fetchone()[0]
            == 1
        )
        connection.execute(
            "DELETE FROM forecast_experimental.emissions WHERE origin_week='2026-09-14'"
        )
