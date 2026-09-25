import math

import pytest

from forecast import regime_research as research


@pytest.mark.parametrize("recipe", research.RECIPES)
def test_predictions_use_only_known_prices_and_scale_with_currency(recipe):
    closes = [100 * math.exp(i * 0.001 + 0.12 * math.sin(i / 9)) for i in range(400)]
    expected = research.predict(recipe, closes, 320)
    assert research.predict(recipe, closes[:321] + [1e12] * 79, 320) == expected
    scaled = research.predict(recipe, [p * 2 for p in closes], 320)
    for row, converted in zip(expected, scaled):
        assert row[2] == closes[320]
        assert row == sorted(row)
        assert converted == pytest.approx([2 * p for p in row])


@pytest.mark.parametrize("recipe", research.RECIPES)
def test_constant_series_has_finite_positive_ordered_bands(recipe):
    prediction = research.predict(recipe, [100.0] * 350, 349)
    assert len(prediction) == 52
    assert all(0 < row[0] < row[2] < row[4] for row in prediction)


def test_regime_neighbors_include_only_mature_labels():
    closes = [100 * math.exp(0.05 * math.sin(i / 7)) for i in range(350)]
    indices = research.neighbors(closes, 320, 52)
    assert len(indices) == 64
    assert min(indices) >= 104
    assert max(indices) + 52 <= 320


def test_guardrails_use_exact_coverage_and_reject_one_bad_horizon():
    actuals = [[100.0] * 52 for _ in range(10)]
    predictions = [[[80, 90, 100, 110, 120] for _ in range(52)] for _ in range(10)]
    result = research.score(predictions, actuals, [100.0] * 10)
    assert result["failed_horizons"] == list(range(1, 53))
    assert result["failures"]["mae"] == []


def test_frozen_snapshot_tampering_is_rejected(tmp_path):
    snapshot = tmp_path / "input.csv"
    snapshot.write_text("date,close\n2020-01-06,100\n")
    directory = tmp_path / "run"
    research.prepare(snapshot, directory)
    (directory / "snapshot.csv").write_text("date,close\n2020-01-06,101\n")
    with pytest.raises(ValueError, match="snapshot"):
        research.verify(directory)
