import numpy as np

from forecast import daily_pooled_research as pooled
from forecast import daily_research as daily


def test_future_prices_cannot_change_training_or_predictions():
    logs = np.log(100 + np.arange(1800)) + np.sin(np.arange(1800) / 30) * 0.1
    features = daily.features(logs)
    x, y = pooled.training_data(logs, features, 1400)
    prediction = pooled.predict(logs, features, 1400)
    logs[1401:] += 10
    future_features = daily.features(logs)
    other_x, other_y = pooled.training_data(logs, future_features, 1400)
    np.testing.assert_array_equal(x, other_x)
    np.testing.assert_array_equal(y, other_y)
    np.testing.assert_array_equal(
        prediction, pooled.predict(logs, future_features, 1400)
    )
    assert prediction.shape == (365,)
    assert np.isfinite(prediction).all()


def test_training_has_daily_origins_and_excludes_immature_labels():
    logs = np.arange(1800, dtype=float)
    features = np.repeat(np.arange(1800)[:, None], 6, axis=1)
    x, y = pooled.training_data(logs, features, 1400)
    starts = x[:, 0].astype(int)
    horizons = np.rint(np.expm1(x[:, -1])).astype(int)
    assert np.all(starts + horizons <= 1400)
    assert np.all(np.diff(np.unique(starts)) == 1)
    np.testing.assert_allclose(y, np.sqrt(horizons))
