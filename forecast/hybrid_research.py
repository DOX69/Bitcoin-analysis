"""Post-selected quantile hybrid. History and overlapping stress are exploratory."""

import argparse
from datetime import date, datetime, timedelta, timezone
import hashlib
import json
import math
from pathlib import Path
import statistics
import sys
import time

import numpy as np

from forecast import benchmark as b
from forecast.artifacts import dependencies, validate_prediction, write_json
from forecast.pipeline import dependence_blocks, supervise
from forecast.student_research import simulate


def combine(student):
    quantiles = student.copy()
    normal = statistics.NormalDist()
    for h in range(1, 53):
        quantiles[h - 1, 0] = math.sqrt(h) * normal.inv_cdf(0.1)
        quantiles[h - 1, 4] = math.sqrt(h) * normal.inv_cdf(0.9)
    if not np.isfinite(quantiles).all() or np.any(np.diff(quantiles, axis=1) < 0):
        raise ValueError("Hybrid quantiles cross; sorting is forbidden")
    return quantiles


def predict(closes, origin, quantiles):
    if origin < 104:
        raise ValueError("At least 105 known closes are required")
    returns = [
        math.log(closes[i] / closes[i - 1]) for i in range(origin - 103, origin + 1)
    ]
    sigma = max(statistics.pstdev(returns), 1e-9)
    predictions = [
        [closes[origin] * math.exp(sigma * value) for value in row] for row in quantiles
    ]
    return validate_prediction(predictions)


def shadow(weekly, quantiles, now):
    origin = date.fromisoformat(weekly[-1]["date"])
    targets = [origin + timedelta(days=6, weeks=h) for h in range(1, 53)]
    if now.utcoffset() != timedelta(0) or targets[0] <= now.date():
        raise ValueError("Shadow requires UTC creation and exclusively future targets")
    closes = [row["close"] for row in weekly]
    predictions = predict(closes, len(closes) - 1, quantiles)
    return {
        "created_at": now.isoformat(),
        "status": "research_shadow_local",
        "promotion": False,
        "origin_week": origin.isoformat(),
        "origin_close": closes[-1],
        "currency": "USD",
        "quantiles": list(b.QUANTILES),
        "data_last_close_date": (origin + timedelta(days=6)).isoformat(),
        "points": [
            {"horizon_weeks": h, "target_date": target.isoformat(), "USD": row}
            for h, (target, row) in enumerate(zip(targets, predictions), 1)
        ],
        "limits": "Locally archived research forecast, no publication and no matured prospective performance evidence",
    }


def sources():
    return [
        Path(__file__),
        Path(b.__file__),
        Path(__file__).with_name("artifacts.py"),
        Path(__file__).with_name("pipeline.py"),
        Path(__file__).with_name("student_research.py"),
    ]


def prepare(snapshot, directory):
    directory.mkdir(parents=True, exist_ok=False)
    (directory / "snapshot.csv").write_bytes(snapshot.read_bytes())
    (directory / "source").mkdir()
    hashes = {}
    for source in sources():
        content = source.read_bytes()
        (directory / "source" / source.name).write_bytes(content)
        hashes[source.name] = hashlib.sha256(content).hexdigest()
    write_json(
        directory / "manifest.json",
        {
            "created_at": datetime.now(timezone.utc).isoformat(),
            "evidence": "adaptive_exploration_after_inspected_results_not_independent_confirmation",
            "recipe": "post_selected_gaussian_outer_student_inner",
            "snapshot_sha256": hashlib.sha256(snapshot.read_bytes()).hexdigest(),
            "source_sha256": hashes,
            "dependencies": dependencies(),
            "folds": [[348, 412], [464, 529]],
            "stress_fold": [412, 464],
            "selection": "Q10/Q90 Gaussian104;Q25/Q50/Q75 Student latent104. Explicit choice after inspected results, not independent validation. Stress targets overlap previous evaluations. Reject quantile crossing; never sort.",
            "quantiles": list(b.QUANTILES),
            "horizons": list(range(1, 53)),
            "simulation": {
                "base_paths": 50000,
                "antithetic_paths": 100000,
                "seed": 42,
                "rng": "numpy.default_rng.PCG64",
                "innovations": "iid Student df5 divided by sqrt(5/3), variance1",
                "latent_drift": "independent Normal(0,1/sqrt(104)) per path, same value for all52increments",
                "paths": "cumsum innovations + h*latent_drift; append exact opposites",
                "quantile_method": "numpy.quantile linear; median set exactly0",
                "scale": "population std104 known one-week log returns through origin, floor1e-9; price=P_origin*exp(sigma*simulated_quantile)",
            },
            "limits": {"seconds": 1800, "cpus": 2, "rss_bytes": 4 * 1024**3},
            "promotion": False,
        },
    )


