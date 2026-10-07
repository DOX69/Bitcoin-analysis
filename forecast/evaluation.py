"""Shared contracts for frozen, final and prospective forecast evidence."""

from __future__ import annotations

from datetime import date, timedelta
import hashlib
import json
import math
import statistics
from typing import Any, Sequence

from forecast import benchmark as b

EVIDENCE_SOURCES = ("selection", "final_holdout", "prospective")
FINAL_HOLDOUT = "final_holdout"
MINIMUM_PROSPECTIVE_ORIGINS = 104
MINIMUM_DEPENDENCE_BLOCKS = 2
SCORING_RULES = {
    "mae": "absolute error of the median",
    "rmse": "root mean squared error of the median",
    "wis": "(0.5*median absolute error + 0.25*IS_0.5 + 0.10*IS_0.2)/2.5",
    "coverage_50": "actual inside q0.25..q0.75",
    "coverage_80": "actual inside q0.10..q0.90",
    "paired_delta": "model metric minus baseline metric on the same origin",
}


def unavailable_final_holdout(reason: str, *, horizon: int = b.MAX_HORIZON) -> dict:
    """Return an explicit non-available partition instead of inventing a holdout."""
    if not reason.strip():
        raise ValueError("A reason is required when final_holdout is unavailable")
    return {
        "name": FINAL_HOLDOUT,
        "status": "not_available",
        "reason": reason,
        "horizon": horizon,
        "origins": 0,
        "read_only_after_scores": True,
    }


def make_final_holdout(
    rows: Sequence[dict[str, Any]],
    *,
    train_end: int,
    origin_start: int,
    origin_end: int,
    horizon: int,
    selection_origin_end: int | None = None,
) -> dict:
    """Freeze an explicit, disjoint and fully mature final-holdout range."""
    if horizon < 1:
        raise ValueError("Final holdout horizon must be positive")
    if not (0 <= train_end <= origin_start < origin_end <= len(rows)):
        raise ValueError("Invalid final_holdout index range")
    if selection_origin_end is not None and origin_start < selection_origin_end:
        raise ValueError("final_holdout origins must be disjoint from selection")
    if origin_end + horizon > len(rows):
        raise ValueError("Final holdout requires mature targets")
    return {
        "name": FINAL_HOLDOUT,
        "status": "available",
        "train_end": train_end,
        "origin_start": origin_start,
        "origin_end": origin_end,
        "origins": origin_end - origin_start,
        "horizon": horizon,
        "target_end": origin_end - 1 + horizon,
        "read_only_after_scores": True,
        "selection_locked": True,
    }


def validate_final_holdout(
    partition: dict[str, Any],
    *,
    row_count: int,
    horizon: int,
    selection_origin_end: int | None = None,
) -> None:
    if partition.get("name") != FINAL_HOLDOUT:
        raise ValueError("Expected a final_holdout partition")
    if partition.get("status") == "not_available":
        if (
            not partition.get("reason")
            or partition.get("read_only_after_scores") is not True
        ):
            raise ValueError("Unavailable final_holdout must explain its status")
        return
    if partition.get("status") != "available":
        raise ValueError("Unknown final_holdout status")
    if partition.get("horizon") != horizon:
        raise ValueError("Final holdout horizon differs from the frozen contract")
    try:
        train_end = int(partition["train_end"])
        origin_start = int(partition["origin_start"])
        origin_end = int(partition["origin_end"])
    except (KeyError, TypeError, ValueError) as error:
        raise ValueError("Incomplete final_holdout range") from error
    expected = make_final_holdout(
        [{"date": "1970-01-01", "close": 1.0}] * row_count,
        train_end=train_end,
        origin_start=origin_start,
        origin_end=origin_end,
        horizon=horizon,
        selection_origin_end=selection_origin_end,
    )
    for key in ("origins", "target_end", "train_end", "origin_start", "origin_end"):
        if partition.get(key) != expected[key]:
            raise ValueError("Final holdout range is not frozen")
    if (
        partition.get("read_only_after_scores") is not True
        or partition.get("selection_locked") is not True
    ):
        raise ValueError("Final holdout must be read-only and selection-locked")


