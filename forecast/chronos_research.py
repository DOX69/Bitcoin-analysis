"""Isolated, zero-shot Chronos research; never registers or promotes a model."""

from __future__ import annotations

import argparse
import importlib.metadata
import json
import math
import os
from pathlib import Path
import shutil
import sys
import time

from forecast import benchmark as b
from forecast.artifacts import write_json
from forecast.pipeline import supervise, validate_weekly

MODEL = "amazon/chronos-bolt-tiny"
MODELS = (MODEL, "autogluon/chronos-2-small")
FOLDS = ((348, 412), (464, 529))


def model_options(model):
    if model not in MODELS:
        raise ValueError("Unsupported research checkpoint")
    return {"batch_size": 1, "context_length": 2048} if model == MODELS[1] else {}


def causal_context(prices, origin, limit=2048):
    if not 0 <= origin < len(prices) or not 1 <= limit <= 2048:
        raise ValueError("Invalid origin or context limit")
    observed = prices[max(0, origin + 1 - limit) : origin + 1]
    if any(not math.isfinite(x) or x <= 0 for x in observed):
        raise ValueError("Invalid observed prices")
    return [math.log(x) for x in observed]


def usd_quantiles(log_quantiles):
    if len(log_quantiles) != 52 or any(len(row) != 5 for row in log_quantiles):
        raise ValueError("Expected 52 horizons and five quantiles")
    result = [[math.exp(x) for x in row] for row in log_quantiles]
    if any(
        any(not math.isfinite(x) or x <= 0 for x in row)
        or any(a > z for a, z in zip(row, row[1:]))
        for row in result
    ):
        raise ValueError("Invalid or crossed quantiles")
    return result


def prepare(snapshot, directory, model=MODEL):
    from huggingface_hub import HfApi

    weekly = b._read_weekly_csv(snapshot)
    validate_weekly(weekly)
    if len(weekly) != 581:
        raise ValueError("This frozen experiment requires 581 weeks")
    options = model_options(model)
    info = HfApi().model_info(model)
    directory.mkdir(parents=True, exist_ok=False)
    shutil.copyfile(snapshot, directory / "snapshot.csv")
    shutil.copyfile(Path(__file__), directory / "chronos_research.py")
    manifest = {
        "model": model,
        "revision": info.sha,
        "snapshot_sha256": b._file_sha256(snapshot),
        "runner_sha256": b._file_sha256(Path(__file__)),
        "scorer_sha256": b._file_sha256(Path(b.__file__)),
        "dependencies": {
            item.metadata["Name"]: item.version
            for item in importlib.metadata.distributions()
        },
        "folds": FOLDS,
        "context": "log(close[max(0,origin+1-2048):origin+1])",
        "quantiles": b.QUANTILES,
        "horizons": 52,
        "device": "cpu",
        "dtype": "float32",
        "threads": 2,
        "limits": {"seconds": 1800, "rss_bytes": 4 * 1024**3},
        "calibration": None,
        "predict_options": options,
        "quantile_interpolation": "Pipeline native interpolation for Q25/Q75",
        "crossing_policy": "reject; do not reorder",
        "evidence": "retrospective research; pretrained data overlap is not excluded",
        "promotion": False,
    }
    write_json(directory / "manifest.json", manifest)
    (directory / "manifest.sha256").write_text(
        b._file_sha256(directory / "manifest.json"), encoding="ascii"
    )


