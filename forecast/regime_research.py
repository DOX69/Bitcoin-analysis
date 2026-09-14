"""Three causal regime hypotheses on inspected history, never promotion evidence."""

import argparse
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import sys

import numpy as np

from forecast import benchmark as b
from forecast.artifacts import dependencies, validate_prediction, write_json
from forecast.pipeline import dependence_blocks, supervise

RECIPES = ("ewma_reverting", "regime_neighbors", "pooled_scaled_errors")
PERIODS = {"first": (348, 412), "stress": (412, 464), "second": (464, 529)}
PROTOCOL = {
    "ewma_reverting": "Zero median log return; variance EWMA of centered last104 returns, half-life13; future variance reverts to population variance104 with half-life26; Gaussian accumulated variance.",
    "regime_neighbors": "For each h choose64 nearest mature origins j>=104; features momentum26/std26/sqrt26, log(std26/std104), drawdown52/std104/sqrt52; population standardization on mature origins only; Euclidean distance then j tie-break; absolute h-return quantiles .5/.8; median last price.",
    "pooled_scaled_errors": "For each k=1..52 use latest156 mature origins j>=104; pool abs(log(P[j+k]/P[j]))/std104(j)/sqrt(k); common linear quantiles .5/.8 times std104(t)*sqrt(h); median last price.",
}


def history(closes, origin):
    if origin < 220 or origin >= len(closes):
        raise ValueError("At least 221 known closes are required")
    known = np.asarray(closes[: origin + 1], dtype=float)
    if not np.isfinite(known).all() or np.any(known <= 0):
        raise ValueError("Known prices must be finite and positive")
    return np.log(known)


def sigmas(logs):
    returns = np.diff(logs)
    return {
        j: max(float(np.std(returns[j - 104 : j])), 1e-9) for j in range(104, len(logs))
    }


def neighbors(closes, origin, horizon):
    logs = history(closes, origin)
    if not 1 <= horizon <= 52:
        raise ValueError("Invalid horizon")
    returns = np.diff(logs)
    volatility = sigmas(logs)

    def features(j):
        short = max(float(np.std(returns[j - 26 : j])), 1e-9)
        return [
            (logs[j] - logs[j - 26]) / short / math.sqrt(26),
            math.log(short / volatility[j]),
            (logs[j] - max(logs[j - 51 : j + 1])) / volatility[j] / math.sqrt(52),
        ]

    indices = np.arange(104, origin - horizon + 1)
    states = np.asarray([features(int(j)) for j in indices])
    scales = np.maximum(states.std(axis=0), 1e-9)
    distance = np.sum(((states - features(origin)) / scales) ** 2, axis=1)
    return indices[np.lexsort((indices, distance))[:64]].tolist()


def predict(recipe, closes, origin):
    if recipe not in RECIPES:
        raise ValueError("Unknown recipe")
    logs = history(closes, origin)
    volatility = sigmas(logs)
    horizons = np.arange(1, 53)
    if recipe == "ewma_reverting":
        returns = np.diff(logs)[-104:]
        weights = np.exp2(-np.arange(103, -1, -1) / 13)
        mean = np.average(returns, weights=weights)
        recent = float(np.average((returns - mean) ** 2, weights=weights))
        long_run = volatility[origin] ** 2
        future = long_run + (recent - long_run) * np.exp2(-horizons / 26)
        scale = np.sqrt(np.maximum(np.cumsum(future), 1e-18))
        from statistics import NormalDist

        widths = np.outer(
            scale, [NormalDist().inv_cdf(0.75), NormalDist().inv_cdf(0.9)]
        )
    elif recipe == "regime_neighbors":
        widths = []
        for h in horizons:
            indices = neighbors(closes, origin, int(h))
            residuals = [abs(logs[j + h] - logs[j]) for j in indices]
            widths.append(np.quantile(residuals, [0.5, 0.8], method="linear"))
    else:
        residuals = []
        for h in horizons:
            last = origin - h
            residuals.extend(
                abs(logs[j + h] - logs[j]) / volatility[j] / math.sqrt(h)
                for j in range(max(104, last - 155), last + 1)
            )
        widths = np.outer(
            volatility[origin] * np.sqrt(horizons),
            np.quantile(residuals, [0.5, 0.8], method="linear"),
        )
    result = []
    for inner, outer in np.maximum(widths, 1e-9):
        result.append(
            [closes[origin] * math.exp(x) for x in (-outer, -inner, 0, inner, outer)]
        )
    return validate_prediction(result)


def score(predictions, actuals, last_prices):
    metrics, horizons = b._score(predictions, actuals)
    baseline, reference = b._score(
        [[[p] * 5 for _ in range(52)] for p in last_prices], actuals
    )
    failures = {"mae": [], "coverage_50": [], "coverage_80": []}
    for row, ref in zip(horizons, reference):
        if row["mae"] > 1.05 * ref["mae"]:
            failures["mae"].append(row["horizon_weeks"])
        for key, low, high in (("coverage_50", 0.4, 0.6), ("coverage_80", 0.7, 0.9)):
            if not low <= row[key] <= high:
                failures[key].append(row["horizon_weeks"])
    return {
        "metrics": metrics,
        "baseline_metrics": baseline,
        "per_horizon": horizons,
        "failures": failures,
        "failed_horizons": sorted(set().union(*failures.values())),
    }


