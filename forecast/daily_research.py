"""Daily targets, Monday refits, causal calibration. Development research only."""

import argparse
from datetime import date, datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path

import numpy as np
from scipy.optimize import least_squares
from threadpoolctl import threadpool_limits

from forecast import trend_research as weekly

HORIZONS = np.arange(1, 366)
QUANTILES = [0.1, 0.25, 0.5, 0.75, 0.9]
PREFIX = "development/research/daily-v1"
RECIPE = {
    "version": "daily-v1",
    "horizon_days": 365,
    "refit": "Monday 07:00 Europe/Paris, completed UTC days only",
    "holt": {
        "window_days": 728,
        "alpha": [0.01, 0.99],
        "beta": [0, 0.99],
        "phi": [0.9686250859269974, 0.9971180597404834],
    },
    "ridge": {
        "features": [
            "return_7",
            "return_30",
            "return_90",
            "return_365",
            "volatility_30",
            "volatility_90",
        ],
        "training_origins": 156,
        "minimum": 52,
        "penalty": 30,
    },
    "calibration": "last 104 mature Sunday-origin log errors per horizon, minimum 26; naive quantiles centered to keep median at last close",
    "selection": "lowest mean MAE ratio to unchanged price at days 7,30,90,180,365; only origins whose day 365 is <= 2023-09-13; candidates holt and ridge",
    "holdout": "origins >= 2023-09-14 with all 365 targets mature; not used for candidate selection",
    "weekly_comparison": "original damped-trend-v1, same origins and Sunday targets",
    "production": False,
}
MODEL_MANIFEST = hashlib.sha256(json.dumps(RECIPE, sort_keys=True).encode()).hexdigest()


def encode(value):
    return json.dumps(value, sort_keys=True, allow_nan=False).encode()


def observations(rows):
    days = [date.fromisoformat(row["date"]) for row in rows]
    values = np.asarray([row["close"] for row in rows], dtype=float)
    if len(days) < 1800 or not np.all(np.isfinite(values) & (values > 0)):
        raise ValueError("At least 1800 positive daily observations required")
    if any(b - a != timedelta(days=1) for a, b in zip(days, days[1:])):
        raise ValueError("Daily observations must be ordered, unique and gap free")
    return days, values


def holt(values):
    logs = np.log(values[-728:])

    def state(parameters):
        alpha, beta, phi = parameters
        level, slope = logs[0], 0.0
        errors = np.empty(len(logs) - 1)
        for i, value in enumerate(logs[1:]):
            prediction = level + phi * slope
            errors[i] = value - prediction
            previous = level
            level = alpha * value + (1 - alpha) * prediction
            slope = beta * (level - previous) + (1 - beta) * phi * slope
        return errors, level, slope

    result = least_squares(
        lambda p: state(p)[0],
        [0.5, 0.1, 0.98],
        bounds=([0.01, 0, 0.8 ** (1 / 7)], [0.99, 0.99, 0.98 ** (1 / 7)]),
        max_nfev=200,
    )
    if not result.success:
        raise ValueError("Daily Holt did not converge")
    _, level, slope = state(result.x)
    phi = result.x[2]
    return level + slope * phi * (1 - phi**HORIZONS) / (1 - phi)


def features(logs):
    result = np.full((len(logs), 6), np.nan)
    for i in range(365, len(logs)):
        result[i] = [
            *(logs[i] - logs[i - lag] for lag in (7, 30, 90, 365)),
            np.std(np.diff(logs[i - 30 : i + 1])),
            np.std(np.diff(logs[i - 90 : i + 1])),
        ]
    return result


def ridge(logs, x, origin, sundays):
    """Each horizon gets its own mature labels and past-only normalization."""
    output = []
    for horizon in HORIZONS:
        indices = sundays[(sundays >= 365) & (sundays + horizon <= origin)][-156:]
        if len(indices) < 52:
            raise ValueError("Insufficient mature ridge labels")
        train = x[indices]
        mean, scale = train.mean(axis=0), train.std(axis=0)
        scale = np.where(scale > 1e-12, scale, 1)
        train = (train - mean) / scale
        target = logs[indices + horizon] - logs[indices]
        coefficients = np.linalg.solve(
            train.T @ train + 30 * np.eye(6), train.T @ (target - target.mean())
        )
        output.append(
            logs[origin] + target.mean() + ((x[origin] - mean) / scale) @ coefficients
        )
    return np.asarray(output)


