"""Three frozen, causal CPU hypotheses. Research only, never promotion evidence."""

import argparse
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import statistics
import sys
import tempfile
import time

from forecast import benchmark as b
from forecast.artifacts import dependencies, validate_prediction, write_json
from forecast.pipeline import dependence_blocks, supervise

RECIPES = ("no_drift_104_gaussian", "empirical_abs_156", "shrink_drift_01")


def empirical(values, probability):
    values = sorted(values)
    position = (len(values) - 1) * probability
    lower = math.floor(position)
    upper = math.ceil(position)
    return values[lower] + (position - lower) * (values[upper] - values[lower])


def predict(recipe, closes, origin):
    if recipe not in RECIPES or origin < 208:
        raise ValueError("Unknown recipe or insufficient history")
    returns = [
        math.log(closes[i] / closes[i - 1]) for i in range(origin - 103, origin + 1)
    ]
    sigma = max(statistics.pstdev(returns), 1e-9)
    drift = 0.1 * statistics.mean(returns) if recipe == "shrink_drift_01" else 0.0
    normal = statistics.NormalDist()
    result = []
    for h in range(1, 53):
        if recipe == "no_drift_104_gaussian":
            lower = sigma * math.sqrt(h) * normal.inv_cdf(0.75)
            upper = sigma * math.sqrt(h) * normal.inv_cdf(0.9)
        else:
            last = origin - h
            residuals = [
                abs(math.log(closes[j + h] / closes[j]))
                for j in range(last - 155, last + 1)
            ]
            lower = max(empirical(residuals, 0.5), 1e-9)
            upper = max(empirical(residuals, 0.8), lower)
        center = drift * h
        result.append(
            [
                closes[origin] * math.exp(center + offset)
                for offset in (-upper, -lower, 0.0, lower, upper)
            ]
        )
    return validate_prediction(result)


def run(directory):
    import psutil

    process = psutil.Process()
    process.cpu_affinity(process.cpu_affinity()[:2])
    manifest = json.loads((directory / "manifest.json").read_text())
    if (
        hashlib.sha256((directory / "snapshot.csv").read_bytes()).hexdigest()
        != manifest["snapshot_sha256"]
    ):
        raise ValueError("Snapshot changed after protocol freeze")
    if (
        hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
        != manifest["source_sha256"]
    ):
        raise ValueError("Recipe changed after protocol freeze")
    weekly = b._read_weekly_csv(directory / "snapshot.csv")
    closes = [row["close"] for row in weekly]
    report = {
        "evidence": "exploratory_previously_inspected_history",
        "promotion": False,
        "candidates": [],
    }
    for recipe in RECIPES:
        started = time.perf_counter()
        predictions, actuals, origins, periods = [], [], [], []
        for start, end in manifest["folds"]:
            fold_origins = list(range(start, end))
            forecast = [predict(recipe, closes, origin) for origin in fold_origins]
            observed = b._actuals(closes, fold_origins)
            metrics, horizons = b._score(forecast, observed)
            periods.append(
                {
                    "first_origin": weekly[start]["date"],
                    "last_origin": weekly[end - 1]["date"],
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
            for key, low, high in (
                ("coverage_50", 0.4, 0.6),
                ("coverage_80", 0.7, 0.9),
            ):
                if not low <= row[key] <= high:
                    failures[key].append(row["horizon_weeks"])
        result = {
            "recipe": recipe,
            "metrics": metrics,
            "baseline_metrics": baseline_metrics,
            "per_horizon": horizons,
            "failures": failures,
            "failed_horizons": sorted(set().union(*failures.values())),
            "periods": periods,
            "seconds": time.perf_counter() - started,
        }
        report["candidates"].append(result)
        write_json(
            directory / f"{recipe}-predictions.json",
            [
                {
                    "origin_week": weekly[origin]["date"],
                    "quantiles": prediction,
                    "actuals": actual,
                }
                for origin, prediction, actual in zip(origins, predictions, actuals)
            ],
        )
    write_json(directory / "report.json", report)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--snapshot", type=Path)
    parser.add_argument("--directory", type=Path, required=True)
    parser.add_argument("--worker", action="store_true")
    args = parser.parse_args()
    if args.worker:
        run(args.directory)
        return
    args.directory.mkdir(parents=True, exist_ok=False)
    snapshot = args.snapshot.read_bytes()
    (args.directory / "snapshot.csv").write_bytes(snapshot)
    manifest = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "recipes": RECIPES,
        "snapshot_sha256": hashlib.sha256(snapshot).hexdigest(),
        "source_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "dependencies": dependencies(),
        "folds": [[348, 412], [464, 529]],
        "quantiles": list(b.QUANTILES),
        "protocol": "Same inspected history: exploration only; causal rolling fit through current origin; no tuning after scores",
        "gaussian": "zero drift;104 latest one-week log returns;population std floor1e-9;sqrt(h)",
        "empirical": "156 latest mature h-week absolute log returns;linear quantile.5/.8; symmetric log bands;zero median;floor1e-9",
        "shrink": "empirical bands plus center h*0.1*mean104 one-week log returns",
        "limits": {"seconds_total": 300, "rss_bytes": 4 * 1024**3, "cpus": 2},
    }
    write_json(args.directory / "manifest.json", manifest)
    with tempfile.TemporaryDirectory() as temporary:
        metrics = supervise(
            [
                sys.executable,
                "-m",
                "forecast.challengers",
                "--worker",
                "--directory",
                str(args.directory),
            ],
            Path(temporary) / "worker.log",
            seconds=300,
            rss_bytes=4 * 1024**3,
        )
    write_json(args.directory / "resources.json", metrics)
    write_json(
        args.directory / "inventory.json",
        {
            path.name: hashlib.sha256(path.read_bytes()).hexdigest()
            for path in args.directory.iterdir()
            if path.is_file()
        },
    )
    print(json.dumps(metrics))


if __name__ == "__main__":
    main()