def probabilistic_last_close_reference(
    closes: Sequence[float],
    origin: int,
    *,
    horizon_count: int = b.MAX_HORIZON,
    quantiles: Sequence[float] = b.QUANTILES,
) -> list[list[float]]:
    """Evaluation-only zero-drift random-walk bands using past returns only."""
    if not 1 <= origin < len(closes) or horizon_count < 1:
        raise ValueError("Invalid probabilistic baseline origin or horizon")
    if any(not math.isfinite(value) or value <= 0 for value in closes[: origin + 1]):
        raise ValueError("Probabilistic baseline requires positive finite history")
    returns = [
        math.log(closes[index] / closes[index - 1]) for index in range(1, origin + 1)
    ]
    sigma = max(statistics.pstdev(returns), 1e-9)
    normal = statistics.NormalDist()
    current = math.log(closes[origin])
    rows = [
        [
            math.exp(
                current + sigma * math.sqrt(horizon) * normal.inv_cdf(float(quantile))
            )
            for quantile in quantiles
        ]
        for horizon in range(1, horizon_count + 1)
    ]
    if any(row != sorted(row) for row in rows):
        raise ValueError("Probabilistic baseline quantiles are not ordered")
    return rows


def _mean_metric(rows: Sequence[dict[str, float]], key: str) -> float | None:
    return statistics.mean(row[key] for row in rows) if rows else None


def _direction(actual: float, origin_close: float) -> str:
    if actual > origin_close:
        return "up"
    if actual < origin_close:
        return "down"
    return "flat"


def realized_regime(actual: float, origin_close: float) -> str:
    """Label the realized direction for descriptive, non-independent reporting."""
    return _direction(actual, origin_close)


def _rows_for_indices(
    predictions: Sequence[Sequence[Sequence[float]]],
    baseline: Sequence[Sequence[Sequence[float]]],
    actuals: Sequence[Sequence[float]],
    origins: Sequence[int],
    weekly: Sequence[dict[str, Any]],
    horizon_index: int,
    indices: Sequence[int],
) -> list[dict[str, float | str]]:
    result = []
    for index in indices:
        actual = float(actuals[index][horizon_index])
        prediction = predictions[index][horizon_index]
        reference = baseline[index][horizon_index]
        origin_close = float(weekly[origins[index]]["close"])
        result.append(
            {
                "mae": abs(actual - prediction[2]),
                "wis": b._wis(actual, prediction),
                "coverage_50": float(prediction[1] <= actual <= prediction[3]),
                "coverage_80": float(prediction[0] <= actual <= prediction[4]),
                "baseline_mae": abs(actual - reference[2]),
                "baseline_wis": b._wis(actual, reference),
                "baseline_coverage_50": float(reference[1] <= actual <= reference[3]),
                "baseline_coverage_80": float(reference[0] <= actual <= reference[4]),
                "mae_delta": abs(actual - prediction[2]) - abs(actual - reference[2]),
                "wis_delta": b._wis(actual, prediction) - b._wis(actual, reference),
                "regime": _direction(actual, origin_close),
            }
        )
    return result


def _summary(rows: Sequence[dict[str, float | str]]) -> dict[str, float | int | None]:
    return {
        "origins": len(rows),
        **{
            key: _mean_metric(rows, key)
            for key in (
                "mae",
                "wis",
                "coverage_50",
                "coverage_80",
                "baseline_mae",
                "baseline_wis",
                "baseline_coverage_50",
                "baseline_coverage_80",
                "mae_delta",
                "wis_delta",
            )
        },
    }