def sources():
    return [
        Path(__file__),
        Path(b.__file__),
        Path(__file__).with_name("artifacts.py"),
        Path(__file__).with_name("pipeline.py"),
    ]


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def prepare(snapshot, directory):
    directory.mkdir(parents=True, exist_ok=False)
    (directory / "source").mkdir()
    (directory / "snapshot.csv").write_bytes(snapshot.read_bytes())
    for source in sources():
        (directory / "source" / source.name).write_bytes(source.read_bytes())
    lock = Path(__file__).resolve().parent.parent / "uv.lock"
    (directory / "uv.lock").write_bytes(lock.read_bytes())
    write_json(
        directory / "manifest.json",
        {
            "created_at": datetime.now(timezone.utc).isoformat(),
            "evidence": "adaptive_exploration_on_previously_inspected_history",
            "promotion": False,
            "recipes": PROTOCOL,
            "periods": PERIODS,
            "selection_periods": ["first", "second"],
            "quantiles": list(b.QUANTILES),
            "snapshot_sha256": digest(directory / "snapshot.csv"),
            "source_sha256": {source.name: digest(source) for source in sources()},
            "lock_sha256": digest(lock),
            "dependencies": dependencies(),
            "limits_per_recipe": {"cpus": 2, "rss_bytes": 4 * 1024**3, "seconds": 1800},
            "guardrails": {
                "mae_ratio_max": 1.05,
                "coverage_50": [0.4, 0.6],
                "coverage_80": [0.7, 0.9],
            },
        },
    )


def verify(directory):
    manifest = json.loads((directory / "manifest.json").read_text())
    if digest(directory / "snapshot.csv") != manifest["snapshot_sha256"]:
        raise ValueError("Frozen snapshot changed")
    if digest(directory / "uv.lock") != manifest["lock_sha256"]:
        raise ValueError("Frozen lock changed")
    if manifest["dependencies"] != dependencies():
        raise ValueError("Frozen dependencies changed")
    for source in sources():
        expected = manifest["source_sha256"][source.name]
        if (
            digest(source) != expected
            or digest(directory / "source" / source.name) != expected
        ):
            raise ValueError("Frozen source changed")
    return manifest


def worker(directory, recipe):
    import psutil

    process = psutil.Process()
    process.cpu_affinity(process.cpu_affinity()[:2])
    manifest = verify(directory)
    target = directory / recipe
    target.mkdir(exist_ok=False)
    write_json(
        target / "started.json", {"created_at": datetime.now(timezone.utc).isoformat()}
    )
    weekly = b._read_weekly_csv(directory / "snapshot.csv")
    closes = [row["close"] for row in weekly]
    periods, selected, all_rows = {}, [], []
    for name, (start, end) in manifest["periods"].items():
        if end + 51 >= len(closes):
            raise ValueError("Evaluation targets are immature")
        origins = list(range(start, end))
        predictions = [predict(recipe, closes, origin) for origin in origins]
        actuals = b._actuals(closes, origins)
        rows = [
            {
                "origin_index": origin,
                "origin_week": weekly[origin]["date"],
                "prediction": pred,
                "actual": obs,
            }
            for origin, pred, obs in zip(origins, predictions, actuals)
        ]
        all_rows.extend(rows)
        if name in manifest["selection_periods"]:
            selected.extend(rows)
        periods[name] = {
            **score(predictions, actuals, [closes[t] for t in origins]),
            "origins": len(origins),
            "first_origin_week": weekly[start]["date"],
            "last_origin_week": weekly[end - 1]["date"],
            "dependence_blocks": dependence_blocks(
                weekly, origins, predictions, actuals
            ),
        }
    selected.sort(key=lambda row: row["origin_index"])
    write_json(
        target / "predictions.json",
        sorted(all_rows, key=lambda row: row["origin_index"]),
    )
    write_json(
        target / "report.json",
        {
            "recipe": recipe,
            "evidence": manifest["evidence"],
            "promotion": False,
            "selection": score(
                [r["prediction"] for r in selected],
                [r["actual"] for r in selected],
                [closes[r["origin_index"]] for r in selected],
            ),
            "periods": periods,
        },
    )
    # Frozen history can be reloaded without relying on an in-memory fitted model.
    final = predict(recipe, closes, len(closes) - 1)
    reloaded = b._read_weekly_csv(directory / "snapshot.csv")
    np.testing.assert_allclose(
        final,
        predict(recipe, [r["close"] for r in reloaded], len(reloaded) - 1),
        rtol=1e-10,
        atol=1e-8,
    )
    write_json(
        target / "historical-preview.json",
        {
            "status": "historical_replay",
            "promotion": False,
            "origin_week": weekly[-1]["date"],
            "prediction": final,
        },
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["prepare", "run", "worker"])
    parser.add_argument("--directory", type=Path, required=True)
    parser.add_argument("--snapshot", type=Path)
    parser.add_argument("--recipe", choices=RECIPES)
    args = parser.parse_args()
    if args.command == "prepare":
        prepare(args.snapshot, args.directory)
    elif args.command == "worker":
        worker(args.directory, args.recipe)
    else:
        verify(args.directory)
        write_json(
            args.directory / "started.json",
            {"created_at": datetime.now(timezone.utc).isoformat()},
        )
        for recipe in RECIPES:
            resources = supervise(
                [
                    sys.executable,
                    "-m",
                    "forecast.regime_research",
                    "worker",
                    "--directory",
                    str(args.directory),
                    "--recipe",
                    recipe,
                ],
                args.directory / f"{recipe}.log",
            )
            write_json(args.directory / recipe / "resources.json", resources)
            print(json.dumps({"recipe": recipe, **resources}), flush=True)
        write_json(
            args.directory / "inventory.json",
            {
                str(p.relative_to(args.directory)): digest(p)
                for p in args.directory.rglob("*")
                if p.is_file()
            },
        )


if __name__ == "__main__":
    main()
