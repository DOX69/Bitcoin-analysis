import math

import numpy as np

from forecast import stacking_research as research
from forecast.student_research import simulate


def test_stacking_ignores_future_and_uses_only_mature_labels():
    distribution, _ = simulate(paths=1000)
    closes = [100 * math.exp(0.001 * i + 0.1 * math.sin(i / 9)) for i in range(450)]
    expected = research.predict(closes, 350, distribution)
    assert research.predict(closes[:351] + [1e12] * 99, 350, distribution) == expected
    points, weights, calibration = expected
    assert len(points) == len(weights) == len(calibration) == 52
    for h, (point, weight, source) in enumerate(zip(points, weights, calibration), 1):
        assert point == sorted(point)
        assert point[2] == closes[350]
        assert all(value in research.WEIGHTS for value in weight)
        assert source["last_origin"] + h == 350
        assert source["first_origin"] >= 104
        assert source["origins"] == 156


def test_weight_ties_prefer_half_then_lower_weight():
    assert research.choose_weight(np.ones(5)) == 0.5
    assert research.choose_weight(np.array([5.0, 1.0, 5.0, 1.0, 5.0])) == 0.25