def score_partition(
    predictions: Sequence[Sequence[Sequence[float]]],
    probabilistic_baseline: Sequence[Sequence[Sequence[float]]],
    actuals: Sequence[Sequence[float]],
    origins: Sequence[int],
    weekly: Sequence[dict[str, Any]],
    *,
    evidence_source: str = FINAL_HOLDOUT,
) -> dict[str, Any]:
    """Score one immutable origin set with central and probabilistic baselines."""
    if evidence_source not in EVIDENCE_SOURCES:
        raise ValueError("Unknown evidence source")
    if (
        not predictions
        or len(predictions) != len(actuals)
        or len(origins) != len(actuals)
    ):
        raise ValueError(
            "Partition predictions, actuals and origins must have equal size"
        )
    central = [
        b.last_close_reference([row["close"] for row in weekly], origin)
        for origin in origins
    ]
    model_metrics, model_horizons = b._score(predictions, actuals)
    central_metrics, central_horizons = b._score(central, actuals)
    probability_metrics, probability_horizons = b._score(
        probabilistic_baseline, actuals
    )
    per_horizon = []
    for horizon_index, (model, reference, probability) in enumerate(
        zip(model_horizons, central_horizons, probability_horizons)
    ):
        rows = _rows_for_indices(
            predictions,
            probabilistic_baseline,
            actuals,
            origins,
            weekly,
            horizon_index,
            list(range(len(origins))),
        )
        blocks = []
        for start in range(0, len(rows), horizon_index + 1):
            indices = list(range(start, min(start + horizon_index + 1, len(rows))))
            block_rows = [rows[index] for index in indices]
            contiguous = all(
                date.fromisoformat(str(weekly[origins[right]]["date"]))
                - date.fromisoformat(str(weekly[origins[left]]["date"]))
                == timedelta(weeks=1)
                for left, right in zip(indices, indices[1:])
            )
            blocks.append(
                {
                    "first_origin_week": weekly[origins[start]]["date"],
                    "last_origin_week": weekly[origins[indices[-1]]]["date"],
                    "origins": len(block_rows),
                    "complete_contiguous": len(block_rows) == horizon_index + 1
                    and contiguous,
                    **_summary(block_rows),
                }
            )
        rolling = []
        for width in sorted(
            {min(26, len(rows)), min(52, len(rows)), min(104, len(rows))}
        ):
            window = rows[-width:]
            rolling.append({"window_origins": width, **_summary(window)})
        by_regime = {
            regime: _summary([row for row in rows if row["regime"] == regime])
            for regime in ("up", "down", "flat")
            if any(row["regime"] == regime for row in rows)
        }
        per_horizon.append(
            {
                **model,
                "baseline_last_close": reference,
                "baseline_probabilistic": probability,
                "paired_delta": {
                    "last_close": {
                        "mae": model["mae"] - reference["mae"],
                        "wis": model["wis"] - reference["wis"],
                    },
                    "probabilistic": {
                        "mae": model["mae"] - probability["mae"],
                        "wis": model["wis"] - probability["wis"],
                    },
                },
                "dependence_blocks": blocks,
                "rolling": rolling,
                "by_regime": by_regime,
            }
        )
    return {
        "evidence_source": evidence_source,
        "scoring_rules": SCORING_RULES,
        "metrics": model_metrics,
        "baseline_metrics": central_metrics,
        "baseline_probabilistic": {
            "metrics": probability_metrics,
            "per_horizon": probability_horizons,
        },
        "baseline_probabilistic_metrics": probability_metrics,
        "per_horizon": per_horizon,
    }


def version_signature(contract: dict[str, Any]) -> str:
    """Hash only the forecast contract, so every behavioral change gets a version."""
    fields = {
        key: contract.get(key)
        for key in (
            "model",
            "candidate",
            "features",
            "variables",
            "target",
            "horizons",
            "quantiles",
            "parameters",
            "calibration",
        )
    }
    if "calibration" not in contract and "recalibration" in contract:
        fields["calibration"] = contract.get("recalibration")
    return hashlib.sha256(
        json.dumps(
            fields, sort_keys=True, separators=(",", ":"), allow_nan=False
        ).encode()
    ).hexdigest()


def require_new_version(previous: dict[str, Any], current: dict[str, Any]) -> str:
    previous_version = previous.get("version") or version_signature(previous)
    current_version = current.get("version") or version_signature(current)
    changed = any(
        previous.get(key) != current.get(key)
        for key in (
            "model",
            "candidate",
            "features",
            "variables",
            "target",
            "horizons",
            "quantiles",
            "parameters",
            "calibration",
            "recalibration",
        )
    )
    if changed and previous_version == current_version:
        raise ValueError("Forecast contract changed without a new version")
    if not changed and previous_version != current_version:
        raise ValueError("Forecast version changed without a contract change")
    return current_version


def target_is_mature(target: date, now: date) -> bool:
    """Targets at the current UTC date are still incomplete."""
    return target < now
