import copy

import numpy as np

from forecast import daily_recovery as recovery


def groups(ratio):
    baseline = {
        "aggregate": {"mae": 100, "wis": 50},
        "per_horizon": [{"mae": 100} for _ in range(365)],
    }
    candidate = {
        "aggregate": {"mae": 100 * ratio, "wis": 50 * ratio},
        "per_horizon": [{"mae": 100 * ratio} for _ in range(365)],
    }
    return {
        g: {
            "models": {
                "naive": copy.deepcopy(baseline),
                "ridge_centered": copy.deepcopy(candidate),
                "ridge_fading_30": copy.deepcopy(candidate),
            }
        }
        for g in ("earlier", "later")
    }


def test_selection_can_reject_every_challenger_instead_of_choosing_the_least_bad():
    assert recovery.shortlist(groups(1.2)) == []
    assert recovery.shortlist(groups(1)) == []


def test_average_gain_cannot_hide_a_failed_period_or_horizon():
    data = groups(0.9)
    data["later"]["models"]["ridge_centered"]["per_horizon"][364]["mae"] = 110
    data["earlier"]["models"]["ridge_fading_30"]["aggregate"]["wis"] = 60
    assert recovery.shortlist(data) == []
    assert recovery.shortlist(groups(0.9)) == ["ridge_centered", "ridge_fading_30"]


def test_centering_preserves_raw_median_and_uses_only_mature_errors():
    logs = np.log(100 + np.arange(2200))
    raw = {j: np.repeat(logs[j], 365) for j in range(0, 2200, 7)}
    result = recovery.centered_calibration(logs, 1750, raw)
    np.testing.assert_allclose(result[:, 2], np.exp(raw[1750]))
    logs[1751:] += 5
    np.testing.assert_array_equal(
        result, recovery.centered_calibration(logs, 1750, raw)
    )
    assert np.all(np.diff(result, axis=1) >= 0)
