"""Portable forecast artifacts: JSON and native LightGBM text, never pickle."""

from __future__ import annotations

import json
import math
import platform
from datetime import date, timedelta
from importlib.metadata import version
from pathlib import Path

from forecast import benchmark as b

FEATURES = (
    ["log_close"]
    + [f"log_return_{lag}w" for lag in b.LOOKBACKS]
    + [f"log_return_population_std_{window}w" for window in (4, 13, 26)]
)
RELOAD_TOLERANCE = {"rtol": 1e-10, "atol": 1e-8}
CANDIDATES = {
    c.name: c
    for c in (
        b.PersistenceCandidate,
        b.GaussianRandomWalkCandidate,
        b.LightGBMQuantileCandidate,
    )
}


def dependencies():
    return {
        "python": platform.python_version(),
        **{
            name: version(name)
            for name in ("lightgbm", "numpy", "scikit-learn", "scipy", "psutil")
        },
    }


def write_json(path: Path, value):
    # Exclusive creation prevents accidental replacement of a published artifact.
    with path.open("x", encoding="utf-8") as handle:
        json.dump(value, handle, indent=2, sort_keys=True, allow_nan=False)
        handle.write("\n")


def validate_prediction(prediction):
    if len(prediction) != 52 or any(len(row) != 5 for row in prediction):
        raise ValueError("Expected 52 horizons with five quantiles")
    for row in prediction:
        if any(not math.isfinite(v) or v <= 0 for v in row) or list(row) != sorted(row):
            raise ValueError("Quantiles must be finite, positive and ordered")
    return prediction


def save_model(candidate, directory: Path, context: dict):
    directory.mkdir(parents=True, exist_ok=False)
    if candidate.name == "lightgbm_quantile":
        for h, models in enumerate(candidate.models, 1):
            for q, model in zip(b.QUANTILES, models):
                model.booster_.save_model(
                    str(directory / f"h{h:02d}-q{int(q*100):02d}.txt")
                )
    else:
        state = (
            {"train_end": candidate.train_end}
            if candidate.name == "price_unchanged"
            else {
                "mu": candidate.mu,
                "sigma": candidate.sigma,
            }
        )
        write_json(directory / "state.json", state)
    manifest = {
        "schema_version": 1,
        "candidate": candidate.name,
        "target": "BTC/USD ISO Sunday close",
        "quantiles": list(b.QUANTILES),
        "horizons": list(range(1, 53)),
        "features": FEATURES,
        "recalibration": None,
        "reload_tolerance": RELOAD_TOLERANCE,
        "dependencies": dependencies(),
        "context": context,
        "files": {p.name: b._file_sha256(p) for p in sorted(directory.iterdir())},
    }
    write_json(directory / "manifest.json", manifest)
    return manifest


def load_model(directory: Path):
    manifest = json.loads((directory / "manifest.json").read_text(encoding="utf-8"))
    if (
        manifest["schema_version"] != 1
        or manifest["recalibration"] is not None
        or manifest["features"] != FEATURES
        or manifest["quantiles"] != list(b.QUANTILES)
        or manifest["horizons"] != list(range(1, 53))
    ):
        raise ValueError("Unsupported model contract")
    if manifest["dependencies"] != dependencies():
        raise ValueError("Model dependencies differ from the frozen environment")
    name = manifest["candidate"]
    expected = (
        {f"h{h:02d}-q{int(q*100):02d}.txt" for h in range(1, 53) for q in b.QUANTILES}
        if name == "lightgbm_quantile"
        else {"state.json"}
    )
    if set(manifest["files"]) != expected:
        raise ValueError("Model integrity: unexpected file list")
    for filename, digest in manifest["files"].items():
        path = directory / filename
        if not path.is_file() or b._file_sha256(path) != digest:
            raise ValueError(f"Model integrity check failed: {filename}")
    candidate = CANDIDATES[name]()
    if name == "lightgbm_quantile":
        import lightgbm

        candidate.models = [
            [
                lightgbm.Booster(
                    model_file=str(directory / f"h{h:02d}-q{int(q*100):02d}.txt")
                )
                for q in b.QUANTILES
            ]
            for h in range(1, 53)
        ]
    else:
        state = json.loads((directory / "state.json").read_text(encoding="utf-8"))
        if name == "price_unchanged":
            candidate.train_end = int(state["train_end"])
        else:
            candidate.mu, candidate.sigma = float(state["mu"]), float(state["sigma"])
            if (
                not math.isfinite(candidate.mu)
                or not math.isfinite(candidate.sigma)
                or candidate.sigma <= 0
            ):
                raise ValueError("Invalid Gaussian state")
    return candidate


def verify_reload(candidate, directory: Path, closes, origins):
    import numpy as np

    loaded = load_model(directory)
    for origin in origins:
        expected = validate_prediction(candidate.predict(closes, origin))
        actual = validate_prediction(loaded.predict(closes, origin))
        np.testing.assert_allclose(actual, expected, **RELOAD_TOLERANCE)


def emit_forecast(candidate, weekly, emission_date: str, fx: dict | None = None):
    from forecast.pipeline import validate_weekly

    validate_weekly(weekly)
    cutoff = date.fromisoformat(emission_date)
    last_monday = date.fromisoformat(weekly[-1]["date"])
    if cutoff < last_monday + timedelta(days=7):
        raise ValueError("Emission precedes completion of the last ISO week")
    rates = {"USD": 1.0}
    for currency, value in (fx or {}).items():
        if (
            currency not in ("EUR", "CHF")
            or date.fromisoformat(value["date"]) > cutoff
            or not math.isfinite(value["rate"])
            or value["rate"] <= 0
        ):
            raise ValueError("FX must be a positive EUR/CHF rate known at emission")
        rates[currency] = value["rate"]
    closes = [row["close"] for row in weekly]
    predictions = validate_prediction(candidate.predict(closes, len(closes) - 1))
    points = []
    for h, row in enumerate(predictions, 1):
        converted = {
            currency: [v * rate for v in row] for currency, rate in rates.items()
        }
        if any(
            not math.isfinite(v) or v <= 0
            for values in converted.values()
            for v in values
        ):
            raise ValueError("Invalid converted quantile")
        points.append(
            {
                "horizon_weeks": h,
                "target_date": (last_monday + timedelta(days=6, weeks=h)).isoformat(),
                **converted,
            }
        )
    return {
        "emission_date": emission_date,
        "origin_week": weekly[-1]["date"],
        "quantiles": list(b.QUANTILES),
        "fx": fx or {},
        "points": points,
    }