def worker(directory):
    import psutil
    import torch
    from chronos import BaseChronosPipeline

    manifest_path = directory / "manifest.json"
    if b._file_sha256(manifest_path) != (directory / "manifest.sha256").read_text():
        raise ValueError("Manifest changed")
    manifest = json.loads(manifest_path.read_text())
    for path, field in (
        (directory / "snapshot.csv", "snapshot_sha256"),
        (Path(__file__), "runner_sha256"),
        (Path(b.__file__), "scorer_sha256"),
    ):
        if b._file_sha256(path) != manifest[field]:
            raise ValueError("Frozen input changed")
    process = psutil.Process()
    allowed = process.cpu_affinity()
    process.cpu_affinity(allowed[:2])
    torch.set_num_threads(2)
    torch.set_num_interop_threads(1)
    torch.manual_seed(42)
    started = time.perf_counter()
    pipeline = BaseChronosPipeline.from_pretrained(
        manifest["model"],
        revision=manifest["revision"],
        device_map="cpu",
        torch_dtype=torch.float32,
        cache_dir=str(directory / "hf-cache"),
    )
    loaded_seconds = time.perf_counter() - started
    weekly = b._read_weekly_csv(directory / "snapshot.csv")
    prices = [row["close"] for row in weekly]
    predictions, actuals, baselines, exports, folds = [], [], [], [], []
    for start, stop in manifest["folds"]:
        fold_predictions, fold_actuals = [], []
        for origin in range(start, stop):
            context = torch.tensor(causal_context(prices, origin), dtype=torch.float32)
            with torch.inference_mode():
                quantiles, _ = pipeline.predict_quantiles(
                    [context],
                    prediction_length=52,
                    quantile_levels=manifest["quantiles"],
                    **manifest["predict_options"],
                )
            output = quantiles[0][0] if manifest["model"] == MODELS[1] else quantiles[0]
            prediction = usd_quantiles(output.tolist())
            actual = prices[origin + 1 : origin + 53]
            fold_predictions.append(prediction)
            fold_actuals.append(actual)
            baselines.append([[prices[origin]] * 5 for _ in range(52)])
            exports.append(
                {
                    "origin_index": origin,
                    "origin_week": weekly[origin]["date"],
                    "observed_close": prices[origin],
                    "quantiles": prediction,
                    "actuals": actual,
                }
            )
        metrics, per_horizon = b._score(fold_predictions, fold_actuals)
        folds.append(
            {
                "origin_start": start,
                "origin_end": stop,
                "metrics": metrics,
                "per_horizon": per_horizon,
            }
        )
        predictions.extend(fold_predictions)
        actuals.extend(fold_actuals)
        print(f"Completed fold {start}:{stop}", flush=True)
    metrics, per_horizon = b._score(predictions, actuals)
    naive_metrics, naive_per_horizon = b._score(baselines, actuals)
    write_json(directory / "predictions.json", exports)
    # Verify the frozen checkpoint can reproduce the first origin without network.
    del pipeline
    pipeline = BaseChronosPipeline.from_pretrained(
        manifest["model"],
        revision=manifest["revision"],
        device_map="cpu",
        torch_dtype=torch.float32,
        cache_dir=str(directory / "hf-cache"),
        local_files_only=True,
    )
    with torch.inference_mode():
        reloaded, _ = pipeline.predict_quantiles(
            [torch.tensor(causal_context(prices, FOLDS[0][0]), dtype=torch.float32)],
            prediction_length=52,
            quantile_levels=manifest["quantiles"],
            **manifest["predict_options"],
        )
    output = reloaded[0][0] if manifest["model"] == MODELS[1] else reloaded[0]
    if usd_quantiles(output.tolist()) != predictions[0]:
        raise ValueError("Reload predictions differ")
    write_json(
        directory / "report.json",
        {
            "evidence": manifest["evidence"],
            "promotion": False,
            "metrics": metrics,
            "per_horizon": per_horizon,
            "folds": folds,
            "naive_metrics": naive_metrics,
            "naive_per_horizon": naive_per_horizon,
            "mae_ratio": metrics["mae"] / naive_metrics["mae"],
            "wis_ratio": metrics["wis"] / naive_metrics["wis"],
            "origins": len(exports),
            "load_seconds": loaded_seconds,
            "worker_seconds": time.perf_counter() - started,
            "cpu_seconds": process.cpu_times().user + process.cpu_times().system,
            "cpu_affinity": process.cpu_affinity(),
            "reload_exact": True,
            "checkpoint_cache_bytes": sum(
                path.stat().st_size
                for path in (directory / "hf-cache").rglob("*")
                if path.is_file() and not path.is_symlink()
            ),
        },
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["prepare", "run", "worker"])
    parser.add_argument("--directory", required=True, type=Path)
    parser.add_argument("--snapshot", type=Path)
    parser.add_argument("--model", choices=MODELS, default=MODEL)
    args = parser.parse_args()
    if args.command == "prepare":
        if args.snapshot is None:
            parser.error("--snapshot required for prepare")
        prepare(args.snapshot, args.directory, args.model)
    elif args.command == "worker":
        worker(args.directory)
    else:
        os.environ["HF_HUB_DISABLE_PROGRESS_BARS"] = "1"
        resources = supervise(
            [
                sys.executable,
                "-m",
                "forecast.chronos_research",
                "worker",
                "--directory",
                str(args.directory),
            ],
            args.directory / "worker.log",
        )
        write_json(args.directory / "resources.json", resources)
        print(json.dumps(resources))


if __name__ == "__main__":
    main()
