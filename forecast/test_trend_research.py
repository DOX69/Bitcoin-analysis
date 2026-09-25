import numpy as np
import pytest

from forecast.trend_research import calibrated, fit


def test_constant_history_does_not_manufacture_a_trend():
    prediction, _ = fit([100.0] * 104)
    np.testing.assert_allclose(np.exp(prediction), 100, rtol=1e-8)


def test_learned_trend_produces_reproducible_future_periods():
    closes = np.exp(np.linspace(4, 5, 120)).tolist()
    prediction, parameters = fit(closes)
    assert len(prediction) == 52
    assert prediction[-1] > prediction[0] > np.log(closes[-1])
    assert 0.8 <= parameters["phi"] <= 0.98
    np.testing.assert_array_equal(prediction, fit(closes)[0])
    assert prediction[-1] - prediction[-2] < prediction[1] - prediction[0]


def test_calibration_never_reads_unmatured_targets():
    closes = np.exp(np.linspace(4, 6, 350))
    forecasts = {j: np.full(52, np.log(closes[j])) for j in range(103, 350)}
    expected = calibrated(closes, 250, forecasts)
    closes[251:] = 1e9
    assert calibrated(closes, 250, forecasts) == expected
    assert np.all(np.diff(expected, axis=1) >= 0)


def test_calibration_refuses_insufficient_mature_errors():
    with pytest.raises(ValueError, match="52 mature"):
        calibrated(
            [100.0] * 150, 149, {j: np.full(52, np.log(100)) for j in range(103, 150)}
        )


@pytest.mark.parametrize("closes", [[100.0] * 103, [float("nan")] * 104, [-1.0] * 104])
def test_invalid_training_data_rejected(closes):
    with pytest.raises(ValueError, match="positive"):
        fit(closes)
