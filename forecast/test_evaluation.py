from datetime import date, timedelta

import pytest

from forecast import benchmark as b
from forecast import evaluation


def weekly_rows(count=120):
    start = date(2020, 1, 6)
    return [
        {"date": (start + timedelta(weeks=index)).isoformat(), "close": 100.0 + index}
        for index in range(count)
    ]


def test_probabilistic_last_close_reference_is_causal_and_ordered():
    closes = [100.0 + index for index in range(80)]
    before = evaluation.probabilistic_last_close_reference(closes, 40)
    closes[41:] = [10_000.0] * (len(closes) - 41)
    after = evaluation.probabilistic_last_close_reference(closes, 40)

    assert after == before
    assert all(row == sorted(row) for row in after)
    assert all(row[2] == pytest.approx(closes[40]) for row in after)


def test_final_holdout_requires_a_disjoint_mature_range():
    rows = weekly_rows(140)
    selection_end = 72
    final = evaluation.make_final_holdout(
        rows,
        train_end=72,
        origin_start=72,
        origin_end=80,
        horizon=52,
        selection_origin_end=selection_end,
    )
    assert final["name"] == "final_holdout"
    assert final["status"] == "available"
    assert final["origin_end"] == 80

    with pytest.raises(ValueError, match="disjoint"):
        evaluation.make_final_holdout(
            rows,
            train_end=70,
            origin_start=71,
            origin_end=80,
            horizon=52,
            selection_origin_end=selection_end,
        )
    with pytest.raises(ValueError, match="mature"):
        evaluation.make_final_holdout(
            rows,
            train_end=72,
            origin_start=80,
            origin_end=90,
            horizon=52,
            selection_origin_end=selection_end,
        )


def test_score_partition_keeps_paired_baseline_blocks_and_rolling_metrics():
    rows = weekly_rows()
    origins = list(range(60, 64))
    actuals = b._actuals([row["close"] for row in rows], origins)
    predictions = [
        b.last_close_reference([row["close"] for row in rows], origin)
        for origin in origins
    ]
    baseline = [
        evaluation.probabilistic_last_close_reference(
            [row["close"] for row in rows], origin
        )
        for origin in origins
    ]

    result = evaluation.score_partition(predictions, baseline, actuals, origins, rows)

    assert result["evidence_source"] == "final_holdout"
    assert len(result["per_horizon"]) == 52
    assert "baseline_probabilistic" in result
    assert "paired_delta" in result["per_horizon"][0]
    assert result["per_horizon"][0]["dependence_blocks"]
    assert result["per_horizon"][0]["rolling"]
    assert result["per_horizon"][0]["by_regime"]


def test_contract_changes_require_a_new_version():
    previous = {
        "candidate": "ridge",
        "features": ["return_7"],
        "target": "close",
        "horizons": [1, 365],
        "quantiles": [0.1, 0.5, 0.9],
        "calibration": "none",
    }
    current = {**previous, "features": ["return_7", "return_30"]}

    assert evaluation.version_signature(previous) != evaluation.version_signature(
        current
    )
    with pytest.raises(ValueError, match="new version"):
        evaluation.require_new_version(
            {**previous, "version": "same"},
            {**current, "version": "same"},
        )
