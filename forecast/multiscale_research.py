"""Causal daily/weekly forecast experiment; never publishes or promotes."""

from __future__ import annotations

import argparse
from datetime import date, datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
import time
from typing import Iterable, Sequence

import numpy as np
from threadpoolctl import threadpool_limits

from forecast import daily_recovery
from forecast import daily_research as daily
from forecast import trend_research as weekly
from forecast.benchmark import PeakRssSampler

HORIZONS = np.arange(1, 366)
WEEKLY_HORIZONS = np.arange(1, 53)
QUANTILES = np.asarray(daily.QUANTILES, dtype=float)
SPLIT_DATE = date(2023, 9, 13)
ANCHOR_WINDOW_WEEKS = 104
ANCHOR_CALIBRATION_LIMIT = 104
MIN_ANCHOR_CALIBRATION = 26
RESIDUAL_WINDOW_WEEKS = 26
MIN_RESIDUAL_SAMPLES = 8

RECIPE = {
    "model": "multiscale_daily_weekly_v1",
    "target": "365 daily UTC closes from a Sunday origin",
    "weekly_component": {
        "anchors": "Sunday closes at horizons 7,14,...,364 days",
        "fit": "existing damped-trend-v1 on the last 104 completed weekly closes",
        "calibration": "last 104 mature anchor log errors per weekly horizon, minimum 26",
    },
    "trajectory": "piecewise linear interpolation in log space; one-day extrapolation after J+364",
    "daily_residual": {
        "definition": "daily log close minus the linear path between two completed Sunday closes",
        "history": "last 26 completed weekly residuals for the target weekday",
        "volatility": "past 30-day log-return volatility rescales residual deviations, clipped to 0.5..2.0",
        "reconciliation": "zero at every weekly anchor",
    },
    "partitions": "same mature Sunday origins and 2023-09-13 split as daily-v1",
    "quantiles": list(daily.QUANTILES),
    "resources": {"threads": 2, "rss_bytes": 4 * 1024**3, "seconds": 30 * 60},
    "production_ready": False,
}
MODEL_MANIFEST = hashlib.sha256(json.dumps(RECIPE, sort_keys=True).encode()).hexdigest()


def _sunday_indices(days: Sequence[date], end: int | None = None) -> list[int]:
    last = len(days) - 1 if end is None else end
    return [index for index, day in enumerate(days[: last + 1]) if day.weekday() == 6]


def weekly_raw_forecasts(
    days: Sequence[date], values: Sequence[float], origins: Iterable[int]
) -> dict[int, np.ndarray]:
    """Fit each weekly anchor using observations available at that Sunday only."""
    closes = np.asarray(values, dtype=float)
    result = {}
    for origin in sorted(set(origins)):
        if origin < 0 or origin >= len(days) or days[origin].weekday() != 6:
            raise ValueError("Weekly origins must be valid Sundays")
        history = _sunday_indices(days, origin)
        if len(history) < ANCHOR_WINDOW_WEEKS:
            raise ValueError("104 completed weekly closes required")
        result[origin] = np.asarray(weekly.fit(closes[history])[0], dtype=float)
    return result


def mature_anchor_origins(
    raw_anchors: dict[int, np.ndarray], origin: int, horizon_weeks: int
) -> list[int]:
    """Return only origins whose weekly target is observed by ``origin``."""
    return [
        candidate
        for candidate in sorted(raw_anchors)
        if candidate < origin and candidate + horizon_weeks * 7 <= origin
    ]


def calibrated_anchor_quantiles(
    logs: np.ndarray,
    origin: int,
    raw_anchors: dict[int, np.ndarray],
    minimum: int = MIN_ANCHOR_CALIBRATION,
) -> np.ndarray:
    calibrated = np.empty((len(WEEKLY_HORIZONS), len(QUANTILES)))
    for index, horizon in enumerate(WEEKLY_HORIZONS):
        mature = mature_anchor_origins(raw_anchors, origin, int(horizon))[
            -ANCHOR_CALIBRATION_LIMIT:
        ]
        if len(mature) < minimum:
            raise ValueError("Insufficient mature weekly anchor errors")
        errors = np.asarray(
            [
                logs[candidate + int(horizon) * 7] - raw_anchors[candidate][index]
                for candidate in mature
            ]
        )
        calibrated[index] = raw_anchors[origin][index] + np.quantile(errors, QUANTILES)
    return np.maximum.accumulate(calibrated, axis=1)


