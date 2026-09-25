from datetime import date, timedelta

import numpy as np

from forecast import daily_research as daily
from forecast import multiscale_research as multi


def rows(count=2100):
    start = date(2017, 1, 2)
    steps = np.arange(count, dtype=float)
    logs = np.log(100.0) + 0.0004 * steps + 0.04 * np.sin(steps / 19)
    return [
        {
            "date": str(start + timedelta(days=index)),
            "close": float(np.exp(logs[index])),
        }
        for index in range(count)
    ]


def prepared():
    days, values = daily.observations(rows())
    origins = [
        index
        for index, day in enumerate(days)
        if day.weekday() == 6 and index >= 1095 and index <= 1644
    ]
    raw = multi.weekly_raw_forecasts(days, values, origins)
    return days, values, origins, raw


def test_future_prices_cannot_change_past_training_or_predictions():
    days, values, _, raw = prepared()
    origin = 1644
    before = multi.forecast_at_origin(days, values, origin, raw)

    changed = values.copy()
    changed[origin + 1 :] *= 3
    changed_raw = multi.weekly_raw_forecasts(days, changed, raw.keys())
    after = multi.forecast_at_origin(days, changed, origin, changed_raw)

    np.testing.assert_array_equal(before["quantiles"], after["quantiles"])
    np.testing.assert_array_equal(before["anchor_quantiles"], after["anchor_quantiles"])


def test_future_sunday_observation_cannot_change_past_anchors():
    days, values, origins, raw = prepared()
    changed = values.copy()
    changed[1651] *= 10
    changed_raw = multi.weekly_raw_forecasts(days, changed, origins)

    for origin in origins:
        np.testing.assert_array_equal(raw[origin], changed_raw[origin])


def test_daily_forecast_reconciles_exactly_to_weekly_anchors():
    days, values, _, raw = prepared()
    result = multi.forecast_at_origin(days, values, 1644, raw)

    for week in range(1, 53):
        np.testing.assert_array_equal(
            result["quantiles"][week * 7 - 1], result["anchor_quantiles"][week - 1]
        )


def test_output_has_365_ordered_quantile_rows_and_dates():
    days, values, _, raw = prepared()
    result = multi.forecast_at_origin(days, values, 1644, raw)
    points = multi.output_points(days[1644], result["quantiles"])

    assert len(points) == 365
    assert points[0]["horizon_days"] == 1
    assert points[-1]["horizon_days"] == 365
    assert points[-1]["target_date"] == str(days[1644] + timedelta(days=365))
    quantiles = np.asarray([point["USD"] for point in points])
    assert np.isfinite(quantiles).all()
    assert np.all(np.diff(quantiles, axis=1) >= 0)


def test_calibration_labels_are_mature_at_the_training_origin():
    days, values, _, raw = prepared()
    origin = 1644
    for horizon in range(1, 53):
        assert all(
            index + horizon * 7 <= origin
            for index in multi.mature_anchor_origins(raw, origin, horizon)
        )
    assert all(index <= origin for index in multi.residual_sample_indices(days, origin))


def test_partition_rule_is_shared_by_all_candidates():
    days, _, origins, _ = prepared()
    partitions = multi.partition_origins(days, origins)
    assert set(partitions) == {"earlier", "later_already_examined"}
    assert all(
        days[index + 365] <= date(2023, 9, 13) for index in partitions["earlier"]
    )
    assert all(
        days[index] > date(2023, 9, 13)
        for index in partitions["later_already_examined"]
    )


def test_benchmark_origins_require_j365_maturity_for_shared_baseline():
    days, _, _, raw = prepared()
    eligible = multi.benchmark_origins(days, raw)
    assert 1637 not in eligible
    assert all(
        sum(candidate < origin and candidate + 365 <= origin for candidate in raw) >= 26
        for origin in eligible
    )
