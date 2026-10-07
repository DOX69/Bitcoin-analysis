"""Software integration on synthetic data, never promotion evidence."""

from datetime import date, datetime, timedelta, timezone
import math
import os
from pathlib import Path

import psycopg
from psycopg.conninfo import conninfo_to_dict
import pytest

from forecast.artifacts import emit_forecast, load_model, save_model
from forecast.benchmark import GaussianRandomWalkCandidate
from forecast.storage import ForecastStore


def test_reloaded_model_to_immutable_postgres_emission(tmp_path):
    url = os.environ.get("FORECAST_INTEGRATION_DATABASE_URL")
    if not url:
        pytest.skip("Set FORECAST_INTEGRATION_DATABASE_URL to a local test database")
    info = conninfo_to_dict(url)
    assert info["host"] in ("localhost", "127.0.0.1")
    assert info["dbname"] == "forecast_integration_test"
    weekly = [
        {
            "date": (date(2024, 1, 1) + timedelta(weeks=i)).isoformat(),
            "close": 100 * math.exp(i * 0.002 + 0.08 * math.sin(i / 5)),
        }
        for i in range(140)
    ]
    closes = [row["close"] for row in weekly]
    candidate = GaussianRandomWalkCandidate()
    candidate.fit(closes, len(closes))
    directory = tmp_path / "model"
    manifest = save_model(candidate, directory, {"evidence": "fixture"})
    payload = emit_forecast(
        load_model(directory),
        weekly,
        "2026-09-07",
        {
            "EUR": {"date": "2026-09-04", "rate": 0.92},
            "CHF": {"date": "2026-09-04", "rate": 0.85},
        },
    )
    payload["evidence"] = "fixture"
    with psycopg.connect(url, autocommit=True) as connection:
        connection.execute("DROP SCHEMA IF EXISTS forecast CASCADE")
        connection.execute(Path("forecast/migrations/001_storage.up.sql").read_text())
        store = ForecastStore(connection)
        store.register_version("fixture", manifest, "development/fixture")
        store.activate_version("fixture", lambda *_: load_model(directory))
        now = datetime(2026, 9, 7, tzinfo=timezone.utc)
        identifier = store.publish_emission("fixture", payload, now)
        assert store.publish_emission("fixture", payload, now) == identifier
        stored = connection.execute(
            "SELECT payload FROM forecast.emissions WHERE id=%s", (identifier,)
        ).fetchone()[0]
        assert stored == payload
        assert len(stored["points"]) == 52
        assert stored["points"][-1]["target_date"] == "2027-09-05"
        for point in stored["points"]:
            assert point["EUR"] == pytest.approx([v * 0.92 for v in point["USD"]])
        assert (
            connection.execute("SELECT count(*) FROM forecast.emissions").fetchone()[0]
            == 1
        )
        connection.execute(Path("forecast/migrations/001_storage.down.sql").read_text())
