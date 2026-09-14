"""Fixed exploratory linear quantile recipe; never registers a production model."""

import hashlib
import importlib.metadata
import json
import math
from pathlib import Path
import statistics
import time

from forecast import benchmark as b

FOLDS = ((348, 348, 412), (464, 464, 529))
ALPHA = 0.01


def features(closes, origin):
    if origin < 52:
        raise ValueError("52 observed weeks required")
    momentum = [math.log(closes[origin] / closes[origin - lag]) for lag in (4, 13, 52)]
    volatility = [
        statistics.pstdev(
            math.log(closes[j] / closes[j - 1])
            for j in range(origin - window + 1, origin + 1)
        )
        for window in (13, 52)
    ]
    return momentum + volatility


class LinearCandidate:
    def fit(self, closes, train_end):
        import numpy as np
        from sklearn.linear_model import QuantileRegressor
        from sklearn.preprocessing import StandardScaler

        self.models, self.scalers = [], []
        for horizon in range(1, 53):
            origins = range(52, train_end - horizon)
            x = np.asarray([features(closes, j) for j in origins])
            y = np.asarray([math.log(closes[j + horizon] / closes[j]) for j in origins])
            scaler = StandardScaler().fit(x)
            scaled = scaler.transform(x)
            self.scalers.append(scaler)
            self.models.append(
                [
                    QuantileRegressor(quantile=q, alpha=ALPHA, solver="highs").fit(
                        scaled, y
                    )
                    for q in b.QUANTILES
                ]
            )

    def predict(self, closes, origin):
        row = [features(closes, origin)]
        return [
            sorted(
                closes[origin]
                * math.exp(float(model.predict(scaler.transform(row))[0]))
                for model in models
            )
            for scaler, models in zip(self.scalers, self.models)
        ]


def main():
    import argparse
    import psutil
    from threadpoolctl import threadpool_limits

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--snapshot", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    process = psutil.Process()
    process.cpu_affinity(process.cpu_affinity()[:2])
    manifest = {
        "candidate": "linear_quantile_l1_001",
        "evidence": "exploratory",
        "promotion": False,
        "alpha": ALPHA,
        "features": ["momentum4", "momentum13", "momentum52", "vol13", "vol52"],
        "scaler": "StandardScaler fit per horizon on training origins only",
        "solver": "highs",
        "label_rule": "origin+horizon<train_end",
        "minimum_origin": 52,
        "quantiles": list(b.QUANTILES),
        "postprocessing": "sort quantiles",
        "folds": FOLDS,
        "snapshot_sha256": hashlib.sha256(args.snapshot.read_bytes()).hexdigest(),
        "code_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "benchmark_sha256": hashlib.sha256(Path(b.__file__).read_bytes()).hexdigest(),
        "versions": {
            name: importlib.metadata.version(name)
            for name in ("scikit-learn", "numpy", "scipy")
        },
        "limits": {"cpus": 2, "rss_bytes": 4 * 1024**3, "seconds": 1800},
    }
    (args.output / "manifest.json").write_text(
        json.dumps(manifest, indent=2), encoding="utf-8"
    )
    closes = [float(row["close"]) for row in b._read_weekly_csv(args.snapshot)]
    started, cpu_started = time.perf_counter(), time.process_time()
    results = []
    with threadpool_limits(limits=2), b.PeakRssSampler() as sampler:
        for train_end, start, end in FOLDS:
            candidate = LinearCandidate()
            candidate.fit(closes, train_end)
            origins = list(range(start, end))
            predictions = [candidate.predict(closes, origin) for origin in origins]
            metrics, per_horizon = b._score(predictions, b._actuals(closes, origins))
            (args.output / f"predictions-{train_end}.json").write_text(
                json.dumps({"origins": origins, "predictions": predictions}),
                encoding="utf-8",
            )
            results.append(
                {
                    "train_end": train_end,
                    "test_start": start,
                    "test_end": end,
                    "metrics": metrics,
                    "per_horizon": per_horizon,
                }
            )
            print(json.dumps({"train_end": train_end, "metrics": metrics}), flush=True)
    report = {
        "manifest": manifest,
        "folds": results,
        "seconds": time.perf_counter() - started,
        "cpu_seconds": time.process_time() - cpu_started,
        "peak_rss_bytes": sampler.peak_bytes,
    }
    (args.output / "report.json").write_text(
        json.dumps(report, indent=2), encoding="utf-8"
    )


if __name__ == "__main__":
    main()
