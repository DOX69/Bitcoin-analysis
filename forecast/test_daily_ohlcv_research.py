import copy
from datetime import date, timedelta

import numpy as np
import pytest

from forecast import daily_ohlcv_research as ohlcv
from forecast import daily_pooled_research as pooled


def sample():
    rows = []
    for j in range(1800):
        close = 100 + j + np.sin(j / 20)
        rows.append(
            {
                "date": str(date(2015, 1, 1) + timedelta(days=j)),
                "open": close,
                "close": close,
                "low": close * 0.98,
                "high": close * 1.03,
                "volume": j % 70,
                "observed_at": "2026-09-16T00:00:00+00:00",
            }
        )
    return {"rows": rows, "exported_at": "2026-09-17T00:00:00+00:00"}


def test_audit_accepts_zero_volume_but_rejects_bad_bounds_and_changed_closes():
    snapshot = sample()
    reference = copy.deepcopy(snapshot["rows"])
    assert ohlcv.audit(snapshot, reference)["zero_volume_days"] > 0
    snapshot["rows"][30]["low"] = 10000
    with pytest.raises(ValueError, match="bounds"):
        ohlcv.audit(snapshot, reference)
    snapshot = sample()
    snapshot["rows"][30]["close"] += 1
    with pytest.raises(ValueError, match="dates/closes"):
        ohlcv.audit(snapshot, reference)


def test_audit_rejects_missing_day_and_future_ingestion():
    snapshot = sample()
    reference = copy.deepcopy(snapshot["rows"])
    snapshot["rows"][30]["observed_at"] = "2027-01-01T00:00:00+00:00"
    with pytest.raises(ValueError, match="timestamps"):
        ohlcv.audit(snapshot, reference)
    snapshot = sample()
    snapshot["rows"].pop(30)
    with pytest.raises(ValueError):
        ohlcv.audit(snapshot, reference)


def test_features_and_predictions_ignore_future_volume_and_ranges():
    rows = sample()["rows"]
    before = ohlcv.feature_sets(rows)
    logs = np.log([r["close"] for r in rows])
    prediction = pooled.predict(logs, before["price_volume_range"], 1400)
    for row in rows[1401:]:
        row["volume"] *= 1000
        row["high"] *= 100
        row["low"] /= 100
    after = ohlcv.feature_sets(rows)
    for name in before:
        np.testing.assert_array_equal(before[name][:1401], after[name][:1401])
    np.testing.assert_array_equal(
        prediction, pooled.predict(logs, after["price_volume_range"], 1400)
    )
    assert np.isfinite(before["price_volume_range"][365:]).all()


def test_enrichment_must_beat_both_price_only_and_naive():
    def score(value):
        return {
            "aggregate": {"mae": value, "wis": value},
            "per_horizon": [{"mae": value} for _ in range(365)],
        }

    groups = {
        g: {
            "models": {
                "naive": score(100),
                "price_only": score(150),
                "price_volume": score(120),
                "price_range": score(90),
                "price_volume_range": score(100),
            }
        }
        for g in ("earlier", "later")
    }
    assert ohlcv.enriched_shortlist(groups) == ["price_range"]
    groups["later"]["models"]["price_only"] = score(80)
    assert ohlcv.enriched_shortlist(groups) == []
