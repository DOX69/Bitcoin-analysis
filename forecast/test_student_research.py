import math

import numpy as np

from forecast import student_research as research


def test_student_paths_are_reproducible_symmetric_and_have_declared_variance():
    quantiles, diagnostics = research.simulate(paths=10000)
    repeated, _ = research.simulate(paths=10000)
    np.testing.assert_array_equal(quantiles, repeated)
    np.testing.assert_allclose(quantiles[:, 0], -quantiles[:, 4], atol=1e-12)
    np.testing.assert_allclose(quantiles[:, 1], -quantiles[:, 3], atol=1e-12)
    assert np.all(quantiles[:, 2] == 0)
    assert abs(diagnostics["variance_h1"] / (1 + 1 / 104) - 1) < 0.12
    assert abs(diagnostics["variance_h52"] / (52 + 52**2 / 104) - 1) < 0.12


def test_student_prediction_is_causal_and_preserves_price_median():
    quantiles, _ = research.simulate(paths=1000)
    closes = [100 * math.exp(0.001 * i + 0.1 * math.sin(i / 9)) for i in range(450)]
    original = research.predict(closes, 350, quantiles)
    assert research.predict(closes[:351] + [1e12] * 99, 350, quantiles) == original
    assert len(original) == 52
    for row in original:
        assert row[2] == closes[350]
        assert row == sorted(row)
        assert all(math.isfinite(value) and value > 0 for value in row)
