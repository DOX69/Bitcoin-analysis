"""Bounded daily Chronos-2 multivariate research; never publishes or promotes."""

from __future__ import annotations

import argparse
from datetime import date, datetime, timedelta, timezone
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import shutil
import sys
import time

import numpy as np

from forecast.pipeline import supervise

MODEL = "autogluon/chronos-2-small"
HORIZON = 365
CONTEXT_LENGTH = 2048
QUANTILES = (0.1, 0.25, 0.5, 0.75, 0.9)
WARMUP_DAYS = 1095
SPLIT_DATE = date(2023, 9, 13)
LIMITS = {"seconds": 1800, "rss_bytes": 4 * 1024**3, "threads": 2}
LANDMARKS = (1, 7, 30, 90, 180, 365)
SELECTION_GATE = {
    "aggregate_mae_and_wis_ratio_max": 0.98,
    "landmark_mae_ratio_max": 1.05,
    "requires_both_partitions": True,
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def encode(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, allow_nan=False).encode("utf-8")


def validate_rows(rows: list[dict]) -> tuple[list[date], np.ndarray]:
    if len(rows) < WARMUP_DAYS + HORIZON + 1:
        raise ValueError("Snapshot is too short for the frozen daily experiment")
    dates = [date.fromisoformat(str(row["date"])[:10]) for row in rows]
    if any(
        current - previous != timedelta(days=1)
        for previous, current in zip(dates, dates[1:])
    ):
        raise ValueError("OHLCV snapshot must be ordered, unique and gap free")
    fields = np.asarray(
        [
            [row[key] for key in ("open", "high", "low", "close", "volume")]
            for row in rows
        ],
        dtype=float,
    )
    if not np.isfinite(fields).all():
        raise ValueError("OHLCV snapshot contains non-finite values")
    opening, high, low, close, volume = fields.T
    if not np.all(
        (low > 0)
        & (low <= opening)
        & (low <= close)
        & (high >= opening)
        & (high >= close)
        & (volume >= 0)
    ):
        raise ValueError("OHLCV snapshot violates its value bounds")
    if "exported_at" in rows[0]:
        raise ValueError("Export metadata must be held outside row data")
    return dates, fields


def load_snapshot(path: Path) -> tuple[dict, list[date], np.ndarray]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    rows = payload.get("rows")
    if not isinstance(rows, list):
        raise ValueError("Expected an OHLCV snapshot with a rows array")
    dates, fields = validate_rows(rows)
    exported_at = datetime.fromisoformat(payload["exported_at"].replace("Z", "+00:00"))
    if (
        exported_at.tzinfo is None
        or dates[-1] >= exported_at.astimezone(timezone.utc).date()
    ):
        raise ValueError("Snapshot contains an incomplete UTC day")
    observed = [
        datetime.fromisoformat(str(row["observed_at"]).replace("Z", "+00:00"))
        for row in rows
    ]
    if any(
        timestamp.tzinfo is None or timestamp > exported_at for timestamp in observed
    ):
        raise ValueError("Snapshot contains an observation after export")
    return payload, dates, fields


def multivariate_context(
    fields: np.ndarray, origin: int, limit: int = CONTEXT_LENGTH
) -> np.ndarray:
    if not 0 <= origin < len(fields) or not 1 <= limit <= CONTEXT_LENGTH:
        raise ValueError("Invalid origin or context length")
    opening, high, low, close, volume = fields.T
    if (
        np.any(close <= 0)
        or np.any(volume < 0)
        or np.any(high <= 0)
        or np.any(low <= 0)
    ):
        raise ValueError("Invalid OHLCV values")
    logs = np.vstack((np.log(close), np.log1p(volume), np.log(high / low)))
    start = max(0, origin + 1 - limit)
    context = logs[:, start : origin + 1]
    if not np.isfinite(context).all():
        raise ValueError("Context contains non-finite values")
    return context.astype(np.float32, copy=False)


def origin_candidates(days: list[date]) -> list[int]:
    return [
        index
        for index, observed in enumerate(days)
        if index >= WARMUP_DAYS
        and observed.weekday() == 6
        and index + HORIZON < len(days)
    ]


def evaluation_origins(days: list[date]) -> list[int]:
    candidates = origin_candidates(days)
    return [
        index
        for index in candidates
        if sum(previous + HORIZON <= index for previous in candidates) >= 26
    ]


def partitions(days: list[date], origins: list[int]) -> dict[str, list[int]]:
    groups = {
        "earlier": [index for index in origins if days[index + HORIZON] <= SPLIT_DATE],
        "later_already_examined": [
            index for index in origins if days[index] > SPLIT_DATE
        ],
    }
    if min(map(len, groups.values())) < 26:
        raise ValueError("Both frozen evaluation partitions need at least 26 origins")
    return groups


def quantiles_to_usd(log_quantiles: object) -> np.ndarray:
    values = np.asarray(log_quantiles, dtype=float)
    if values.shape != (HORIZON, len(QUANTILES)):
        raise ValueError(f"Expected {(HORIZON, len(QUANTILES))} close quantiles")
    result = np.exp(values)
    if not np.isfinite(result).all() or np.any(result <= 0):
        raise ValueError("Chronos returned invalid close quantiles")
    if np.any(np.diff(result, axis=1) < 0):
        raise ValueError("Chronos returned crossed quantiles")
    return result


def naive_quantiles(
    log_closes: np.ndarray, origin: int, origins: list[int]
) -> np.ndarray:
    rows = []
    for horizon in range(1, HORIZON + 1):
        mature = [
            index for index in origins if index < origin and index + horizon <= origin
        ][-104:]
        if len(mature) < 26:
            raise ValueError("Insufficient mature reference errors")
        errors = (
            log_closes[np.asarray(mature) + horizon] - log_closes[np.asarray(mature)]
        )
        correction = np.quantile(errors, QUANTILES)
        correction -= correction[2]
        rows.append(log_closes[origin] + correction)
    return np.exp(np.asarray(rows))


def scores(predictions: list[np.ndarray], actuals: list[np.ndarray]) -> dict:
    predicted = np.asarray(predictions, dtype=float)
    observed = np.asarray(actuals, dtype=float)
    if predicted.shape != (len(actuals), HORIZON, len(QUANTILES)):
        raise ValueError("Invalid prediction shape")
    if observed.shape != (len(actuals), HORIZON):
        raise ValueError("Invalid actual shape")
    error = predicted[:, :, 2] - observed
    interval50 = (
        predicted[:, :, 3]
        - predicted[:, :, 1]
        + 4
        * np.maximum(
            np.maximum(predicted[:, :, 1] - observed, observed - predicted[:, :, 3]), 0
        )
    )
    interval80 = (
        predicted[:, :, 4]
        - predicted[:, :, 0]
        + 10
        * np.maximum(
            np.maximum(predicted[:, :, 0] - observed, observed - predicted[:, :, 4]), 0
        )
    )
    arrays = {
        "mae": np.abs(error).mean(axis=0),
        "rmse": np.sqrt((error**2).mean(axis=0)),
        "wis": (0.5 * np.abs(error) + 0.25 * interval50 + 0.1 * interval80).mean(axis=0)
        / 2.5,
        "coverage_50": (
            (observed >= predicted[:, :, 1]) & (observed <= predicted[:, :, 3])
        ).mean(axis=0),
        "coverage_80": (
            (observed >= predicted[:, :, 0]) & (observed <= predicted[:, :, 4])
        ).mean(axis=0),
        "width_50": (predicted[:, :, 3] - predicted[:, :, 1]).mean(axis=0),
        "width_80": (predicted[:, :, 4] - predicted[:, :, 0]).mean(axis=0),
    }
    return {
        "origins": len(actuals),
        "aggregate": {key: float(value.mean()) for key, value in arrays.items()},
        "per_horizon": [
            {
                "horizon_days": index + 1,
                **{key: float(value[index]) for key, value in arrays.items()},
            }
            for index in range(HORIZON)
        ],
    }


def summary(model: dict, reference: dict) -> dict:
    result = {
        "model": model["aggregate"],
        "reference": reference["aggregate"],
        "ratios": {
            metric: model["aggregate"][metric] / reference["aggregate"][metric]
            for metric in ("mae", "wis")
        },
        "landmarks": {},
    }
    for horizon in LANDMARKS:
        model_row = model["per_horizon"][horizon - 1]
        reference_row = reference["per_horizon"][horizon - 1]
        result["landmarks"][str(horizon)] = {
            "model_mae": model_row["mae"],
            "reference_mae": reference_row["mae"],
            "mae_ratio": model_row["mae"] / reference_row["mae"],
            "model_wis": model_row["wis"],
            "reference_wis": reference_row["wis"],
        }
    return result


def passes_gate(group_summaries: dict[str, dict]) -> bool:
    for item in group_summaries.values():
        if any(
            item["ratios"][metric] > SELECTION_GATE["aggregate_mae_and_wis_ratio_max"]
            for metric in ("mae", "wis")
        ):
            return False
        if any(
            item["landmarks"][str(horizon)]["mae_ratio"]
            > SELECTION_GATE["landmark_mae_ratio_max"]
            for horizon in LANDMARKS
        ):
            return False
    return True


def prepare(snapshot: Path, directory: Path) -> None:
    from huggingface_hub import HfApi

    payload, days, fields = load_snapshot(snapshot)
    info = HfApi().model_info(MODEL)
    directory.mkdir(parents=False, exist_ok=False)
    shutil.copyfile(snapshot, directory / "ohlcv-snapshot.json")
    shutil.copyfile(Path(__file__), directory / "chronos2_daily_research.py")
    manifest = {
        "schema_version": 1,
        "model": MODEL,
        "model_revision": info.sha,
        "license": info.card_data.get("license") if info.card_data else None,
        "snapshot_sha256": sha256(snapshot),
        "runner_sha256": sha256(Path(__file__)),
        "rows": len(days),
        "first_date": str(days[0]),
        "last_date": str(days[-1]),
        "channels": ["log_close", "log1p_volume", "log_high_low_range"],
        "context_length": CONTEXT_LENGTH,
        "horizon_days": HORIZON,
        "quantiles": QUANTILES,
        "origins": "Sunday dates after 1095-day warmup with 365 mature targets",
        "split_date": str(SPLIT_DATE),
        "selection_gate": SELECTION_GATE,
        "limits": LIMITS,
        "device": "cpu",
        "dtype": "float32",
        "calibration": None,
        "future_values_used": False,
        "point_in_time_history": False,
        "pretraining_overlap": "not excluded",
        "production_ready": False,
        "evidence_sources": {
            "selection": {"status": "historical_research_only"},
            "final_holdout": {
                "status": "already_examined_not_final",
                "horizon_days": HORIZON,
                "reason": "The revised research snapshot is not an untouched final holdout",
            },
            "prospective": {
                "status": "required_for_confirmation",
                "maturity": "365 complete UTC days after each origin",
            },
        },
        "partitions": {
            "selection": {"name": "selection", "status": "available"},
            "final_holdout": {
                "name": "final_holdout",
                "status": "not_available",
                "horizon_days": HORIZON,
                "read_only_after_scores": True,
                "reason": "The revised research snapshot is not an untouched final holdout",
            },
            "prospective": {
                "name": "prospective",
                "status": "required_for_confirmation",
            },
        },
        "dependencies": {
            package: importlib.metadata.version(package)
            for package in (
                "chronos-forecasting",
                "huggingface-hub",
                "numpy",
                "torch",
                "transformers",
            )
        },
        "source": payload.get("source"),
    }
    (directory / "manifest.json").write_bytes(encode(manifest))
    (directory / "manifest.sha256").write_text(
        sha256(directory / "manifest.json"), encoding="ascii"
    )


def read_manifest(directory: Path) -> dict:
    manifest_path = directory / "manifest.json"
    if sha256(manifest_path) != (directory / "manifest.sha256").read_text(
        encoding="ascii"
    ):
        raise ValueError("Manifest integrity failure")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest["limits"] != LIMITS or manifest["model"] != MODEL:
        raise ValueError("Unsupported frozen contract")
    if sha256(directory / "ohlcv-snapshot.json") != manifest["snapshot_sha256"]:
        raise ValueError("Snapshot integrity failure")
    if sha256(Path(__file__)) != manifest["runner_sha256"]:
        raise ValueError("Runner changed after preparation")
    return manifest


def _chronos_close_quantiles(
    pipeline, torch, context: np.ndarray, manifest: dict
) -> np.ndarray:
    quantiles, _ = pipeline.predict_quantiles(
        [torch.tensor(context, dtype=torch.float32)],
        prediction_length=manifest["horizon_days"],
        quantile_levels=manifest["quantiles"],
        batch_size=1,
        context_length=manifest["context_length"],
        limit_prediction_length=False,
    )
    output = quantiles[0]
    if hasattr(output, "detach"):
        output = output.detach().cpu().numpy()
    output = np.asarray(output, dtype=float)
    if output.ndim == 4:
        output = output[0]
    if output.ndim != 3 or output.shape[0] < 1:
        raise ValueError(f"Unexpected Chronos output shape: {output.shape}")
    return quantiles_to_usd(output[0])


def worker(directory: Path) -> None:
    import psutil
    import torch
    from chronos import BaseChronosPipeline

    manifest = read_manifest(directory)
    payload, days, fields = load_snapshot(directory / "ohlcv-snapshot.json")
    origins = evaluation_origins(days)
    reference_origins = origin_candidates(days)
    groups = partitions(days, origins)
    process = psutil.Process()
    process.cpu_affinity(process.cpu_affinity()[: manifest["limits"]["threads"]])
    torch.set_num_threads(manifest["limits"]["threads"])
    torch.set_num_interop_threads(1)
    torch.manual_seed(42)
    started = time.perf_counter()
    pipeline = BaseChronosPipeline.from_pretrained(
        manifest["model"],
        revision=manifest["model_revision"],
        device_map="cpu",
        torch_dtype=torch.float32,
        cache_dir=str(directory / "hf-cache"),
    )
    model_context = getattr(pipeline, "model_context_length", None)
    model_horizon = getattr(pipeline, "model_prediction_length", None)
    if model_context is not None and model_context < manifest["context_length"]:
        raise ValueError("Frozen context exceeds checkpoint context")
    if model_horizon is not None and model_horizon < manifest["horizon_days"]:
        raise ValueError("Frozen horizon exceeds checkpoint prediction length")
    log_closes = np.log(fields[:, 3])
    predictions: dict[int, np.ndarray] = {}
    actuals: dict[int, np.ndarray] = {}
    references: dict[int, np.ndarray] = {}
    records = []
    for position, origin in enumerate(origins, start=1):
        prediction = _chronos_close_quantiles(
            pipeline, torch, multivariate_context(fields, origin), manifest
        )
        actual = fields[origin + 1 : origin + 1 + HORIZON, 3]
        reference = naive_quantiles(log_closes, origin, reference_origins)
        predictions[origin] = prediction
        actuals[origin] = actual
        references[origin] = reference
        records.append(
            {
                "origin_index": origin,
                "origin_date": str(days[origin]),
                "observed_close": float(fields[origin, 3]),
                "quantiles": prediction.tolist(),
                "actuals": actual.tolist(),
            }
        )
        if position == 1 or position % 25 == 0:
            print(f"Forecasted {position}/{len(origins)} origins", flush=True)
    group_reports = {}
    group_summaries = {}
    for name, indices in groups.items():
        model_score = scores(
            [predictions[index] for index in indices],
            [actuals[index] for index in indices],
        )
        reference_score = scores(
            [references[index] for index in indices],
            [actuals[index] for index in indices],
        )
        group_reports[name] = {
            "origins": len(indices),
            "first_origin": str(days[indices[0]]),
            "last_origin": str(days[indices[-1]]),
            "models": {"chronos2_multivariate": model_score, "naive": reference_score},
        }
        group_summaries[name] = summary(model_score, reference_score)
    report = {
        "recipe": manifest,
        "groups": group_reports,
        "comparison": group_summaries,
        "decision": (
            "candidate_requires_review"
            if passes_gate(group_summaries)
            else "reject_all_challengers"
        ),
        "production_ready": False,
        "evidence": "retrospective_replay_on_revised_snapshot; prospective_confirmation_required",
        "evidence_sources": {
            "selection": {"status": "historical_research_only"},
            "final_holdout": {
                "status": "already_examined_not_final",
                "maturity_horizon_days": HORIZON,
                "reason": "This replay uses revised history and is not an untouched holdout",
            },
            "prospective": {
                "status": "required_for_confirmation",
                "maturity": "365 complete UTC days after each daily origin",
            },
        },
        "partitions": {
            "selection": {"name": "selection", "status": "historical_research"},
            "final_holdout": {
                "name": "final_holdout",
                "status": "not_available",
                "horizon_days": HORIZON,
                "read_only_after_scores": True,
                "reason": "This replay uses revised history and is not an untouched final holdout",
            },
            "prospective": {
                "name": "prospective",
                "status": "immutable_emissions",
            },
        },
        "origins": len(origins),
        "load_seconds": None,
        "worker_seconds": time.perf_counter() - started,
        "cpu_affinity": process.cpu_affinity(),
        "model_context_length": model_context,
        "model_prediction_length": model_horizon,
        "output_shape": [len(QUANTILES), HORIZON],
        "payload_source": payload.get("source"),
    }
    write_json(directory / "predictions.json", records)
    write_json(directory / "report.json", report)


def write_json(path: Path, value: object) -> None:
    path.write_bytes(encode(value))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("prepare", "run", "worker"))
    parser.add_argument("--directory", required=True, type=Path)
    parser.add_argument("--snapshot", type=Path)
    args = parser.parse_args()
    if args.command == "prepare":
        if args.snapshot is None:
            parser.error("prepare requires --snapshot")
        prepare(args.snapshot, args.directory)
    elif args.command == "worker":
        worker(args.directory)
    else:
        os.environ["HF_HUB_DISABLE_PROGRESS_BARS"] = "1"
        resources = supervise(
            [
                sys.executable,
                "-m",
                "forecast.chronos2_daily_research",
                "worker",
                "--directory",
                str(args.directory.resolve()),
            ],
            args.directory / "worker.log",
            seconds=LIMITS["seconds"],
            rss_bytes=LIMITS["rss_bytes"],
        )
        report = json.loads(
            (args.directory / "report.json").read_text(encoding="utf-8")
        )
        report["resources"] = resources
        report["estimated_railway_equivalent_cost_usd"] = (
            resources["wall_seconds"] / 60 * (2 * 0.000463 + 4 * 0.000231)
        )
        write_json(args.directory / "report.json", report)
        print(json.dumps({"decision": report["decision"], "resources": resources}))


if __name__ == "__main__":
    main()