def _residual_history(
    days: Sequence[date], logs: np.ndarray, origin: int
) -> dict[int, list[float]]:
    """Build residuals only for weeks whose ending Sunday is <= origin."""
    history = {weekday: [] for weekday in range(7)}
    sundays = _sunday_indices(days, origin)
    for previous, current in zip(sundays, sundays[1:]):
        for index in range(previous + 1, current + 1):
            fraction = (index - previous) / 7
            baseline = logs[previous] + fraction * (logs[current] - logs[previous])
            history[days[index].weekday()].append(float(logs[index] - baseline))
    return history


def residual_sample_indices(days: Sequence[date], origin: int) -> list[int]:
    """Return daily residual observations that are available at ``origin``."""
    sundays = _sunday_indices(days, origin)
    return [
        index
        for previous, current in zip(sundays, sundays[1:])
        for index in range(previous + 1, current + 1)
        if index <= origin
    ]


def _volatility_scale(logs: np.ndarray, days: Sequence[date], origin: int) -> float:
    current_start = max(1, origin - 29)
    current = float(np.std(np.diff(logs[current_start : origin + 1])))
    sunday_ends = _sunday_indices(days, origin)
    past = []
    for end in sunday_ends[-RESIDUAL_WINDOW_WEEKS:]:
        start = max(1, end - 29)
        past.append(float(np.std(np.diff(logs[start : end + 1]))))
    baseline = float(np.median(past)) if past else current
    if baseline <= 1e-12:
        return 1.0
    return float(np.clip(current / baseline, 0.5, 2.0))


def residual_quantiles(
    days: Sequence[date], logs: np.ndarray, origin: int
) -> np.ndarray:
    history = _residual_history(days, logs, origin)
    scale = _volatility_scale(logs, days, origin)
    result = np.zeros((len(HORIZONS), len(QUANTILES)))
    origin_date = days[origin]
    for index, horizon in enumerate(HORIZONS):
        if horizon % 7 == 0:
            continue
        weekday = (origin_date + timedelta(days=int(horizon))).weekday()
        samples = history[weekday][-RESIDUAL_WINDOW_WEEKS:]
        if len(samples) < MIN_RESIDUAL_SAMPLES:
            raise ValueError("Insufficient mature daily residuals")
        quantiles = np.quantile(samples, QUANTILES)
        result[index] = quantiles[2] + (quantiles - quantiles[2]) * scale
    return np.maximum.accumulate(result, axis=1)


