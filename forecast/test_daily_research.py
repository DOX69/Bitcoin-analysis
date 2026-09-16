from datetime import date, datetime, timedelta, timezone
import json

import numpy as np
import pytest

from forecast import daily_research as daily
from forecast import daily_cloud as cloud
from forecast.benchmark import _wis
from forecast.storage_artifacts import ArtifactRepository
from forecast.test_backups import Objects


def test_direct_ridge_uses_only_mature_labels_and_past_normalization():
    logs = np.log(100 + np.arange(1800) / 10 + np.sin(np.arange(1800)))
    sundays = np.arange(6, len(logs), 7)
    before = daily.ridge(logs, daily.features(logs), 1500, sundays)
    logs[1501:] += 4
    after = daily.ridge(logs, daily.features(logs), 1500, sundays)
    np.testing.assert_array_equal(before, after)
    assert len(before) == 365


def test_calibration_does_not_read_future_realizations_or_forecasts():
    logs = np.log(100 + np.arange(2200))
    raw = {j: np.repeat(logs[j], 365) for j in range(0, 2200, 7)}
    origin = 1750
    expected = daily.calibrated(logs, origin, raw, naive=True)
    logs[origin + 1 :] += 5
    raw.update({j: np.repeat(9, 365) for j in raw if j > origin})
    np.testing.assert_array_equal(
        expected, daily.calibrated(logs, origin, raw, naive=True)
    )
    np.testing.assert_allclose(expected[:, 2], np.exp(logs[origin]))


def test_daily_holt_keeps_constant_history_constant():
    np.testing.assert_allclose(np.exp(daily.holt(np.repeat(123.0, 728))), 123.0)


def test_scores_match_scalar_proper_interval_score():
    predictions = np.array([[[70, 80, 100, 120, 130], [90, 100, 110, 120, 150]]])
    actual = [[140, 110]]
    score = daily.scores(predictions, actual)
    assert score["per_horizon"][0]["wis"] == pytest.approx(_wis(140, predictions[0, 0]))
    assert score["aggregate"]["mae"] == 20
    assert score["per_horizon"][0]["coverage_80"] == 0


def rows():
    start = date(2021, 1, 1)
    return [
        {
            "date": str(start + timedelta(days=i)),
            "close": 100.0,
            "observed_at": "2026-09-15T12:00:00+00:00",
        }
        for i in range((date(2026, 9, 15) - start).days + 1)
    ]


def test_initial_emission_uses_real_clock_and_starts_today(monkeypatch):
    data = rows()
    now = datetime(2026, 9, 16, 8, tzinfo=timezone.utc)
    monkeypatch.setattr(daily, "raw_forecasts", lambda *a, **kw: {"ridge": {}})
    monkeypatch.setattr(
        daily, "calibrated", lambda *a: np.tile([80, 90, 100, 110, 120], (365, 1))
    )
    result = daily.emission(data, now, "ridge")
    assert result["points"][0]["target_date"] == "2026-09-16"
    assert result["points"][-1]["target_date"] == "2027-09-15"
    assert result["created_at"] == now.isoformat()
    with pytest.raises(ValueError, match="Latest completed"):
        daily.emission(data[:-1], now, "ridge")
    data[-1]["observed_at"] = "2026-09-17T00:00:00+00:00"
    with pytest.raises(ValueError, match="Future ingestion"):
        daily.emission(data, now, "ridge")


def test_missing_or_duplicate_daily_dates_are_rejected():
    data = rows()
    with pytest.raises(ValueError, match="gap free"):
        daily.observations(data[:500] + data[501:])
    with pytest.raises(ValueError, match="gap free"):
        daily.observations(data[:500] + data[499:])


def test_cloud_monday_only_and_restart_repairs_backup_without_refitting(monkeypatch):
    objects = Objects()
    source = ArtifactRepository(objects, "primary")
    backup_objects = Objects()
    backup = ArtifactRepository(backup_objects, "backup")
    now = datetime(2026, 9, 16, 8, tzinfo=timezone.utc)
    assert cloud.collect(source, backup, [], now)["status"] == "outside_monday"
    document = {"created_at": now.isoformat()}
    monkeypatch.setattr(daily, "emission", lambda *a: document)
    result = cloud.collect(source, backup, rows(), now, bootstrap=True)
    assert result["independent_copy_verified"] is True
    backup_objects.objects.clear()
    monkeypatch.setattr(
        daily, "emission", lambda *a: pytest.fail("Restart must reuse issuance")
    )
    repeated = cloud.collect(source, backup, [], now, bootstrap=True)
    assert repeated["status"] == "already_emitted"
    assert (
        backup_objects.objects[result["report_key"]]
        == objects.objects[result["report_key"]]
    )


def test_daily_selection_matches_frozen_recipe():
    assert cloud.selection()["model_manifest_sha256"] == daily.MODEL_MANIFEST
    assert cloud.selection()["production_ready"] is False


def test_orchestrator_supervises_daily_worker_without_changing_legacy(monkeypatch):
    from raw_ingest import orchestrator
    from forecast import pipeline

    calls = []

    def supervise(command, log_path, **limits):
        calls.append((command, limits))
        log_path.write_text('{"status":"outside_monday","mature_points":2}')
        return {}

    monkeypatch.setenv("FORECAST_RESEARCH_CONFIG", "forecast/development-config.json")
    monkeypatch.setattr(pipeline, "supervise", supervise)
    assert orchestrator.run_daily_forecast_research()["mature_points"] == 2
    orchestrator.run_forecast_research()
    assert "forecast.daily_cloud" in calls[0][0]
    assert "forecast.cloud_research" in calls[1][0]
    assert calls[0][1] == {"seconds": 300, "rss_bytes": 4 * 1024**3}


def test_prospective_scoring_waits_for_completed_targets_and_preserves_emission():
    source, backup = ArtifactRepository(Objects(), "primary"), ArtifactRepository(
        Objects(), "backup"
    )
    data = rows()
    now = datetime(2026, 9, 16, 8, tzinfo=timezone.utc)
    document = {
        "model_manifest_sha256": daily.MODEL_MANIFEST,
        "created_at": "2026-09-14T05:00:00+00:00",
        "origin_close": 90,
        "points": [
            {
                "horizon_days": h,
                "target_date": str(date(2026, 9, 13) + timedelta(days=h)),
                "USD": [80, 90, 100, 110, 120],
            }
            for h in range(1, 366)
        ],
    }
    content = daily.encode({"emission": document})
    key = daily.PREFIX + "/emissions/2026-09-13.json"
    source.client.objects[key] = content
    result = cloud.score_existing(source, backup, data, now)
    assert result["mature_points"] == 2
    report = json.loads(source.client.objects[result["score_report_key"]])
    assert report["per_horizon"][0]["mae"] == 0
    assert report["per_horizon"][0]["naive_mae"] == 10
    assert report["per_horizon"][2]["origins"] == 0
    assert source.client.objects[key] == backup.client.objects[key] == content
