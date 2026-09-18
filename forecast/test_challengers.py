import math

import pytest

from forecast import challengers


@pytest.mark.parametrize("recipe", challengers.RECIPES)
def test_challenger_is_causal_and_quantiles_are_valid(recipe):
    closes = [100 * math.exp(i * 0.001 + 0.1 * math.sin(i / 9)) for i in range(450)]
    original = challengers.predict(recipe, closes, 350)
    changed = closes[:351] + [1e9] * 99
    assert challengers.predict(recipe, changed, 350) == original
    assert len(original) == 52
    for row in original:
        assert len(row) == 5
        assert row == sorted(row)
        assert all(math.isfinite(value) and value > 0 for value in row)
    if recipe != "shrink_drift_01":
        assert all(row[2] == pytest.approx(closes[350]) for row in original)


def test_empirical_band_uses_mature_horizon_returns_only():
    closes = [100.0] * 351
    closes[350] = 200.0
    prediction = challengers.predict("empirical_abs_156", closes, 350)
    assert prediction[-1][2] == pytest.approx(200.0)
    assert prediction[-1][0] < prediction[-1][4]


def test_unknown_recipe_is_rejected():
    with pytest.raises(ValueError):
        challengers.predict("adaptive_after_scores", [100.0] * 400, 399)
