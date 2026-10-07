from datetime import datetime, timezone
import json
import sys

import pytest

from forecast import cloud_research as cloud
from forecast.development_cron import due


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
                    "report_key": "development/research/lightgbm-v1/reports/example.json",
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
    assert "forecast.candidate_cloud" in calls[0][0]
    assert "--no-sync" in calls[0][0]
    assert calls[0][1] == {"seconds": 300, "rss_bytes": 4 * 1024**3}


def test_configured_research_candidate_uses_isolated_collector(monkeypatch, tmp_path):
    from forecast import candidate_cloud

    config = tmp_path / "research.json"
    config.write_text(json.dumps({"research_model": "lightgbm_quantile"}))
    calls = []
    monkeypatch.setattr(sys, "argv", ["cloud", "--config", str(config)])
    monkeypatch.setattr(candidate_cloud, "main", lambda: calls.append("candidate"))

    cloud.main()

    assert calls == ["candidate"]
