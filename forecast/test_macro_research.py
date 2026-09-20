from datetime import date, timedelta

import numpy as np
import pytest

from forecast import macro_research as macro


def test_alfred_parser_requires_the_requested_vintage_columns():
    content = (
        "observation_date,DFF_20240107,DFF_20240204\n"
        "2024-01-01,5.33,5.33\n"
        "2024-01-02,5.33,.\n"
    )

    parsed = macro.parse_alfred_csv(
        content, "DFF", [date(2024, 1, 7), date(2024, 2, 4)]
    )

    assert parsed["vintage_dates"] == ["2024-01-07", "2024-02-04"]
    assert parsed["observations"][1]["values"] == [5.33, None]
    with pytest.raises(ValueError, match="vintage header"):
        macro.parse_alfred_csv(
            content.replace("DFF_20240204", "DFF_20260920"),
            "DFF",
            [date(2024, 1, 7), date(2024, 2, 4)],
        )


def test_features_use_only_the_latest_vintage_available_on_each_day():
    days = [date(2024, 1, 1) + timedelta(days=i) for i in range(40)]
    snapshot = {
        "vintage_dates": ["2024-01-07", "2024-01-21"],
        "series": [
            {
                "series_id": "DFF",
                "vintage_dates": ["2024-01-07", "2024-01-21"],
                "observations": [
                    {"date": "2024-01-01", "values": [5.0, 6.0]},
                    {"date": "2024-01-15", "values": [None, 7.0]},
                ],
            }
        ],
    }

    features = macro.feature_matrix(days, snapshot)

    assert np.isnan(features[0]).all()
    assert features[7, 0] == pytest.approx(5.0)
    assert features[20, 0] == pytest.approx(7.0)
    assert np.isfinite(features[20:]).all()


def test_future_observations_and_future_vintages_cannot_change_past_features():
    days = [date(2024, 1, 1) + timedelta(days=i) for i in range(80)]
    base_series = {
        "series_id": "CPIAUCSL",
        "vintage_dates": [
            "2024-01-07",
            "2024-02-04",
            "2024-03-03",
            "2024-03-10",
        ],
        "observations": [
            {
                "date": "2024-01-01",
                "values": [300.0, 301.0, 302.0, 303.0],
            },
            {"date": "2024-02-01", "values": [None, 305.0, 306.0, 307.0]},
        ],
    }
    snapshot = {"vintage_dates": base_series["vintage_dates"], "series": [base_series]}
    before = macro.feature_matrix(days, snapshot)

    changed = {
        "vintage_dates": base_series["vintage_dates"],
        "series": [
            {
                **base_series,
                "observations": [
                    *base_series["observations"],
                    {
                        "date": "2024-03-01",
                        "values": [None, None, None, 999.0],
                    },
                ],
            }
        ],
    }
    after = macro.feature_matrix(days, changed)

    np.testing.assert_array_equal(before[:69], after[:69])


def test_enriched_shortlist_requires_beating_price_only_and_naive():
    def score(value):
        return {
            "aggregate": {"mae": value, "wis": value},
            "per_horizon": [{"mae": value} for _ in range(365)],
        }

    groups = {
        name: {
            "models": {
                "naive": score(100),
                "price_only": score(90),
                "price_macro": score(80),
            }
        }
        for name in ("earlier", "later")
    }
    assert macro.enriched_shortlist(groups) == ["price_macro"]
    groups["later"]["models"]["price_macro"] = score(95)
    assert macro.enriched_shortlist(groups) == []
