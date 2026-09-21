"""Frozen, sequential, resource-bounded evaluation of two forecast candidates."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import shutil
import subprocess
import sys
import tempfile
import time
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from forecast import benchmark as b
from forecast import evaluation
from forecast.artifacts import (
    CANDIDATES,
    FEATURES,
    RELOAD_TOLERANCE,
    dependencies,
    emit_forecast,
    save_model,
    validate_prediction,
    verify_reload,
    write_json,
)

LIMITS = {
    "cpu_count": 2,
    "rss_bytes": 4 * 1024**3,
    "seconds_per_recipe": 1800,
    "recipes": 2,
    "concurrency": 1,
    "retries": 0,
}
REFERENCE = {
    "name": "last_close_holdout_reference",
    "scope": "evaluation_only",
    "definition": "last observed close at each out-of-sample origin",
    "prospective": "origin_close compared with each later matured observation",
}
ROOT = Path(__file__).resolve().parents[1]
RUN_LOCK = Path(tempfile.gettempdir()) / (
    "forecast-" + hashlib.sha256(str(ROOT).encode()).hexdigest()[:16] + ".lock"
)


def validate_weekly(weekly):
    if not weekly:
        raise ValueError("Empty snapshot")
    previous = None
    for row in weekly:
        observed = date.fromisoformat(row["date"])
        close = float(row["close"])
        if (
            observed.weekday() != 0
            or not math.isfinite(close)
            or close <= 0
            or previous is not None
            and observed != previous + timedelta(weeks=1)
        ):
            raise ValueError(
                "Snapshot requires consecutive complete ISO weeks and positive finite closes"
            )
        previous = observed


def prepare_run(snapshot: Path, directory: Path, final_holdout: dict | None = None):
    weekly = b._read_weekly_csv(snapshot)
    validate_weekly(weekly)
    split = b.split_series(weekly)
    if final_holdout is not None:
        try:
            final_train_end = int(final_holdout["train_end"])
        except (KeyError, TypeError, ValueError) as error:
            raise ValueError("Final holdout requires a valid train_end") from error
        if not (split.calibration_end + b.MAX_HORIZON < final_train_end <= len(weekly)):
            raise ValueError("Final holdout leaves no mature second selection period")
        fold_ends = (
            (split.train_end, split.calibration_end),
            (split.calibration_end, final_train_end),
        )
    else:
        fold_ends = (
            (split.train_end, split.calibration_end),
            (split.calibration_end, len(weekly)),
        )
    folds = []
    for start, end in fold_ends:
        stop = end - 52
        if stop <= start:
            raise ValueError("Each evaluation period requires mature 52-week targets")
        folds.append(
            {
                "train_end": start,
                "origin_start": start,
                "origin_end": stop,
                "train_last_week": weekly[start - 1]["date"],
                "first_origin_week": weekly[start]["date"],
                "last_origin_week": weekly[stop - 1]["date"],
                "last_target_week": weekly[end - 1]["date"],
            }
        )
    selection_origin_end = max(fold["origin_end"] for fold in folds)
    if final_holdout is None:
        final_partition = evaluation.unavailable_final_holdout(
            "No untouched historical period was supplied; prospective evidence is required"
        )
    else:
        final_partition = evaluation.make_final_holdout(
            weekly,
            train_end=final_holdout["train_end"],
            origin_start=final_holdout["origin_start"],
            origin_end=final_holdout["origin_end"],
            horizon=b.MAX_HORIZON,
            selection_origin_end=selection_origin_end,
        )
    from lightgbm import LGBMRegressor

    manifest = {
        "schema_version": 1,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "snapshot_sha256": b._file_sha256(snapshot),
        "weekly_rows": len(weekly),
        "first_week": weekly[0]["date"],
        "last_week": weekly[-1]["date"],
        "week_label": "Monday UTC; observed close is the following Sunday",
        "target": "BTC/USD ISO Sunday close",
        "horizons": list(range(1, 53)),
        "quantiles": list(b.QUANTILES),
        "features": FEATURES,
        "recalibration": None,
        "recipes": list(CANDIDATES),
        "reference": REFERENCE,
        "baseline": {
            "central": REFERENCE,
            "probabilistic": {
                "name": "probabilistic_last_close_reference",
                "scope": "evaluation_only",
                "definition": "zero-drift lognormal random-walk bands; population sigma of returns known through each origin; no future observations",
                "quantiles": list(b.QUANTILES),
            },
        },
        "lightgbm_target": "log(P[t+h]/P[t])",
        "lightgbm_parameters_by_quantile": {
            str(q): LGBMRegressor(alpha=q, **b.LIGHTGBM_PARAMS).get_params()
            for q in b.QUANTILES
        },
        "gaussian": "training log-return population mean and std; drift retained; sigma floor 1e-9",
        "folds": folds,
        "final_fit_train_end": len(weekly),
        "reload_tolerance": RELOAD_TOLERANCE,
        "dependencies": dependencies(),
        "limits": LIMITS,
        "lock_sha256": b._file_sha256(ROOT / "uv.lock"),
        "source_sha256": {
            name: b._file_sha256(ROOT / "forecast" / name)
            for name in ("benchmark.py", "artifacts.py", "evaluation.py", "pipeline.py")
        },
        "wis": "(0.5*abs_error_median + 0.25*IS_0.5 + 0.10*IS_0.2)/2.5",
        "first_version_gates": {
            "mae_vs_holdout_reference_max": 1.05,
            "coverage_50": [0.4, 0.6],
            "coverage_80": [0.7, 0.9],
        },
        "evidence": "exploratory; overlapping targets; prospective confirmation required",
        "period_policy": "two expanding training cuts at floor(0.6*n), floor(0.8*n); no calibration; all 52 labels mature inside each evaluation period",
        "dependence_policy": "paired errors retained by origin; contiguous blocks of h origins for horizon h; blocks do not establish independence",
        "partitions": {
            "selection": {
                "name": "selection",
                "status": "available",
                "folds": folds,
                "read_before_final_holdout": True,
                "historical_research": True,
            },
            "final_holdout": {
                **final_partition,
                "snapshot_sha256": b._file_sha256(snapshot),
                "scoring_rules": evaluation.SCORING_RULES,
            },
            "prospective": {
                "name": "prospective",
                "status": "separate_immutable_emissions",
                "maturity": "weekly targets are scoreable after Monday 00:00 UTC; daily targets after the completed UTC day",
                "publishable": False,
            },
        },
    }
    directory.mkdir(parents=True, exist_ok=False)
    shutil.copyfile(snapshot, directory / "snapshot.csv")
    shutil.copyfile(ROOT / "uv.lock", directory / "uv.lock")
    source_directory = directory / "source" / "forecast"
    source_directory.mkdir(parents=True)
    for name in (*manifest["source_sha256"], "__init__.py"):
        shutil.copyfile(ROOT / "forecast" / name, source_directory / name)
    write_json(directory / "manifest.json", manifest)
    (directory / "manifest.sha256").write_text(
        b._file_sha256(directory / "manifest.json"), encoding="ascii"
    )
    return manifest


def read_manifest(directory):
    path = directory / "manifest.json"
    if b._file_sha256(path) != (directory / "manifest.sha256").read_text(
        encoding="ascii"
    ):
        raise ValueError("Frozen manifest integrity failure")
    manifest = json.loads(path.read_text(encoding="utf-8"))
    if manifest["limits"] != LIMITS or manifest["recalibration"] is not None:
        raise ValueError("Unsupported run contract")
    partitions = manifest.get("partitions")
    if not isinstance(partitions, dict) or set(partitions) != {
        "selection",
        "final_holdout",
        "prospective",
    }:
        raise ValueError(
            "Run manifest must name selection, final_holdout and prospective"
        )
    selection = partitions["selection"]
    if (
        selection.get("name") != "selection"
        or selection.get("historical_research") is not True
    ):
        raise ValueError("Selection partition is not explicitly marked as research")
    selection_end = max(fold["origin_end"] for fold in manifest["folds"])
    evaluation.validate_final_holdout(
        partitions["final_holdout"],
        row_count=manifest["weekly_rows"],
        horizon=b.MAX_HORIZON,
        selection_origin_end=selection_end,
    )
    if partitions["final_holdout"].get("snapshot_sha256") not in (
        None,
        manifest["snapshot_sha256"],
    ):
        raise ValueError("Final holdout snapshot differs from the frozen snapshot")
    if partitions["prospective"].get("name") != "prospective":
        raise ValueError("Prospective evidence partition is missing")
    for filename, digest in {
        "snapshot.csv": manifest["snapshot_sha256"],
        "uv.lock": manifest["lock_sha256"],
    }.items():
        if b._file_sha256(directory / filename) != digest:
            raise ValueError(f"Frozen input integrity failure: {filename}")
    if manifest["dependencies"] != dependencies():
        raise ValueError("Frozen dependencies changed")
    for name, digest in manifest["source_sha256"].items():
        if (
            b._file_sha256(ROOT / "forecast" / name) != digest
            or b._file_sha256(directory / "source" / "forecast" / name) != digest
        ):
            raise ValueError(f"Frozen source changed: {name}")
    return manifest


def dependence_blocks(weekly, origins, predictions, actuals):
    result = []
    for h in range(1, 53):
        for start in range(0, len(origins), h):
            indices = range(start, min(start + h, len(origins)))
            rows = []
            for i in indices:
                target, row = actuals[i][h - 1], predictions[i][h - 1]
                reference = weekly[origins[i]]["close"]
                rows.append(
                    {
                        "wis_delta": b._wis(target, row)
                        - b._wis(target, [reference] * 5),
                        "mae_delta": abs(target - row[2]) - abs(target - reference),
                        "coverage_50": float(row[1] <= target <= row[3]),
                        "coverage_80": float(row[0] <= target <= row[4]),
                    }
                )
            result.append(
                {
                    "horizon_weeks": h,
                    "first_origin_week": weekly[origins[start]]["date"],
                    "last_origin_week": weekly[origins[start + len(rows) - 1]]["date"],
                    "origins": len(rows),
                    "full_horizon_block": len(rows) == h,
                    **{key: sum(r[key] for r in rows) / len(rows) for key in rows[0]},
                }
            )
    return result


def run_candidate(directory: Path, name: str):
    manifest = read_manifest(directory)
    if name not in manifest["recipes"]:
        raise ValueError("Recipe outside frozen cycle")
    candidate_dir = directory / name
    candidate_dir.mkdir()  # A failed attempt cannot be silently retried.
    weekly = b._read_weekly_csv(directory / "snapshot.csv")
    closes = [row["close"] for row in weekly]
    started = time.perf_counter()
    (
        all_predictions,
        all_reference_predictions,
        all_probabilistic_predictions,
        all_actuals,
        all_origins,
        periods,
    ) = (
        [],
        [],
        [],
        [],
        [],
        [],
    )
    fit_seconds = 0.0
    with b.PeakRssSampler() as sampler:
        for index, fold in enumerate(manifest["folds"]):
            candidate = CANDIDATES[name]()
            fit_start = time.perf_counter()
            candidate.fit(closes[: fold["train_end"]], fold["train_end"])
            fit_seconds += time.perf_counter() - fit_start
            origins = list(range(fold["origin_start"], fold["origin_end"]))
            predictions = [
                validate_prediction(candidate.predict(closes[: origin + 1], origin))
                for origin in origins
            ]
            actuals = b._actuals(closes, origins)
            metrics, horizons = b._score(predictions, actuals)
            reference_predictions = [
                b.last_close_reference(closes, origin) for origin in origins
            ]
            reference_metrics, reference_horizons = b._score(
                reference_predictions, actuals
            )
            probabilistic_predictions = [
                evaluation.probabilistic_last_close_reference(closes, origin)
                for origin in origins
            ]
            probabilistic_metrics, probabilistic_horizons = b._score(
                probabilistic_predictions, actuals
            )
            model_dir = candidate_dir / f"fold-{index}"
            save_model(
                candidate,
                model_dir,
                {"snapshot_sha256": manifest["snapshot_sha256"], "fold": fold},
            )
            verify_reload(candidate, model_dir, closes, origins)
            periods.append(
                {
                    **fold,
                    "origins": len(origins),
                    "metrics": metrics,
                    "per_horizon": horizons,
                    "reference_metrics": reference_metrics,
                    "reference_per_horizon": reference_horizons,
                    "baseline_probabilistic_metrics": probabilistic_metrics,
                    "baseline_probabilistic_per_horizon": probabilistic_horizons,
                    "dependence_blocks": dependence_blocks(
                        weekly, origins, predictions, actuals
                    ),
                }
            )
            all_predictions.extend(predictions)
            all_reference_predictions.extend(reference_predictions)
            all_probabilistic_predictions.extend(probabilistic_predictions)
            all_actuals.extend(actuals)
            all_origins.extend(origins)
        metrics, horizons = b._score(all_predictions, all_actuals)
        reference_metrics, reference_horizons = b._score(
            all_reference_predictions, all_actuals
        )
        probabilistic_metrics, probabilistic_horizons = b._score(
            all_probabilistic_predictions, all_actuals
        )
        final_partition = manifest["partitions"]["final_holdout"]
        if final_partition["status"] == "available":
            final_origins = list(
                range(final_partition["origin_start"], final_partition["origin_end"])
            )
            final_candidate = CANDIDATES[name]()
            final_candidate.fit(
                closes[: final_partition["train_end"]], final_partition["train_end"]
            )
            final_predictions = [
                validate_prediction(
                    final_candidate.predict(closes[: origin + 1], origin)
                )
                for origin in final_origins
            ]
            final_actuals = b._actuals(closes, final_origins)
            final_baseline = [
                evaluation.probabilistic_last_close_reference(closes, origin)
                for origin in final_origins
            ]
            final_holdout = evaluation.score_partition(
                final_predictions,
                final_baseline,
                final_actuals,
                final_origins,
                weekly,
            )
            final_holdout.update(
                {
                    "name": final_partition["name"],
                    "status": final_partition["status"],
                    "train_end": final_partition["train_end"],
                    "origin_start": final_partition["origin_start"],
                    "origin_end": final_partition["origin_end"],
                    "read_only_after_scores": final_partition["read_only_after_scores"],
                    "selection_locked": final_partition["selection_locked"],
                    "partition": final_partition,
                    "origins": len(final_origins),
                }
            )
        else:
            final_holdout = final_partition
        write_json(candidate_dir / "final-holdout.json", final_holdout)
        candidate = CANDIDATES[name]()
        fit_start = time.perf_counter()
        candidate.fit(closes, len(closes))
        fit_seconds += time.perf_counter() - fit_start
        model_dir = candidate_dir / "final"
        save_model(
            candidate,
            model_dir,
            {
                "snapshot_sha256": manifest["snapshot_sha256"],
                "train_end": len(closes),
                "last_week": weekly[-1]["date"],
            },
        )
        verify_reload(candidate, model_dir, closes, [len(closes) - 1])
        emission_date = (
            date.fromisoformat(weekly[-1]["date"]) + timedelta(days=7)
        ).isoformat()
        preview = emit_forecast(candidate, weekly, emission_date)
        preview["status"] = "historical_replay_not_a_published_emission"
        write_json(candidate_dir / "preview.json", preview)
        write_json(
            candidate_dir / "predictions.json",
            [
                {
                    "origin_week": weekly[origin]["date"],
                    "quantiles": prediction,
                    "actuals": actual,
                }
                for origin, prediction, actual in zip(
                    all_origins, all_predictions, all_actuals
                )
            ],
        )
        result = {
            "name": name,
            "recalibration": None,
            "fit_seconds": fit_seconds,
            "runtime_seconds": time.perf_counter() - started,
            "peak_rss_bytes": sampler.peak_bytes,
            "artifact_bytes": sum(
                p.stat().st_size for p in candidate_dir.rglob("*") if p.is_file()
            ),
            "reload_verified": True,
            "metrics": metrics,
            "per_horizon": horizons,
            "reference_metrics": reference_metrics,
            "reference_per_horizon": reference_horizons,
            "baseline_probabilistic_metrics": probabilistic_metrics,
            "baseline_probabilistic_per_horizon": probabilistic_horizons,
            "per_period": periods,
            "final_holdout": final_holdout,
            "promotion": "not_evaluated_prospective_confirmation_required",
        }
        write_json(candidate_dir / "result.json", result)
    return result


def supervise(command, log_path: Path, seconds=1800, rss_bytes=4 * 1024**3):
    """Terminate only the worker started here when its total resource budget expires."""
    import psutil

    env = dict(
        os.environ, OMP_NUM_THREADS="2", OPENBLAS_NUM_THREADS="2", MKL_NUM_THREADS="2"
    )
    started, peak = time.perf_counter(), 0
    with log_path.open("x", encoding="utf-8") as log:
        process = subprocess.Popen(
            command, stdout=log, stderr=subprocess.STDOUT, env=env
        )
        monitored = psutil.Process(process.pid)
        descendants = {}
        try:
            while process.poll() is None:
                if time.perf_counter() - started > seconds:
                    raise RuntimeError("Recipe exceeded its total time budget")
                try:
                    # Windows virtualenv Python can be a launcher with a child interpreter.
                    members = [monitored, *monitored.children(recursive=True)]
                    rss = 0
                    for member in members:
                        descendants[member.pid] = member
                        try:
                            rss += member.memory_info().rss
                        except psutil.NoSuchProcess:
                            pass
                    peak = max(peak, rss)
                except psutil.NoSuchProcess:
                    break
                if peak > rss_bytes:
                    raise RuntimeError("Recipe exceeded its RAM budget")
                time.sleep(0.025)
            if process.wait() != 0:
                raise RuntimeError(f"Recipe failed; see {log_path}")
        finally:
            if process.poll() is None:
                for member in reversed(list(descendants.values())):
                    try:
                        member.kill()
                    except psutil.NoSuchProcess:
                        pass
                if process.poll() is None:
                    process.kill()
                process.wait()
                psutil.wait_procs(list(descendants.values()), timeout=5)
    return {"wall_seconds": time.perf_counter() - started, "peak_rss_bytes": peak}


def execute_run(directory: Path):
    with RUN_LOCK.open("x", encoding="utf-8") as lock:
        lock.write(f"pid={os.getpid()} directory={directory.resolve()}\n")
    try:
        return _execute_run(directory)
    finally:
        RUN_LOCK.unlink()


def _execute_run(directory: Path):
    manifest = read_manifest(directory)
    write_json(
        directory / "started.json",
        {"started_at": datetime.now(timezone.utc).isoformat()},
    )
    measurements = []
    for name in manifest["recipes"]:
        try:
            resources = supervise(
                [
                    sys.executable,
                    "-m",
                    "forecast.pipeline",
                    "worker",
                    "--directory",
                    str(directory.resolve()),
                    "--candidate",
                    name,
                ],
                directory / f"{name}.log",
            )
        except Exception as error:
            write_json(
                directory / "failure.json", {"candidate": name, "error": str(error)}
            )
            raise
        result = json.loads(
            (directory / name / "result.json").read_text(encoding="utf-8")
        )
        result["resources"] = resources
        result["artifact_bytes"] = sum(
            p.stat().st_size for p in (directory / name).rglob("*") if p.is_file()
        )
        result["estimated_railway_equivalent_cost_usd"] = b.estimate_railway_cost_usd(
            resources["wall_seconds"]
        )
        measurements.append(result)
    for result in measurements:
        result["historical_gate_failures"] = [
            row["horizon_weeks"]
            for row, ref in zip(result["per_horizon"], result["reference_per_horizon"])
            if not (
                row["mae"] <= 1.05 * ref["mae"]
                and 0.4 <= row["coverage_50"] <= 0.6
                and 0.7 <= row["coverage_80"] <= 0.9
            )
        ]
        final = result["final_holdout"]
        if final.get("status") == "available":
            result["final_holdout_gate_failures"] = [
                row["horizon_weeks"]
                for row in final["per_horizon"]
                if not (
                    row["mae"] <= 1.05 * row["baseline_last_close"]["mae"]
                    and 0.4 <= row["coverage_50"] <= 0.6
                    and 0.7 <= row["coverage_80"] <= 0.9
                )
            ]
        else:
            result["final_holdout_gate_failures"] = None
        result["publishable"] = False
    report = {
        "manifest_sha256": b._file_sha256(directory / "manifest.json"),
        "protocol": manifest,
        "reference": manifest["reference"],
        "candidates": measurements,
        "evidence_sources": {
            "selection": {
                "status": "historical_research",
                "read_before_final_holdout": True,
            },
            "final_holdout": manifest["partitions"]["final_holdout"],
            "prospective": manifest["partitions"]["prospective"],
        },
        "evidence": "exploratory; insufficient prospective evidence; no promotion",
        "actual_railway_cost_usd": 0.0,
    }
    write_json(directory / "report.json", report)
    write_json(
        directory / "inventory.json",
        {
            str(p.relative_to(directory)): {
                "sha256": b._file_sha256(p),
                "bytes": p.stat().st_size,
            }
            for p in sorted(directory.rglob("*"))
            if p.is_file()
        },
    )
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("prepare", "run", "worker"))
    parser.add_argument("--directory", required=True, type=Path)
    parser.add_argument("--snapshot", type=Path)
    parser.add_argument("--candidate", choices=list(CANDIDATES))
    parser.add_argument("--final-holdout-train-end", type=int)
    parser.add_argument("--final-holdout-origin-start", type=int)
    parser.add_argument("--final-holdout-origin-end", type=int)
    args = parser.parse_args()
    if args.command == "prepare":
        if args.snapshot is None:
            parser.error("prepare requires --snapshot")
        holdout_values = (
            args.final_holdout_train_end,
            args.final_holdout_origin_start,
            args.final_holdout_origin_end,
        )
        if any(value is not None for value in holdout_values) and not all(
            value is not None for value in holdout_values
        ):
            parser.error(
                "final holdout requires train-end, origin-start and origin-end together"
            )
        final_holdout = (
            {
                "train_end": args.final_holdout_train_end,
                "origin_start": args.final_holdout_origin_start,
                "origin_end": args.final_holdout_origin_end,
            }
            if all(value is not None for value in holdout_values)
            else None
        )
        prepare_run(args.snapshot, args.directory, final_holdout)
    elif args.command == "run":
        execute_run(args.directory)
    else:
        import psutil

        process = psutil.Process()
        # Set affinity before importing numerical libraries or fitting any model.
        process.cpu_affinity(process.cpu_affinity()[:2])
        if args.candidate is None:
            parser.error("worker requires --candidate")
        run_candidate(args.directory, args.candidate)
    print(str(args.directory))


if __name__ == "__main__":
    main()
