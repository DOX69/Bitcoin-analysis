import math

from forecast import normalized_research as research


def test_normalized_bands_are_causal_ordered_and_keep_persistence_median():
    closes = [100 * math.exp(i * 0.001 + 0.1 * math.sin(i / 9)) for i in range(450)]
    expected = research.predict(closes, 350)
    assert research.predict(closes[:351] + [1e12] * 99, 350) == expected
    assert len(expected) == 52
    for row in expected:
        assert row[2] == closes[350]
        assert len(row) == 5 and row == sorted(row)
        assert all(math.isfinite(value) and value > 0 for value in row)


def test_constant_series_has_positive_finite_floor_bands():
    rows = research.predict([100.0] * 350, 349)
    assert all(row[0] > 0 and row[0] < row[2] < row[4] for row in rows)
