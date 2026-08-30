from datetime import date

import pandas as pd
import pytest

from raw_ingest.ingest_market_price_data import get_fetcher, ingest_ticker_data
from raw_ingest.ingest_technical_indicators import get_fetcher as get_indicator_fetcher


class MarketFetcherStub:
    table_name = "btc_usd_ohlcv"

    def __init__(self):
        self.start_dates = []

    def fetch_historical_data(self, start_date_time=None):
        self.start_dates.append(start_date_time)
        return pd.DataFrame(
            {
                "time": pd.to_datetime(["2026-08-28", "2026-08-29"]),
                "low": [110_000.0, 111_000.0],
                "high": [112_000.0, 113_000.0],
                "open": [111_000.0, 112_000.0],
                "close": [111_500.0, 112_500.0],
                "volume": [1_000.0, 1_100.0],
            }
        )


def test_runtime_fetchers_target_bronze_without_a_catalog(mock_logger):
    assert (
        get_fetcher("BTC", "USD", mock_logger).full_path_table_name
        == "bronze.btc_usd_ohlcv"
    )
    assert (
        get_fetcher("USD", "CHF", mock_logger).full_path_table_name
        == "bronze.usd_chf_rates"
    )
    assert (
        get_indicator_fetcher(mock_logger).full_path_table_name
        == "bronze.bgeometrics_btc_technical_indicators"
    )


def test_market_ingestion_resumes_from_max_date_and_upserts(
    postgres_connection, mock_logger
):
    fetcher = MarketFetcherStub()

    ingest_ticker_data(
        postgres_connection,
        "BTC",
        "USD",
        "market-run-1",
        fetcher=fetcher,
        logger=mock_logger,
    )
    ingest_ticker_data(
        postgres_connection,
        "BTC",
        "USD",
        "market-run-2",
        fetcher=fetcher,
        logger=mock_logger,
    )

    with postgres_connection.cursor() as cursor:
        cursor.execute("SELECT count(*), max(date) FROM bronze.btc_usd_ohlcv")
        count, latest_date = cursor.fetchone()

    assert fetcher.start_dates == [None, pd.Timestamp(date(2026, 8, 29))]
    assert count == 2
    assert latest_date == date(2026, 8, 29)


def test_market_ingestion_does_not_write_after_fetch_failure(
    postgres_connection, mock_logger
):
    class FailedFetcher:
        table_name = "btc_usd_ohlcv"

        def fetch_historical_data(self, start_date_time=None):
            raise ValueError("invalid second page")

    with pytest.raises(ValueError):
        ingest_ticker_data(
            postgres_connection,
            "BTC",
            "USD",
            "failed-market-run",
            fetcher=FailedFetcher(),
            logger=mock_logger,
        )

    with postgres_connection.cursor() as cursor:
        cursor.execute("SELECT to_regclass('bronze.btc_usd_ohlcv')")
        table_name = cursor.fetchone()[0]

    assert table_name is None
