"""One frozen compact NHITS experiment; no production registration."""

import hashlib
import importlib.metadata
import json
from pathlib import Path
import time

from forecast import benchmark as b

FOLDS = ((348, 348, 412), (464, 464, 529))
PARAMS = dict(
    h=52,
    input_size=104,
    n_blocks=[1, 1, 1],
    mlp_units=[[64, 64], [64, 64], [64, 64]],
    n_pool_kernel_size=[2, 2, 1],
    n_freq_downsample=[4, 2, 1],
    windows_batch_size=32,
    inference_windows_batch_size=32,
    batch_size=1,
    max_steps=300,
    random_seed=42,
    scaler_type="standard",
    accelerator="cpu",
    devices=1,
    logger=False,
    enable_checkpointing=False,
    enable_progress_bar=False,
    early_stop_patience_steps=-1,
    val_check_steps=100,
)


def causal_frame(closes, end):
    import numpy as np
    import pandas as pd

    if not 104 <= end <= len(closes):
        raise ValueError("Invalid observed context")
    return pd.DataFrame(
        {"unique_id": "btc", "ds": range(end), "y": np.log(closes[:end])}
    )


def prices(frame, columns):
    import numpy as np

    values = np.exp(frame[columns].to_numpy(dtype=float))
    if (
        values.shape != (52, 5)
        or not np.isfinite(values).all()
        or not (values > 0).all()
    ):
        raise ValueError("Invalid forecast contract")
    return np.sort(values, axis=1).tolist()


class NhitsCandidate:
    def fit(self, closes, train_end):
        from neuralforecast import NeuralForecast
        from neuralforecast.models import NHITS
        from neuralforecast.losses.pytorch import MQLoss

        loss = MQLoss(quantiles=list(b.QUANTILES))
        model = NHITS(loss=loss, **PARAMS)
        self.columns = ["NHITS" + name for name in loss.output_names]
        self.forecaster = NeuralForecast(models=[model], freq=1)
        self.forecaster.fit(df=causal_frame(closes, train_end), val_size=52)

    def predict(self, closes, origin):
        frame = self.forecaster.predict(
            df=causal_frame(closes, origin + 1), verbose=False
        )
        if frame["ds"].tolist() != list(range(origin + 1, origin + 53)):
            raise ValueError("Forecast horizon dates differ")
        return prices(frame, self.columns)


def main():
    import argparse
    import psutil
    import torch

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--snapshot", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    process = psutil.Process()
    process.cpu_affinity(process.cpu_affinity()[:2])
    torch.set_num_threads(2)
    torch.set_num_interop_threads(2)
    manifest = {
        "candidate": "nhits_compact_300",
        "evidence": "exploratory",
        "promotion": False,
        "parameters": PARAMS,
        "quantiles": list(b.QUANTILES),
        "folds": FOLDS,
        "val_size": 52,
        "calibration": None,
        "target": "log(close)",
        "postprocessing": "exp then sort quantiles",
        "prediction_context": "closes[:origin+1]",
        "snapshot_sha256": hashlib.sha256(args.snapshot.read_bytes()).hexdigest(),
        "code_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "benchmark_sha256": hashlib.sha256(Path(b.__file__).read_bytes()).hexdigest(),
        "versions": {
            dist.metadata["Name"]: dist.version
            for dist in importlib.metadata.distributions()
        },
        "limits": {"cpus": 2, "rss_bytes": 4 * 1024**3, "seconds": 1800},
    }
    (args.output / "manifest.json").write_text(
        json.dumps(manifest, indent=2), encoding="utf-8"
    )
    closes = [float(row["close"]) for row in b._read_weekly_csv(args.snapshot)]
    started, cpu_started = time.perf_counter(), time.process_time()
    results, all_predictions, all_origins = [], [], []
    with b.PeakRssSampler() as sampler:
        for train_end, start, end in FOLDS:
            candidate = NhitsCandidate()
            candidate.fit(closes, train_end)
            origins = list(range(start, end))
            predictions = [candidate.predict(closes, origin) for origin in origins]
            metrics, per_horizon = b._score(predictions, b._actuals(closes, origins))
            (args.output / f"predictions-{train_end}.json").write_text(
                json.dumps({"origins": origins, "predictions": predictions}),
                encoding="utf-8",
            )
            candidate.forecaster.save(
                path=str(args.output / f"model-{train_end}"),
                overwrite=False,
                save_dataset=False,
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
            all_predictions.extend(predictions)
            all_origins.extend(origins)
            print(json.dumps({"train_end": train_end, "metrics": metrics}), flush=True)
    metrics, per_horizon = b._score(all_predictions, b._actuals(closes, all_origins))
    report = {
        "manifest": manifest,
        "folds": results,
        "aggregate": {"metrics": metrics, "per_horizon": per_horizon},
        "seconds": time.perf_counter() - started,
        "cpu_seconds": time.process_time() - cpu_started,
        "peak_rss_bytes": sampler.peak_bytes,
    }
    (args.output / "report.json").write_text(
        json.dumps(report, indent=2), encoding="utf-8"
    )


if __name__ == "__main__":
    main()
