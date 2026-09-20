from datetime import date, timedelta

import numpy as np
import pytest

from forecast import chronos2_daily_research as research


def rows(count=1500):
    start = date(2015, 1, 1)
    return [
        {
            "date": str(start + timedelta(days=index)),
            "open": 100 + index,
            "high": 102 + index,
            "low": 99 + index,
            "close": 101 + index,
            "volume": float(index),
            "observed_at": "2026-09-17T05:00:00+00:00",
        }
        for index in range(count)
    ]


def test_context_contains_only_complete_origin_and_three_log_channels():
    values = np.asarray(
        [
            [row[key] for key in ("open", "high", "low", "close", "volume")]
            for row in rows(1200)
        ],
        dtype=float,
    )
    context = research.multivariate_context(values, 1000, limit=4)
    assert context.shape == (3, 4)
    assert context[0, -1] == pytest.approx(np.log(values[1000, 3]))
    assert context[1, -1] == pytest.approx(np.log1p(values[1000, 4]))
    assert context[2, -1] == pytest.approx(np.log(values[1000, 1] / values[1000, 2]))
    changed = values.copy()
    changed[1001:, 3:] *= 100
    np.testing.assert_array_equal(
        context, research.multivariate_context(changed, 1000, limit=4)
    )


def test_quantiles_require_monotone_daily_close_output():
    values = np.log(np.arange(1, research.HORIZON + 1, dtype=float))[:, None]
    valid = np.repeat(values, len(research.QUANTILES), axis=1)
    assert research.quantiles_to_usd(valid).shape == (
        research.HORIZON,
        len(research.QUANTILES),
    )
    crossed = valid.copy()
    crossed[:, 1] = crossed[:, 0] - 1
    with pytest.raises(ValueError, match="crossed"):
        research.quantiles_to_usd(crossed)


def test_naive_reference_uses_only_mature_prior_sunday_origins():
    log_closes = np.log(np.arange(1, 5000, dtype=float))
    origins = list(range(100, 5000, 7))
    reference = research.naive_quantiles(log_closes, 1000, origins)
    assert reference.shape == (research.HORIZON, len(research.QUANTILES))
    assert np.all(np.diff(reference, axis=1) >= 0)
    with pytest.raises(ValueError, match="Insufficient"):
        research.naive_quantiles(log_closes, 200, origins)


def test_selection_gate_requires_both_partitions_and_landmarks():
    passing = {
        "earlier": {
            "ratios": {"mae": 0.9, "wis": 0.9},
            "landmarks": {str(h): {"mae_ratio": 1.0} for h in research.LANDMARKS},
        },
        "later": {
            "ratios": {"mae": 0.9, "wis": 0.9},
            "landmarks": {str(h): {"mae_ratio": 1.0} for h in research.LANDMARKS},
        },
    }
    assert research.passes_gate(passing)
    passing["later"]["landmarks"]["365"]["mae_ratio"] = 1.06
    assert not research.passes_gate(passing)
