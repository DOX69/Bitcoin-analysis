import math

import numpy as np
import pandas as pd
import pytest

from forecast.nhits_research import causal_frame, prices


def test_context_excludes_future_and_uses_observed_log_prices():
    closes = [100 + j for j in range(200)]
    frame = causal_frame(closes, 120)
    changed = causal_frame(closes[:120] + [1e20] * 80, 120)
    pd.testing.assert_frame_equal(frame, changed)
    assert len(frame) == 120
    assert frame.iloc[-1]["ds"] == 119
    assert frame.iloc[-1]["y"] == math.log(closes[119])


def test_quantile_columns_use_declared_order_and_reject_missing_horizons():
    columns = ["q10", "q25", "q50", "q75", "q90"]
    frame = pd.DataFrame(
        {name: [value] * 52 for name, value in zip(columns, [4, 2, 3, 5, 6])}
    )
    result = prices(frame[list(reversed(columns))], columns)
    np.testing.assert_allclose(result[0], np.exp([2, 3, 4, 5, 6]))
    with pytest.raises(ValueError):
        prices(frame.iloc[:-1], columns)
