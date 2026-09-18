"""Adaptive exploratory volatility-normalized intervals. No promotion contract."""

import argparse
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import statistics
import sys
import time

from forecast import benchmark as b
from forecast.artifacts import dependencies, validate_prediction, write_json
from forecast.challengers import empirical
from forecast.pipeline import dependence_blocks, supervise


def predict(closes, origin):
    if origin < 208:
        raise ValueError("At least 209 known closes are required")
    returns = [math.log(closes[i] / closes[i - 1]) for i in range(1, origin + 1)]
    sigmas = {
        j: max(statistics.pstdev(returns[j - 104 : j]), 1e-9)
        for j in range(104, origin + 1)
    }
    result = []
    for h in range(1, 53):
        last = origin - h
        residuals = [
            abs(math.log(closes[j + h] / closes[j])) / (sigmas[j] * math.sqrt(h))
            for j in range(max(104, last - 155), last + 1)
        ]
        scale = sigmas[origin] * math.sqrt(h)
        inner = max(empirical(residuals, 0.5) * scale, 1e-9)
        outer = max(empirical(residuals, 0.8) * scale, inner)
        result.append(
            [
                closes[origin] * math.exp(offset)
                for offset in (-outer, -inner, 0.0, inner, outer)
            ]
        )
    return validate_prediction(result)


def sources():
    return [
        Path(__file__),
        Path(b.__file__),
        Path(__file__).with_name("challengers.py"),
        Path(__file__).with_name("pipeline.py"),
        Path(__file__).with_name("artifacts.py"),
    ]


def prepare(snapshot, directory):
    directory.mkdir(parents=True, exist_ok=False)
    (directory / "snapshot.csv").write_bytes(snapshot.read_bytes())
    code = directory / "source"
    code.mkdir()
    hashes = {}
    for source in sources():
        content = source.read_bytes()
        (code / source.name).write_bytes(content)
        hashes[source.name] = hashlib.sha256(content).hexdigest()
    write_json(
        directory / "manifest.json",
        {
            "created_at": datetime.now(timezone.utc).isoformat(),
            "evidence": "adaptive_exploration_on_previously_inspected_history",
            "recipe": "volatility_normalized_empirical_abs_156",
            "snapshot_sha256": hashlib.sha256(snapshot.read_bytes()).hexdigest(),
            "source_sha256": hashes,
            "dependencies": dependencies(),
            "folds": [[348, 412], [464, 529]],
            "protocol": "Median P[t]. For each h, latest156 j>=104 with j+h<=t; residual abs(log(P[j+h]/P[j]))/(population std104 returns through j *sqrt(h)); width at t empirical linear quantile.5/.8 times std104 through t*sqrt(h). Std and final log-width floors1e-9; no horizon-specific tuning.",
            "quantiles": list(b.QUANTILES),
            "horizons": list(range(1, 53)),
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
    with (directory / "started.json").open("x") as handle:
        json.dump({"started_at": datetime.now(timezone.utc).isoformat()}, handle)
    started = time.perf_counter()
    weekly = b._read_weekly_csv(directory / "snapshot.csv")
    closes = [row["close"] for row in weekly]
    predictions, actuals, origins, periods = [], [], [], []
    for start, end in manifest["folds"]:
        fold_origins = list(range(start, end))
        forecast = [predict(closes, origin) for origin in fold_origins]
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
        resources = supervise(
            [
                sys.executable,
                "-m",
                "forecast.normalized_research",
                "worker",
                "--directory",
                str(args.directory),
            ],
            args.directory / "worker.log",
            seconds=1800,
            rss_bytes=4 * 1024**3,
        )
        write_json(args.directory / "resources.json", resources)
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
        print(json.dumps(resources))


if __name__ == "__main__":
    main()
