import json
import math
import sys
from datetime import date, timedelta

import numpy as np
import pytest

from forecast import benchmark as b


def series(count=360):
    return [
        {
            "date": (date(2019, 1, 7) + timedelta(weeks=i)).isoformat(),
            "close": 100 * math.exp(i * 0.002 + 0.08 * math.sin(i / 5)),
        }
        for i in range(count)
    ]


def test_runner_never_uses_residual_calibration(monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail("Residual calibration is forbidden in this cycle")

    monkeypatch.setattr(b.ResidualQuantileCalibrator, "fit", forbidden)
    closes = [r["close"] for r in series()]
    result = b._candidate_measurement(
        b.GaussianRandomWalkCandidate(), closes, b.split_series(series())
    )
    assert result.metrics["mae"] > 0


def test_last_close_reference_is_evaluation_only():
    from forecast.artifacts import CANDIDATES

    assert set(CANDIDATES) == {"gaussian_random_walk", "lightgbm_quantile"}
    assert b.last_close_reference([100.0, 110.0], 1) == [[110.0] * 5] * 52


def test_wis_uses_accepted_interval_weights():
    metrics, horizons = b._score([[[1, 2, 3, 4, 5]] * 52], [[6] * 52])
    # IS50 = 2 + 4*2; IS80 = 4 + 10*1.
    assert metrics.get("wis") == pytest.approx((0.5 * 3 + 0.25 * 10 + 0.1 * 14) / 2.5)
    assert len(horizons) == 52


def test_lightgbm_labels_are_mature_log_returns(monkeypatch):
    import lightgbm

    captured = []

    class Regressor:
        def __init__(self, **kwargs):
            pass

        def fit(self, x, y):
            captured.append((x.copy(), y.copy()))

    monkeypatch.setattr(lightgbm, "LGBMRegressor", Regressor)
    closes = [r["close"] for r in series()]
    b.LightGBMQuantileCandidate().fit(closes, 150)
    for h in (1, 52):
        x, y = captured[(h - 1) * 5]
        origins = list(range(52, 150 - h))
        np.testing.assert_allclose(
            y, [math.log(closes[t + h] / closes[t]) for t in origins]
        )
        assert origins[-1] + h == 149
        np.testing.assert_allclose(x[-1], b._feature_row(closes[:150], origins[-1]))


def test_lightgbm_reconstructs_prices_and_orders_quantiles():
    class Model:
        def __init__(self, value):
            self.value = value

        def predict(self, features):
            return [self.value]

    candidate = b.LightGBMQuantileCandidate()
    candidate.models = [[Model(v) for v in (0.2, -0.1, 0, 0.1, -0.2)]] * 52
    closes = [r["close"] for r in series()]
    result = candidate.predict(closes, 100)
    np.testing.assert_allclose(
        result[0], [closes[100] * math.exp(v) for v in (-0.2, -0.1, 0, 0.1, 0.2)]
    )


def test_features_ignore_future_observations():
    closes = [r["close"] for r in series()]
    assert b._feature_row(closes, 100) == b._feature_row(closes[:101], 100)


@pytest.mark.parametrize(
    "defect", ["gap", "duplicate", "negative", "nan", "not_monday"]
)
def test_snapshot_validation(defect):
    from forecast.pipeline import validate_weekly

    rows = series()
    if defect == "gap":
        rows.pop(5)
    elif defect == "duplicate":
        rows[5] = rows[4]
    elif defect == "not_monday":
        rows[0]["date"] = "2019-01-08"
    else:
        rows[5]["close"] = -1 if defect == "negative" else float("nan")
    with pytest.raises(ValueError):
        validate_weekly(rows)


def test_manifest_is_frozen_before_execution_and_rejects_reuse(tmp_path):
    from forecast.pipeline import prepare_run

    snapshot = tmp_path / "input.csv"
    b._write_weekly_csv(snapshot, series())
    manifest = prepare_run(snapshot, tmp_path / "run")
    assert manifest["recalibration"] is None
    assert manifest["reload_tolerance"] == {"rtol": 1e-10, "atol": 1e-8}
    assert manifest["recipes"] == ["gaussian_random_walk", "lightgbm_quantile"]
    assert manifest["reference"]["scope"] == "evaluation_only"
    assert len(manifest["folds"]) == 2
    assert (tmp_path / "run/manifest.json").exists()
    assert (tmp_path / "run/source/forecast/pipeline.py").exists()
    for fold in manifest["folds"]:
        assert fold["train_end"] <= fold["origin_start"]
        assert fold["origin_end"] - 1 + 52 < len(series())
    with pytest.raises(FileExistsError):
        prepare_run(snapshot, tmp_path / "run")


@pytest.mark.parametrize("kind", ["gaussian_random_walk", "lightgbm_quantile"])
def test_artifacts_reload_and_detect_corruption(tmp_path, kind):
    from forecast.artifacts import save_model, load_model

    candidates = {
        c.name: c
        for c in [
            b.GaussianRandomWalkCandidate(),
            b.LightGBMQuantileCandidate(),
        ]
    }
    candidate = candidates[kind]
    closes = [r["close"] for r in series(160)]
    candidate.fit(closes, len(closes))
    manifest = save_model(candidate, tmp_path / "model", {"snapshot_sha256": "test"})
    loaded = load_model(tmp_path / "model")
    np.testing.assert_allclose(
        loaded.predict(closes, 159),
        candidate.predict(closes, 159),
        rtol=1e-10,
        atol=1e-8,
    )
    assert manifest["recalibration"] is None
    first = next(iter(manifest["files"]))
    (tmp_path / "model" / first).write_text("corrupt")
    with pytest.raises(ValueError, match="integrity"):
        load_model(tmp_path / "model")


def test_emission_uses_sunday_targets_and_known_constant_fx(tmp_path):
    from forecast.artifacts import emit_forecast

    candidate = b.GaussianRandomWalkCandidate()
    rows = series(160)
    candidate.fit([r["close"] for r in rows], 160)
    cutoff = date.fromisoformat(rows[-1]["date"]) + timedelta(days=7)
    fx = {
        "EUR": {"date": cutoff.isoformat(), "rate": 0.9},
        "CHF": {"date": cutoff.isoformat(), "rate": 0.8},
    }
    result = emit_forecast(candidate, rows, cutoff.isoformat(), fx)
    assert len(result["points"]) == 52
    assert (
        result["points"][0]["target_date"] == (cutoff + timedelta(days=6)).isoformat()
    )
    assert (
        result["points"][-1]["target_date"]
        == (cutoff + timedelta(days=363)).isoformat()
    )
    assert result["points"][-1]["EUR"][2] == pytest.approx(
        result["points"][-1]["USD"][2] * 0.9
    )
    fx["EUR"]["date"] = (cutoff + timedelta(days=1)).isoformat()
    with pytest.raises(ValueError, match="FX"):
        emit_forecast(candidate, rows, cutoff.isoformat(), fx)


def test_worker_reports_both_periods_without_promoting(tmp_path, monkeypatch):
    from forecast.pipeline import prepare_run, run_candidate

    def forbidden(*args, **kwargs):
        pytest.fail("The current pipeline must not fit a calibrator")

    monkeypatch.setattr(b.ResidualQuantileCalibrator, "fit", forbidden)

    snapshot = tmp_path / "input.csv"
    b._write_weekly_csv(snapshot, series())
    prepare_run(snapshot, tmp_path / "run")
    result = run_candidate(tmp_path / "run", "gaussian_random_walk")
    assert result["recalibration"] is None
    assert len(result["per_period"]) == 2
    assert len(result["per_horizon"]) == 52
    assert len(result["reference_per_horizon"]) == 52
    assert result["reference_metrics"]["mae"] > 0
    assert result["artifact_bytes"] > 0
    assert result["reload_verified"]
    assert result["promotion"] == "not_evaluated_prospective_confirmation_required"
    assert all(len(period["per_horizon"]) == 52 for period in result["per_period"])


@pytest.mark.parametrize("budget", ["time", "memory"])
def test_supervisor_stops_only_its_worker_on_exceeded_budget(tmp_path, budget):
    from forecast.pipeline import supervise

    kwargs = {"seconds": 0.05} if budget == "time" else {"rss_bytes": 1}
    with pytest.raises(RuntimeError, match="budget"):
        supervise(
            [sys.executable, "-c", "import time; time.sleep(10)"],
            tmp_path / "worker.log",
            **kwargs,
        )


def test_modified_snapshot_is_rejected_before_training(tmp_path):
    from forecast.pipeline import prepare_run, run_candidate

    snapshot = tmp_path / "input.csv"
    b._write_weekly_csv(snapshot, series())
    prepare_run(snapshot, tmp_path / "run")
    (tmp_path / "run/snapshot.csv").write_text("modified")
    with pytest.raises(ValueError, match="integrity"):
        run_candidate(tmp_path / "run", "gaussian_random_walk")
    assert not (tmp_path / "run/gaussian_random_walk").exists()


def test_complete_cycle_runs_two_workers_and_cannot_retry(tmp_path):
    from forecast.pipeline import prepare_run, execute_run

    snapshot = tmp_path / "input.csv"
    b._write_weekly_csv(snapshot, series())
    directory = tmp_path / "run"
    prepare_run(snapshot, directory)
    report = execute_run(directory)
    assert len(report["candidates"]) == 2
    assert report["reference"]["scope"] == "evaluation_only"
    for result in report["candidates"]:
        assert result["resources"]["peak_rss_bytes"] > 0
        assert result["publishable"] is False
        assert len(result["per_horizon"]) == 52
        assert len(result["reference_per_horizon"]) == 52
        assert result["artifact_bytes"] == sum(
            p.stat().st_size
            for p in (directory / result["name"]).rglob("*")
            if p.is_file()
        )
    inventory = json.loads((directory / "inventory.json").read_text())
    assert inventory["manifest.json"]["sha256"] == b._file_sha256(
        directory / "manifest.json"
    )
    with pytest.raises(FileExistsError):
        execute_run(directory)


def test_separate_cycles_cannot_run_concurrently(tmp_path, monkeypatch):
    from forecast import pipeline

    assert hasattr(pipeline, "RUN_LOCK"), "A repository-wide execution lock is required"
    lock = tmp_path / "running.lock"
    monkeypatch.setattr(pipeline, "RUN_LOCK", lock)
    lock.write_text("another active cycle")
    with pytest.raises(FileExistsError):
        pipeline.execute_run(tmp_path / "different-cycle")
    assert lock.read_text() == "another active cycle"


def test_supervisor_counts_memory_in_python_child_processes(tmp_path):
    import psutil
    from forecast.pipeline import supervise

    marker = tmp_path / "child.pid"
    child = (
        f"import time,os; from pathlib import Path; Path({str(marker)!r}).write_text(str(os.getpid())); "
        "data = bytearray(128*1024**2); time.sleep(.5)"
    )
    parent = f"import subprocess,sys; subprocess.run([sys.executable, '-c', {child!r}], check=True)"
    with pytest.raises(RuntimeError, match="RAM budget"):
        supervise(
            [sys.executable, "-c", parent],
            tmp_path / "tree.log",
            rss_bytes=100 * 1024**2,
        )
    assert not psutil.pid_exists(int(marker.read_text()))
