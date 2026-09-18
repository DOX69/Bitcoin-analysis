from datetime import date, datetime, timedelta, timezone
import json
import sys

import pytest

from forecast import cloud_research as cloud
from forecast import prospective_research as local
from forecast.development_cron import due
from forecast.storage_artifacts import ArtifactRepository
from forecast.test_backups import Objects


@pytest.mark.parametrize(
    "day,utc_hour",
    [("2026-09-14", 5), ("2026-12-14", 6), ("2026-03-29", 5), ("2026-10-25", 6)],
)
def test_schedule_runs_only_at_seven_paris_including_dst_changes(day, utc_hour):
    for hour in (5, 6):
        instant = datetime.fromisoformat(day).replace(hour=hour, tzinfo=timezone.utc)
        assert due(instant) is (hour == utc_hour)


def test_manual_run_uses_existing_ingestion_but_still_refuses_production(monkeypatch):
    from forecast import development_cron
    from raw_ingest import orchestrator

    calls = []
    monkeypatch.setattr(sys, "argv", ["development_cron", "--run-now"])
    monkeypatch.setattr(development_cron, "due", lambda _: False)
    monkeypatch.setattr(orchestrator, "main", lambda: calls.append("ingestion"))
    monkeypatch.setenv("RAILWAY_ENVIRONMENT_NAME", "Development")
    development_cron.main()
    assert calls == ["ingestion"]
    monkeypatch.setenv("RAILWAY_ENVIRONMENT_NAME", "production")
    with pytest.raises(ValueError, match="Development"):
        development_cron.main()
    assert calls == ["ingestion"]


def test_cloud_restart_reuses_emission_and_restores_from_independent_objects(
    monkeypatch, tmp_path
):
    start = date(2024, 1, 1)
    daily = [
        {"date": (start + timedelta(days=i)).isoformat(), "close": 100.0}
        for i in range(140 * 7)
    ]
    now = datetime.combine(
        start + timedelta(weeks=140), datetime.min.time(), timezone.utc
    )
    distribution = [[-2, -1, 0, 1, 2]] * 52
    weekly = cloud.b.aggregate_daily_rows(daily)
    legacy = local.make_emission(
        weekly[:-1], distribution, now - timedelta(weeks=1), evidence="prospective"
    )
    monkeypatch.setattr(local, "frozen_distribution", lambda _: distribution)
    monkeypatch.setattr(local, "read_legacy_emission", lambda *args: legacy)
    source = ArtifactRepository(Objects(), "source")
    backup = ArtifactRepository(Objects(), "backup")
    first = cloud.collect(source, backup, tmp_path, daily, now)
    assert first["emissions"] == 2 and first["independent_copy_verified"]
    emission_keys = cloud.keys(source, cloud.PREFIX + "/emissions")
    assert len(emission_keys) == 1
    original = source.client.objects[emission_keys[0]]
    # A fresh container can read only the backup and reconstruct the same emission.
    restored = cloud.load_emissions(backup, source, distribution)
    assert len(restored) == 1
    again = cloud.collect(source, backup, tmp_path, daily, now + timedelta(days=1))
    assert again["emissions"] == 2
    assert source.client.objects[emission_keys[0]] == original
    assert source.client.objects == backup.client.objects
    source.client.objects[json.loads(original)["snapshot_key"]] = b"[]"
    with pytest.raises(ValueError, match="snapshot changed"):
        cloud.load_emissions(source, backup, distribution)


def test_research_hook_is_bounded_and_does_not_install_packages(monkeypatch):
    from raw_ingest import orchestrator
    from forecast import pipeline

    monkeypatch.delenv("FORECAST_RESEARCH_CONFIG", raising=False)
    assert orchestrator.run_forecast_research() == {"status": "disabled"}
    monkeypatch.setenv("FORECAST_RESEARCH_CONFIG", "/app/config/research.json")
    calls = []

    def supervise(command, log, **limits):
        calls.append((command, limits))
        log.write_text(
            json.dumps(
                {
                    "status": "completed",
                    "emissions": 1,
                    "mature_points": 0,
                    "validation_status": "insufficient_evidence",
                    "report_key": cloud.PREFIX + "/reports/example.json",
                    "report_sha256": "a" * 64,
                    "independent_copy_verified": True,
                }
            )
        )
        return {}

    monkeypatch.setattr(pipeline, "supervise", supervise)
    result = orchestrator.run_forecast_research()
    assert result["independent_copy_verified"]
    assert result["validation_status"] == "insufficient_evidence"
    assert result["report_sha256"] == "a" * 64
    assert "--no-sync" in calls[0][0]
    assert calls[0][1] == {"seconds": 300, "rss_bytes": 4 * 1024**3}
