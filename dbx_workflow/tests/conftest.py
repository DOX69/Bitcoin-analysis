import os
from unittest.mock import MagicMock

import pandas as pd
import psycopg
import pytest


@pytest.fixture()
def mock_logger():
    return MagicMock()


@pytest.fixture()
def database_url():
    return os.getenv(
        "TEST_DATABASE_URL",
        "postgresql://postgres:postgres@localhost:55432/bitcoin_test",
    )


@pytest.fixture()
def postgres_connection(database_url):
    with psycopg.connect(database_url, autocommit=True) as connection:
        with connection.cursor() as cursor:
            cursor.execute("DROP SCHEMA IF EXISTS bronze CASCADE")
            cursor.execute("CREATE SCHEMA bronze")
        yield connection
        with connection.cursor() as cursor:
            cursor.execute("DROP SCHEMA IF EXISTS bronze CASCADE")


@pytest.fixture()
def mock_coinbase_api_response():
    return [
        [1640995200, 46000.0, 47500.0, 46500.0, 47000.0, 1500.5],
        [1641081600, 47000.0, 48000.0, 47000.0, 47800.0, 1800.3],
        [1641168000, 47800.0, 49000.0, 47800.0, 48500.0, 2100.7],
        [1641254400, 48500.0, 49500.0, 48500.0, 49000.0, 1950.2],
        [1641340800, 49000.0, 50000.0, 49000.0, 49800.0, 2200.1],
    ]


@pytest.fixture()
def mock_bgeometrics_api_response():
    return [
        {
            "d": "2026-02-24",
            "unixTs": "1771891200",
            "rsi": 35.015935,
            "macd": -3866.934213,
            "macdsignal": -4253.672544,
            "macdhist": 386.738331,
            "sma7": 66524.960526,
            "sma50": 80196.904354,
            "sma200": 98418.315352,
            "ema7": 66290.616363,
            "ema50": 76811.130651,
            "ema200": 91778.421821,
        },
        {
            "d": "2026-02-25",
            "unixTs": "1771977600",
            "rsi": 39.408559,
            "macd": -3837.731918,
            "macdsignal": -4170.484419,
            "macdhist": 332.7525,
            "sma7": 66202.373817,
            "sma50": 79607.870612,
            "sma200": 98156.370073,
            "ema7": 65748.612272,
            "ema50": 76313.541214,
            "ema200": 91503.239514,
        },
        {
            "d": "2026-02-26",
            "unixTs": "1772064000",
            "rsi": 45.102345,
            "macd": -3500.123456,
            "macdsignal": -3800.484419,
            "macdhist": 300.360963,
            "sma7": 66100.0,
            "sma50": 79000.0,
            "sma200": 98000.0,
            "ema7": 65500.0,
            "ema50": 76000.0,
            "ema200": 91000.0,
        },
    ]


@pytest.fixture()
def sample_pandas_df():
    return pd.DataFrame(
        {
            "time": pd.to_datetime(
                ["2022-01-01", "2022-01-02", "2022-01-03", "2022-01-04", "2022-01-05"]
            ),
            "low": [46000.0, 47000.0, 47800.0, 48500.0, 49000.0],
            "high": [47500.0, 48000.0, 49000.0, 49500.0, 50000.0],
            "open": [46500.0, 47000.0, 47800.0, 48500.0, 49000.0],
            "close": [47000.0, 47800.0, 48500.0, 49000.0, 49800.0],
            "volume": [1500.5, 1800.3, 2100.7, 1950.2, 2200.1],
        }
    )