def calibrated(logs, origin, raw, naive=False):
    past = np.array(sorted(j for j in raw if j < origin), dtype=int)
    result = []
    for h in HORIZONS:
        mature = past[past + h <= origin][-104:]
        if len(mature) < 26:
            raise ValueError("Insufficient mature calibration errors")
        errors = logs[mature + h] - np.array([raw[j][h - 1] for j in mature])
        corrections = np.quantile(errors, QUANTILES)
        if naive:
            corrections -= corrections[2]
        result.append(np.exp(raw[origin][h - 1] + corrections))
    return np.asarray(result)


def scores(predictions, actuals):
    p, y = np.asarray(predictions), np.asarray(actuals)
    error = p[:, :, 2] - y
    interval50 = (
        p[:, :, 3]
        - p[:, :, 1]
        + 4 * np.maximum(np.maximum(p[:, :, 1] - y, y - p[:, :, 3]), 0)
    )
    interval80 = (
        p[:, :, 4]
        - p[:, :, 0]
        + 10 * np.maximum(np.maximum(p[:, :, 0] - y, y - p[:, :, 4]), 0)
    )
    arrays = {
        "mae": np.abs(error).mean(axis=0),
        "rmse": np.sqrt((error**2).mean(axis=0)),
        "wis": (0.5 * np.abs(error) + 0.25 * interval50 + 0.1 * interval80).mean(axis=0)
        / 2.5,
        "coverage_50": ((y >= p[:, :, 1]) & (y <= p[:, :, 3])).mean(axis=0),
        "coverage_80": ((y >= p[:, :, 0]) & (y <= p[:, :, 4])).mean(axis=0),
        "width_50": (p[:, :, 3] - p[:, :, 1]).mean(axis=0),
        "width_80": (p[:, :, 4] - p[:, :, 0]).mean(axis=0),
    }
    return {
        "origins": len(y),
        "aggregate": {k: float(v.mean()) for k, v in arrays.items()},
        "per_horizon": [
            {"horizon_days": i + 1, **{k: float(v[i]) for k, v in arrays.items()}}
            for i in range(y.shape[1])
        ],
    }


def raw_forecasts(days, values, latest_only=False, candidate=None):
    logs = np.log(values)
    sundays = np.array([i for i, day in enumerate(days) if day.weekday() == 6])
    origins = list(sundays[sundays >= 1095])
    if len(values) - 1 not in origins:
        origins.append(len(values) - 1)
    # Inference needs only 104 mature errors at day 365, plus current origin.
    if latest_only:
        origins = [j for j in origins if j >= len(values) - 1 - 365 - 104 * 7]
    names = [candidate] if candidate else ["holt", "ridge", "naive"]
    raw = {name: {} for name in names}
    x = features(logs) if "ridge" in names else None
    for origin in origins:
        if "holt" in raw:
            raw["holt"][origin] = holt(values[: origin + 1])
        if "ridge" in raw:
            raw["ridge"][origin] = ridge(logs, x, origin, sundays)
        if "naive" in raw:
            raw["naive"][origin] = np.repeat(logs[origin], 365)
    return raw


