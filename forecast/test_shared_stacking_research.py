import math

from forecast import shared_stacking_research as research
from forecast.student_research import simulate


def test_shared_weight_prediction_is_causal_and_has_one_choice_per_horizon():
    distribution, _ = simulate(paths=1000)
    closes = [100 * math.exp(0.001 * i + 0.1 * math.sin(i / 9)) for i in range(450)]
    expected = research.predict(closes, 350, distribution)
    assert research.predict(closes[:351] + [1e12] * 99, 350, distribution) == expected
    points, weights, calibration = expected
    assert len(points) == len(weights) == len(calibration) == 52
    for h, (point, weight, source) in enumerate(zip(points, weights, calibration), 1):
        assert point == sorted(point)
        assert point[2] == closes[350]
        assert weight in research.WEIGHTS
        assert source["last_origin"] + h == 350
        assert source["origins"] == 156