def run(directory):
    import psutil

    process = psutil.Process()
    process.cpu_affinity(process.cpu_affinity()[:2])
    manifest = json.loads((directory / "manifest.json").read_text())
    if manifest["dependencies"] != dependencies():
        raise ValueError("Frozen dependencies changed")
    for source in sources():
        expected = manifest["source_sha256"][source.name]
        if (
            hashlib.sha256(source.read_bytes()).hexdigest() != expected
            or hashlib.sha256(
                (directory / "source" / source.name).read_bytes()
            ).hexdigest()
            != expected
        ):
            raise ValueError("Frozen source changed")
    if (
        hashlib.sha256((directory / "snapshot.csv").read_bytes()).hexdigest()
        != manifest["snapshot_sha256"]
    ):
        raise ValueError("Frozen snapshot changed")
    write_json(
        directory / "started.json",
        {"started_at": datetime.now(timezone.utc).isoformat()},
    )
    started = time.perf_counter()
    student, diagnostics = simulate()
    quantiles = combine(student)
    write_json(
        directory / "standardized-distribution.json",
        {"quantiles": quantiles.tolist(), "diagnostics": diagnostics},
    )
    weekly = b._read_weekly_csv(directory / "snapshot.csv")
    closes = [row["close"] for row in weekly]
    predictions, actuals, origins, periods = [], [], [], []
    for start, end in manifest["folds"]:
        fold_origins = list(range(start, end))
        forecast = [predict(closes, origin, quantiles) for origin in fold_origins]
        observed = b._actuals(closes, fold_origins)
        metrics, horizons = b._score(forecast, observed)
        periods.append(
            {
                "first_origin_week": weekly[start]["date"],
                "last_origin_week": weekly[end - 1]["date"],
                "metrics": metrics,
                "per_horizon": horizons,
                "dependence_blocks": dependence_blocks(
                    weekly, fold_origins, forecast, observed
                ),
            }
        )
        predictions.extend(forecast)
        actuals.extend(observed)
        origins.extend(fold_origins)
    metrics, horizons = b._score(predictions, actuals)
    baseline = [[[closes[origin]] * 5 for _ in range(52)] for origin in origins]
    baseline_metrics, baseline_horizons = b._score(baseline, actuals)
    failures = {"mae": [], "coverage_50": [], "coverage_80": []}
    for row, ref in zip(horizons, baseline_horizons):
        if row["mae"] > 1.05 * ref["mae"]:
            failures["mae"].append(row["horizon_weeks"])
        for key, low, high in (("coverage_50", 0.4, 0.6), ("coverage_80", 0.7, 0.9)):
            if not low <= row[key] <= high:
                failures[key].append(row["horizon_weeks"])
    write_json(
        directory / "predictions.json",
        [
            {
                "origin_week": weekly[origin]["date"],
                "quantiles": forecast,
                "actuals": observed,
            }
            for origin, forecast, observed in zip(origins, predictions, actuals)
        ],
    )
    write_json(
        directory / "report.json",
        {
            "recipe": manifest["recipe"],
            "evidence": manifest["evidence"],
            "promotion": False,
            "metrics": metrics,
            "baseline_metrics": baseline_metrics,
            "per_horizon": horizons,
            "failures": failures,
            "failed_horizons": sorted(set().union(*failures.values())),
            "periods": periods,
            "seconds": time.perf_counter() - started,
        },
    )
    start, end = manifest["stress_fold"]
    stress_origins = list(range(start, end))
    stress_predictions = [
        predict(closes, origin, quantiles) for origin in stress_origins
    ]
    stress_actuals = b._actuals(closes, stress_origins)
    stress_metrics, stress_horizons = b._score(stress_predictions, stress_actuals)
    stress_baseline, stress_references = b._score(
        [[[closes[origin]] * 5 for _ in range(52)] for origin in stress_origins],
        stress_actuals,
    )
    stress_failures = {"mae": [], "coverage_50": [], "coverage_80": []}
    for row, ref in zip(stress_horizons, stress_references):
        if row["mae"] > 1.05 * ref["mae"]:
            stress_failures["mae"].append(row["horizon_weeks"])
        for key, low, high in (("coverage_50", 0.4, 0.6), ("coverage_80", 0.7, 0.9)):
            if not low <= row[key] <= high:
                stress_failures[key].append(row["horizon_weeks"])
    write_json(
        directory / "stress-report.json",
        {
            "evidence": "overlapping_targets_from_previously_inspected_history_not_independent",
            "promotion": False,
            "first_origin_week": weekly[start]["date"],
            "last_origin_week": weekly[end - 1]["date"],
            "metrics": stress_metrics,
            "baseline_metrics": stress_baseline,
            "per_horizon": stress_horizons,
            "failures": stress_failures,
            "failed_horizons": sorted(set().union(*stress_failures.values())),
            "dependence_blocks": dependence_blocks(
                weekly, stress_origins, stress_predictions, stress_actuals
            ),
        },
    )
    write_json(
        directory / "stress-predictions.json",
        [
            {
                "origin_week": weekly[origin]["date"],
                "quantiles": forecast,
                "actuals": observed,
            }
            for origin, forecast, observed in zip(
                stress_origins, stress_predictions, stress_actuals
            )
        ],
    )
    write_json(
        directory / "research-shadow.json",
        shadow(weekly, quantiles, datetime.now(timezone.utc)),
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["prepare", "run", "worker"])
    parser.add_argument("--directory", type=Path, required=True)
    parser.add_argument("--snapshot", type=Path)
    args = parser.parse_args()
    if args.command == "prepare":
        prepare(args.snapshot, args.directory)
    elif args.command == "worker":
        run(args.directory)
    else:
        metrics = supervise(
            [
                sys.executable,
                "-m",
                "forecast.hybrid_research",
                "worker",
                "--directory",
                str(args.directory),
            ],
            args.directory / "worker.log",
            seconds=1800,
            rss_bytes=4 * 1024**3,
        )
        write_json(args.directory / "resources.json", metrics)
        write_json(
            args.directory / "inventory.json",
            {
                str(path.relative_to(args.directory)): hashlib.sha256(
                    path.read_bytes()
                ).hexdigest()
                for path in args.directory.rglob("*")
                if path.is_file()
            },
        )
        print(json.dumps(metrics))


if __name__ == "__main__":
    main()
