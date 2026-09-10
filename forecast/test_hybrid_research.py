import math
from datetime import date, datetime, timedelta, timezone

import numpy as np
import pytest

from forecast import hybrid_research as research
from forecast.student_research import simulate


def test_hybrid_is_causal_ordered_through_52_weeks_and_preserves_selected_levels():
    student, _ = simulate(paths=1000)
    table = research.combine(student)
    np.testing.assert_array_equal(table[:, 1:4], student[:, 1:4])
    closes = [100 * math.exp(0.001 * i + 0.1 * math.sin(i / 9)) for i in range(450)]
    expected = research.predict(closes, 350, table)
    assert research.predict(closes[:351] + [1e12] * 99, 350, table) == expected
    assert len(expected) == 52
    for row in expected:
        assert row == sorted(row)
        assert row[2] == closes[350]
        assert all(math.isfinite(value) and value > 0 for value in row)


def test_hybrid_rejects_crossing_instead_of_sorting():
    student, _ = simulate(paths=1000)
    student[51, 3] = 100
    with pytest.raises(ValueError, match="cross"):
        research.combine(student)


def test_shadow_dates_are_future_and_timestamp_is_explicit():
    student, _ = simulate(paths=1000)
    table = research.combine(student)
    last = date(2026, 8, 31)
    weekly = [
        {"date": (last - timedelta(weeks=109 - i)).isoformat(), "close": 100 + i}
        for i in range(110)
    ]
    now = datetime(2026, 9, 10, tzinfo=timezone.utc)
    shadow = research.shadow(weekly, table, now)
    assert shadow["created_at"] == now.isoformat()
    assert shadow["points"][0]["target_date"] == "2026-09-13"
    assert shadow["points"][-1]["target_date"] == "2027-09-05"
    assert shadow["status"] == "research_shadow_local"
    with pytest.raises(ValueError, match="future"):
        research.shadow(weekly, table, datetime(2026, 9, 14, tzinfo=timezone.utc))
