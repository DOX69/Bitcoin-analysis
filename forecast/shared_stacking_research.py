"""Adaptive exploratory stacking with one shared weight per horizon."""

import argparse
from datetime import datetime, timezone
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

WEIGHTS = (0.0, 0.25, 0.5, 0.75, 1.0)


def choose_weight(losses):
    return min(
        zip(losses, WEIGHTS), key=lambda pair: (pair[0], abs(pair[1] - 0.5), pair[1])
    )[1]


def predict(closes, origin, student_quantiles):
    if origin < 208:
        raise ValueError("Insufficient causal history")
    returns = [math.log(closes[i] / closes[i - 1]) for i in range(1, origin + 1)]
    known = np.array(closes[: origin + 1])
    sigma = np.array(
        [
            max(statistics.pstdev(returns[j - 104 : j]), 1e-9)
            for j in range(104, origin + 1)
        ]
    )
    normal = statistics.NormalDist()
    gaussian = np.array(
        [[math.sqrt(h) * normal.inv_cdf(q) for q in b.QUANTILES] for h in range(1, 53)]
    )
    p_gaussian = known[104:, None, None] * np.exp(
        sigma[:, None, None] * gaussian[None, :, :]
    )
    p_student = known[104:, None, None] * np.exp(
        sigma[:, None, None] * student_quantiles[None, :, :]
    )
    points, weights, calibration = [], [], []
    for h in range(1, 53):
        last = origin - h
        first = max(104, last - 155)
        indices = np.arange(first, last + 1)
        observed = known[indices + h, None]
        q = np.array(b.QUANTILES)[None, :]
        gauss = p_gaussian[indices - 104, h - 1, :]
        student = p_student[indices - 104, h - 1, :]
        losses = []
        for weight in WEIGHTS:
            error = observed - (weight * student + (1 - weight) * gauss)
            losses.append(
                float(np.mean(np.sum(np.maximum(q * error, (q - 1) * error), axis=1)))
            )
        weight = choose_weight(losses)
        horizon_points = (
            weight * p_student[-1, h - 1, :] + (1 - weight) * p_gaussian[-1, h - 1, :]
        ).tolist()
        horizon_points[2] = closes[origin]
        points.append(sorted(horizon_points))
        weights.append(weight)
        calibration.append(
            {
                "first_origin": first,
                "last_origin": last,
                "origins": len(indices),
                "last_target": last + h,
            }
        )
    return validate_prediction(points), weights, calibration


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
            "evidence": "adaptive_exploration_after_inspected_failures_not_independent_confirmation",
            "recipe": "shared_horizon_stacking_gaussian104_student5_drift104",
            "snapshot_sha256": hashlib.sha256(snapshot.read_bytes()).hexdigest(),
            "source_sha256": hashes,
            "dependencies": dependencies(),
            "folds": [[348, 412], [464, 529]],
            "quantiles": list(b.QUANTILES),
            "horizons": list(range(1, 53)),
            "weights": WEIGHTS,
            "algorithm": "Each origin t,h: latest156 mature origins j>=104,j+h<=t. Causal sigma104 at each j for Gaussian and frozen Student trajectory quantiles. Choose one weight shared across5quantiles minimizing mean sum of5 USD pinball losses, proportional to WIS, over weights0,.25,.5,.75,1. Tie nearest.5 then lower. Price quantile w*Student+(1-w)*Gaussian; median P[t]; sort5quantiles. No manual horizon adjustments.",
            "student": "seed42;50000 Student5 variance1 innovation paths, latent Normal drift sd1/sqrt104 fixed per path; append opposites;100000 total paths;linear quantiles",
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
    distribution, diagnostics = simulate()
    write_json(
        directory / "student-distribution.json",
        {"quantiles": distribution.tolist(), "diagnostics": diagnostics},
    )
    weekly = b._read_weekly_csv(directory / "snapshot.csv")
    closes = [row["close"] for row in weekly]
    predictions, actuals, origins, periods, learned = [], [], [], [], []
    for start, end in manifest["folds"]:
        fold_origins = list(range(start, end))
        fitted = [predict(closes, origin, distribution) for origin in fold_origins]
        forecast = [row[0] for row in fitted]
        for origin, (_, weights, calibration) in zip(fold_origins, fitted):
            learned.append(
                {
                    "origin_week": weekly[origin]["date"],
                    "weights": weights,
                    "calibration": calibration,
                }
            )
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
    write_json(directory / "learned-weights.json", learned)
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
                "forecast.shared_stacking_research",
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
