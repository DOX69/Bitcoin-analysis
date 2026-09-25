"""Local, causal damped-trend preview. Never promotes a production model."""

import argparse
from datetime import date, datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path

import numpy as np
from scipy.optimize import least_squares

from forecast import benchmark as b

WINDOW = 104
CALIBRATION = 156
PREFIX = "development/research/damped-trend-v1"
RECIPE = {
    "model": "damped-trend-v1",
    "window": WINDOW,
    "fit": "Holt damped trend on log prices; least squares one-step errors",
    "bounds": {"alpha": [0.01, 0.99], "beta": [0.0, 0.99], "phi": [0.8, 0.98]},
    "initialization": "first log price, zero slope; initial states held fixed",
    "calibration": "last 156 mature rolling-origin log errors per horizon; minimum 52",
    "quantiles": list(b.QUANTILES),
    "evaluation": "rolling origins 348 through min(528,last_index-52), refit each origin",
    "production": False,
}
MODEL_MANIFEST = hashlib.sha256(json.dumps(RECIPE, sort_keys=True).encode()).hexdigest()


def fit(closes):
    """Fit only the supplied observations, never an unseen future suffix."""
    values = np.asarray(closes, dtype=float)
    if len(values) < WINDOW or not np.all(np.isfinite(values) & (values > 0)):
        raise ValueError("104 finite positive closes required")
    logs = np.log(values[-WINDOW:])

    def filter_state(parameters):
        alpha, beta, phi = parameters
        level, slope = logs[0], 0.0
        errors = []
        for value in logs[1:]:
            prediction = level + phi * slope
            errors.append(value - prediction)
            previous = level
            level = alpha * value + (1 - alpha) * prediction
            slope = beta * (level - previous) + (1 - beta) * phi * slope
        return np.asarray(errors), level, slope

    result = least_squares(
        lambda parameters: filter_state(parameters)[0],
        [0.5, 0.1, 0.9],
        bounds=([0.01, 0, 0.8], [0.99, 0.99, 0.98]),
        max_nfev=200,
    )
    if not result.success:
        raise ValueError("Trend optimization did not converge")
    _, level, slope = filter_state(result.x)
    phi = result.x[2]
    horizons = np.arange(1, 53)
    predictions = level + slope * phi * (1 - phi**horizons) / (1 - phi)
    return predictions, {
        "alpha": float(result.x[0]),
        "beta": float(result.x[1]),
        "phi": float(phi),
        "level": float(level),
        "slope": float(slope),
    }


def calibrated(closes, origin, forecasts):
    """Use errors only after their actual target has been observed."""
    points = []
    for horizon in range(1, 53):
        last = origin - horizon
        first = max(WINDOW - 1, last - CALIBRATION + 1)
        if last - first + 1 < 52:
            raise ValueError("52 mature calibration errors per horizon required")
        errors = [
            np.log(closes[j + horizon]) - forecasts[j][horizon - 1]
            for j in range(first, last + 1)
        ]
        points.append(
            np.exp(
                forecasts[origin][horizon - 1] + np.quantile(errors, b.QUANTILES)
            ).tolist()
        )
    return points


def run(daily, now):
    monday = now.date() - timedelta(days=now.weekday())
    if now.utcoffset() != timedelta(0) or any(
        date.fromisoformat(row["date"]) >= monday for row in daily
    ):
        raise ValueError("UTC and completed weeks required")
    weekly = b.aggregate_daily_rows(daily)
    if date.fromisoformat(weekly[-1]["date"]) != monday - timedelta(weeks=1):
        raise ValueError("Latest completed week missing")
    closes = [float(row["close"]) for row in weekly]
    forecasts, parameters = {}, {}
    for origin in range(WINDOW - 1, len(closes)):
        forecasts[origin], parameters[origin] = fit(closes[: origin + 1])
    origins = list(range(348, min(529, len(closes) - 52)))
    if not origins:
        raise ValueError("Historical evaluation period missing")
    predictions = [calibrated(closes, origin, forecasts) for origin in origins]
    actuals = b._actuals(closes, origins)
    metrics, per_horizon = b._score(predictions, actuals)
    baseline = [[[closes[origin]] * 5 for _ in range(52)] for origin in origins]
    baseline_metrics, baseline_horizons = b._score(baseline, actuals)
    report = {
        "evidence": "historical_replay",
        "publishable": False,
        "origins": len(origins),
        "metrics": metrics,
        "baseline": baseline_metrics,
        "per_horizon": per_horizon,
        "baseline_per_horizon": baseline_horizons,
        "limitations": "Previously inspected history; overlapping targets; no independent prospective validation.",
    }
    last = len(closes) - 1
    quantiles = calibrated(closes, last, forecasts)
    origin_date = date.fromisoformat(weekly[-1]["date"])
    document = {
        "created_at": now.isoformat(),
        "origin_week": origin_date.isoformat(),
        "origin_close": closes[-1],
        "currency": "USD",
        "evidence": "prospective",
        "model_manifest_sha256": MODEL_MANIFEST,
        "quantiles": list(b.QUANTILES),
        "fit_parameters": parameters[last],
        "points": [
            {
                "horizon_weeks": h,
                "target_date": (origin_date + timedelta(days=6, weeks=h)).isoformat(),
                "USD": row,
            }
            for h, row in enumerate(quantiles, 1)
        ],
    }
    if any(
        date.fromisoformat(point["target_date"]) <= now.date()
        for point in document["points"]
    ):
        raise ValueError("All emission targets must still be in the future")
    return (
        document,
        report,
        {"origins": origins, "predictions": predictions, "actuals": actuals},
    )


def main():
    import psutil
    from threadpoolctl import threadpool_limits
    from forecast.artifacts import dependencies

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--daily", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    process = psutil.Process()
    process.cpu_affinity(process.cpu_affinity()[:2])
    manifest = {
        "recipe": RECIPE,
        "recipe_sha256": MODEL_MANIFEST,
        "source_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "snapshot_sha256": hashlib.sha256(args.daily.read_bytes()).hexdigest(),
        "dependencies": dependencies(),
    }
    (args.output / "manifest.json").write_text(json.dumps(manifest, indent=2))
    with threadpool_limits(limits=2):
        document, report, replay = run(
            json.loads(args.daily.read_text()), datetime.now(timezone.utc)
        )
    for name, value in (("emission", document), ("report", report), ("replay", replay)):
        (args.output / f"{name}.json").write_text(
            json.dumps(value, allow_nan=False, indent=2)
        )
    print(
        json.dumps(
            {
                "metrics": report["metrics"],
                "baseline": report["baseline"],
                "origins": report["origins"],
                "manifest": MODEL_MANIFEST,
                "first": document["points"][0],
                "last": document["points"][-1],
            }
        )
    )


if __name__ == "__main__":
    main()
