import math

import numpy as np

from forecast.linear_research import LinearCandidate, features


def series():
    return [math.exp(4 + i * 0.003 + 0.08 * math.sin(i / 6)) for i in range(120)]


def test_features_ignore_future_and_price_scale():
    closes = series()
    assert features(closes, 60) == features(closes[:61] + [1e20] * 59, 60)
    np.testing.assert_allclose(
        features(closes, 60), features([x * 100 for x in closes], 60)
    )


def test_linear_training_excludes_unobserved_labels_and_scaler_rows():
    closes = series()
    first, second = LinearCandidate(), LinearCandidate()
    first.fit(closes, 108)
    second.fit(closes[:108] + [1e20] * 12, 108)
    np.testing.assert_allclose(first.predict(closes, 107), second.predict(closes, 107))
    expected = np.asarray([features(closes, j) for j in range(52, 108 - 52)])
    np.testing.assert_allclose(first.scalers[-1].mean_, expected.mean(axis=0))
    prediction = first.predict(closes, 107)
    assert len(prediction) == 52
    assert all(
        len(row) == 5 and row == sorted(row) and min(row) > 0 for row in prediction
    )
