from datetime import date

import pandas as pd
import pytest

from raw_ingest.ingest_technical_indicators import ingest_technical_indicators


class IndicatorFetcherStub:
    table_name = "bgeometrics_btc_technical_indicators"

    def __init__(self):
        self.start_dates = []

    def fetch_historical_data(self, start_date_time=None):
        self.start_dates.append(start_date_time)
        return pd.DataFrame(
            {
                "d": ["2026-08-29"],
                "unixTs": [1787961600],
                "rsi": [52.1],
                "macd": [100.0],
                "macdsignal": [90.0],
                "macdhist": [10.0],
                "sma7": [111_000.0],
                "sma50": [105_000.0],
                "sma200": [98_000.0],
                "ema7": [111_100.0],
                "ema50": [105_100.0],
                "ema200": [98_100.0],
                "time": pd.to_datetime(["2026-08-29"]),
            }
        )


def test_indicator_ingestion_resumes_from_max_date_and_upserts(
    postgres_connection, mock_logger
):
    fetcher = IndicatorFetcherStub()

    ingest_technical_indicators(
        postgres_connection,
        "indicator-run-1",
        fetcher=fetcher,
        logger=mock_logger,
    )
    ingest_technical_indicators(
        postgres_connection,
        "indicator-run-2",
        fetcher=fetcher,
        logger=mock_logger,
    )

    with postgres_connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT count(*), max(date)
            FROM bronze.bgeometrics_btc_technical_indicators
            """
        )
        count, latest_date = cursor.fetchone()

    assert fetcher.start_dates == [None, pd.Timestamp(date(2026, 8, 29))]
    assert count == 1
    assert latest_date == date(2026, 8, 29)


def test_indicator_ingestion_does_not_write_after_fetch_failure(
    postgres_connection, mock_logger
):
    class FailedFetcher:
        table_name = "bgeometrics_btc_technical_indicators"

        def fetch_historical_data(self, start_date_time=None):
            raise ValueError("invalid response item")

    with pytest.raises(ValueError):
        ingest_technical_indicators(
            postgres_connection,
            "failed-indicator-run",
            fetcher=FailedFetcher(),
            logger=mock_logger,
        )

    with postgres_connection.cursor() as cursor:
        cursor.execute(
            "SELECT to_regclass('bronze.bgeometrics_btc_technical_indicators')"
        )
        table_name = cursor.fetchone()[0]

    assert table_name is None
