from datetime import date, timedelta

import pytest

from forecast.benchmark import (
    MAX_HORIZON,
    ResidualQuantileCalibrator,
    aggregate_daily_rows,
    estimate_railway_cost_usd,
    _process_rss_bytes,
    split_series,
)


def make_daily_rows(start: date, weeks: int) -> list[dict[str, object]]:
    rows = []
    for day_offset in range(weeks * 7):
        observed = start + timedelta(days=day_offset)
        rows.append({"date": observed.isoformat(), "close": 100 + day_offset})
    return rows


def test_aggregate_daily_rows_uses_complete_iso_week_sunday_closes() -> None:
    rows = make_daily_rows(date(2024, 1, 1), weeks=2)

    weekly = aggregate_daily_rows(rows)

    assert weekly == [
        {"date": "2024-01-01", "close": 106.0},
        {"date": "2024-01-08", "close": 113.0},
    ]


def test_aggregate_daily_rows_rejects_incomplete_weeks() -> None:
    rows = make_daily_rows(date(2024, 1, 1), weeks=2)[:-1]

    with pytest.raises(ValueError, match="complete ISO weeks"):
        aggregate_daily_rows(rows)


def test_aggregate_daily_rows_rejects_a_missing_complete_week() -> None:
    rows = make_daily_rows(date(2024, 1, 1), weeks=3)
    rows = rows[:7] + rows[14:]

    with pytest.raises(ValueError, match="missing ISO week"):
        aggregate_daily_rows(rows)


def test_split_series_keeps_calibration_and_test_targets_disjoint() -> None:
    weekly = [
        {"date": f"2024-{index:03d}", "close": float(index)} for index in range(360)
    ]

    split = split_series(weekly)

    assert split.train_end == split.calibration_start
    assert split.calibration_end <= split.test_start
    assert split.test_end + MAX_HORIZON == len(weekly)
    assert split.train_end + MAX_HORIZON <= split.calibration_end
    assert split.calibration_end + MAX_HORIZON <= split.test_end + MAX_HORIZON


def test_calibrator_orders_quantiles_after_residual_correction() -> None:
    calibrator = ResidualQuantileCalibrator.fit(
        predictions=[[[10.0, 11.0, 12.0], [20.0, 19.0, 21.0]]],
        actuals=[[13.0, 18.0]],
        quantiles=(0.1, 0.5, 0.9),
    )

    calibrated = calibrator.apply([[[10.0, 11.0, 12.0], [20.0, 19.0, 21.0]]])

    assert calibrated[0][0] == sorted(calibrated[0][0])
    assert calibrated[0][1] == sorted(calibrated[0][1])


def test_estimate_railway_cost_is_zero_for_zero_runtime() -> None:
    assert estimate_railway_cost_usd(0) == 0.0
    assert estimate_railway_cost_usd(30 * 60) == pytest.approx(0.0555)


def test_process_rss_measurement_is_positive() -> None:
    assert _process_rss_bytes() > 0