def benchmark(rows):
    days, values = observations(rows)
    logs = np.log(values)
    raw = raw_forecasts(days, values)
    origins = [
        j
        for j in raw["naive"]
        if days[j].weekday() == 6
        and j + 365 < len(values)
        and sum(k + 365 <= j for k in raw["naive"]) >= 26
    ]
    split = date(2023, 9, 13)
    groups = {
        "selection": [j for j in origins if days[j + 365] <= split],
        "holdout": [j for j in origins if days[j] > split],
    }
    if min(map(len, groups.values())) < 26:
        raise ValueError("Insufficient selection or holdout origins")
    predictions = {
        name: {j: calibrated(logs, j, cache, name == "naive") for j in origins}
        for name, cache in raw.items()
    }
    report = {
        "recipe": RECIPE,
        "model_manifest_sha256": MODEL_MANIFEST,
        "evidence": "historical_replay_revised_snapshot",
        "groups": {},
    }
    for group, js in groups.items():
        actuals = [values[j + HORIZONS] for j in js]
        report["groups"][group] = {
            "first_origin": str(days[js[0]]),
            "last_origin": str(days[js[-1]]),
            "models": {
                name: scores([p[j] for j in js], actuals)
                for name, p in predictions.items()
            },
        }
    selection = report["groups"]["selection"]["models"]
    landmarks = [6, 29, 89, 179, 364]
    ratios = {
        name: float(
            np.mean(
                [
                    selection[name]["per_horizon"][h]["mae"]
                    / selection["naive"]["per_horizon"][h]["mae"]
                    for h in landmarks
                ]
            )
        )
        for name in ("holt", "ridge")
    }
    report["selected"] = min(ratios, key=ratios.get)
    report["selection_ratios"] = ratios
    # Original weekly model, evaluated only on the very same Sunday targets.
    weekly_values = values[[i for i, day in enumerate(days) if day.weekday() == 6]]
    weekly_raw = {
        i: weekly.fit(weekly_values[: i + 1])[0] for i in range(103, len(weekly_values))
    }
    js = groups["holdout"]
    sunday0 = next(i for i, day in enumerate(days) if day.weekday() == 6)
    weekly_predictions = [
        weekly.calibrated(weekly_values, (j - sunday0) // 7, weekly_raw) for j in js
    ]
    sunday_indices = np.arange(6, 364, 7)
    actuals = np.asarray([values[j + HORIZONS] for j in js])[:, sunday_indices]
    comparison = {
        name: scores(np.asarray([p[j] for j in js])[:, sunday_indices], actuals)
        for name, p in predictions.items()
    }
    comparison["weekly"] = scores(weekly_predictions, actuals)
    for model in comparison.values():
        for point in model["per_horizon"]:
            point["horizon_days"] *= 7
    report["same_sunday_targets"] = comparison
    report["production_ready"] = False
    return report


def emission(rows, now, candidate):
    days, values = observations(rows)
    if now.utcoffset() != timedelta(0) or days[-1] != now.date() - timedelta(days=1):
        raise ValueError("Latest completed UTC day required; no backdated issuance")
    if any(datetime.fromisoformat(row["observed_at"]) > now for row in rows):
        raise ValueError("Future ingestion timestamp")
    raw = raw_forecasts(days, values, latest_only=True, candidate=candidate)[candidate]
    points = calibrated(np.log(values), len(values) - 1, raw)
    return {
        "created_at": now.isoformat(),
        "origin_date": str(days[-1]),
        "origin_week": str(days[-1] - timedelta(days=days[-1].weekday())),
        "origin_close": float(values[-1]),
        "currency": "USD",
        "frequency": "daily",
        "candidate": candidate,
        "evidence": "prospective",
        "model_manifest_sha256": MODEL_MANIFEST,
        "points": [
            {
                "horizon_days": int(h),
                "target_date": str(days[-1] + timedelta(days=int(h))),
                "USD": p.tolist(),
            }
            for h, p in zip(HORIZONS, points)
        ],
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--daily", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    output = Path(args.output)
    output.mkdir(parents=True, exist_ok=False)
    source = Path(args.daily).read_bytes()
    manifest = {
        "recipe": RECIPE,
        "model_manifest_sha256": MODEL_MANIFEST,
        "snapshot_sha256": hashlib.sha256(source).hexdigest(),
        "code_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    (output / "manifest.json").write_bytes(encode(manifest))
    with threadpool_limits(limits=2):
        report = benchmark(json.loads(source))
    (output / "report.json").write_bytes(encode(report))
    print(
        json.dumps(
            {
                "selected": report["selected"],
                "selection_ratios": report["selection_ratios"],
                "holdout": {
                    name: s["aggregate"]
                    for name, s in report["groups"]["holdout"]["models"].items()
                },
            }
        )
    )


if __name__ == "__main__":
    main()