def _interpolated_anchor_quantiles(
    origin_log: float, anchors: np.ndarray
) -> np.ndarray:
    result = np.empty((len(HORIZONS), len(QUANTILES)))
    origin_row = np.repeat(origin_log, len(QUANTILES))
    for index, horizon in enumerate(HORIZONS):
        if horizon == 365:
            previous = anchors[-2]
            current = anchors[-1]
            result[index] = previous + (current - previous) * (8 / 7)
            continue
        if horizon % 7 == 0:
            result[index] = anchors[horizon // 7 - 1]
            continue
        upper_week = (int(horizon) + 6) // 7
        upper_horizon = upper_week * 7
        if upper_week == 1:
            lower_horizon = 0
            lower = origin_row
        else:
            lower_horizon = (upper_week - 1) * 7
            lower = anchors[upper_week - 2]
        weight = (horizon - lower_horizon) / (upper_horizon - lower_horizon)
        result[index] = lower + (anchors[upper_week - 1] - lower) * weight
    return np.maximum.accumulate(result, axis=1)


def forecast_at_origin(
    days: Sequence[date],
    values: Sequence[float],
    origin: int,
    raw_anchors: dict[int, np.ndarray],
) -> dict[str, np.ndarray]:
    """Return calibrated anchor, weekly-only and reconciled multi-scale quantiles."""
    if origin not in raw_anchors or days[origin].weekday() != 6:
        raise ValueError("Forecast origin must be a Sunday in raw weekly forecasts")
    logs = np.log(np.asarray(values, dtype=float)[: origin + 1])
    anchors = calibrated_anchor_quantiles(logs, origin, raw_anchors)
    trajectory = _interpolated_anchor_quantiles(logs[-1], anchors)
    residuals = residual_quantiles(days, logs, origin)
    combined = trajectory.copy()
    for index, horizon in enumerate(HORIZONS):
        if horizon % 7 != 0:
            combined[index] = np.maximum.accumulate(
                trajectory[index] + residuals[index]
            )
        else:
            combined[index] = anchors[horizon // 7 - 1]
    return {
        "anchor_quantiles": np.exp(anchors),
        "trajectory": np.exp(trajectory),
        "residual_quantiles": residuals,
        "quantiles": np.exp(combined),
    }


def output_points(origin_date: date, quantiles: np.ndarray) -> list[dict[str, object]]:
    return [
        {
            "horizon_days": int(horizon),
            "target_date": str(origin_date + timedelta(days=int(horizon))),
            "USD": row.tolist(),
        }
        for horizon, row in zip(HORIZONS, quantiles)
    ]


def benchmark_origins(
    days: Sequence[date], raw_anchors: dict[int, np.ndarray]
) -> list[int]:
    return [
        origin
        for origin in sorted(raw_anchors)
        if origin + 365 < len(days)
        and len(mature_anchor_origins(raw_anchors, origin, 52))
        >= MIN_ANCHOR_CALIBRATION
        and len(
            [
                candidate
                for candidate in raw_anchors
                if candidate < origin and candidate + 365 <= origin
            ]
        )
        >= MIN_ANCHOR_CALIBRATION
    ]


def partition_origins(
    days: Sequence[date], origins: Iterable[int]
) -> dict[str, list[int]]:
    origins = sorted(origins)
    return {
        "earlier": [origin for origin in origins if days[origin + 365] <= SPLIT_DATE],
        "later_already_examined": [
            origin for origin in origins if days[origin] > SPLIT_DATE
        ],
    }


def prediction_archive(predictions: dict[str, dict[str, list[np.ndarray]]]) -> dict:
    return {
        partition: {
            candidate: [np.asarray(prediction).tolist() for prediction in rows]
            for candidate, rows in candidates.items()
        }
        for partition, candidates in predictions.items()
    }


def _candidate_passes_gate(groups: dict[str, dict], candidate: str) -> bool:
    for group in groups.values():
        model = group["models"][candidate]
        naive = group["models"]["naive"]
        if any(
            model["aggregate"][metric] > 0.98 * naive["aggregate"][metric]
            for metric in ("mae", "wis")
        ):
            return False
        if any(
            model["per_horizon"][horizon - 1]["mae"]
            > 1.05 * naive["per_horizon"][horizon - 1]["mae"]
            for horizon in (1, 7, 30, 90, 180, 365)
        ):
            return False
    return True


def run(rows: Sequence[dict[str, object]], include_daily: bool = True):
    days, values = daily.observations(rows)
    logs = np.log(values)
    raw_origins = [index for index in _sunday_indices(days) if index >= 1095]
    raw_anchors = weekly_raw_forecasts(days, values, raw_origins)
    origins = benchmark_origins(days, raw_anchors)
    partitions = partition_origins(days, origins)
    naive_raw = {origin: np.repeat(logs[origin], 365) for origin in raw_anchors}
    price_only_raw = (
        daily.raw_forecasts(days, values, candidate="ridge")["ridge"]
        if include_daily
        else {}
    )
    predictions = {}
    for name, group_origins in partitions.items():
        predictions[name] = {
            "naive": [],
            "weekly_only": [],
            "multiscale": [],
        }
        if include_daily:
            predictions[name]["daily_price_only"] = []
        for origin in group_origins:
            result = forecast_at_origin(days, values, origin, raw_anchors)
            predictions[name]["naive"].append(
                daily.calibrated(logs, origin, naive_raw, naive=True)
            )
            predictions[name]["weekly_only"].append(result["trajectory"])
            predictions[name]["multiscale"].append(result["quantiles"])
            if include_daily:
                predictions[name]["daily_price_only"].append(
                    daily.calibrated(logs, origin, price_only_raw)
                )

    report = {
        "recipe": RECIPE,
        "model_manifest_sha256": MODEL_MANIFEST,
        "evidence": "historical_replay_revised_snapshot",
        "origins": {name: len(group) for name, group in partitions.items()},
        "groups": {},
    }
    for name, group_origins in partitions.items():
        actuals = [values[origin + HORIZONS] for origin in group_origins]
        report["groups"][name] = {
            "origins": len(group_origins),
            "first_origin": str(days[group_origins[0]]),
            "last_origin": str(days[group_origins[-1]]),
            "models": {
                candidate: daily.scores(rows_for_model, actuals)
                for candidate, rows_for_model in predictions[name].items()
            },
        }

    sunday_offsets = np.arange(6, 364, 7)
    holdout_origins = partitions["later_already_examined"]
    holdout_actuals = [
        values[origin + sunday_offsets + 1] for origin in holdout_origins
    ]
    same_sunday = {}
    for candidate, rows_for_model in predictions["later_already_examined"].items():
        same_sunday[candidate] = daily.scores(
            np.asarray(rows_for_model)[:, sunday_offsets], holdout_actuals
        )
    sunday_indices = _sunday_indices(days)
    weekly_values = values[sunday_indices]
    weekly_origin_by_daily = {
        origin: sunday_indices.index(origin) for origin in raw_anchors
    }
    legacy_raw = {
        weekly_origin_by_daily[origin]: forecast
        for origin, forecast in raw_anchors.items()
    }
    legacy_predictions = [
        weekly.calibrated(
            weekly_values,
            weekly_origin_by_daily[origin],
            legacy_raw,
        )
        for origin in holdout_origins
    ]
    same_sunday["historical_weekly"] = daily.scores(legacy_predictions, holdout_actuals)
    for score in same_sunday.values():
        for point in score["per_horizon"]:
            point["horizon_days"] *= 7
    report["same_sunday_targets"] = same_sunday
    candidates = ("weekly_only", "multiscale")
    report["shortlist"] = [
        candidate
        for candidate in candidates
        if _candidate_passes_gate(report["groups"], candidate)
    ]
    report["decision"] = (
        "further_validation_required"
        if report["shortlist"]
        else "reject_all_challengers"
    )
    report["production_ready"] = False
    return report, predictions


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--daily", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    snapshot = args.daily.read_bytes()
    sources = {}
    for source in (
        Path(__file__),
        Path(daily.__file__),
        Path(weekly.__file__),
        Path(daily_recovery.__file__),
    ):
        sources[source.name] = hashlib.sha256(source.read_bytes()).hexdigest()
        (args.output / source.name).write_bytes(source.read_bytes())
    manifest = {
        "recipe": RECIPE,
        "model_manifest_sha256": MODEL_MANIFEST,
        "snapshot_sha256": hashlib.sha256(snapshot).hexdigest(),
        "sources": sources,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    started = time.perf_counter()
    with PeakRssSampler() as sampler:
        with threadpool_limits(limits=2):
            report, predictions = run(json.loads(snapshot))
    manifest["runtime_seconds"] = time.perf_counter() - started
    manifest["peak_rss_bytes"] = sampler.peak_bytes
    (args.output / "snapshot.json").write_bytes(snapshot)
    (args.output / "manifest.json").write_bytes(daily.encode(manifest))
    (args.output / "report.json").write_bytes(daily.encode(report))
    (args.output / "predictions.json").write_bytes(
        daily.encode(prediction_archive(predictions))
    )
    print(
        json.dumps(
            {
                "decision": report["decision"],
                "shortlist": report["shortlist"],
                "origins": report["origins"],
                "runtime_seconds": manifest["runtime_seconds"],
                "peak_rss_bytes": manifest["peak_rss_bytes"],
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
