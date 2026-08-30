from datetime import date
import importlib

import pandas as pd
import psycopg
import pytest


db_writer = importlib.import_module("raw_ingest.DbWriter")


def test_latest_date_is_none_before_first_batch(postgres_connection):
    assert db_writer.get_latest_date(postgres_connection, "btc_usd_ohlcv") is None


def test_ohlcv_batch_is_idempotent_and_records_run_metadata(
    postgres_connection, mock_logger
):
    first_batch = pd.DataFrame(
        {
            "time": pd.to_datetime(["2026-08-28", "2026-08-29"]),
            "low": [110_000.0, 111_000.0],
            "high": [112_000.0, 113_000.0],
            "open": [111_000.0, 112_000.0],
            "close": [111_500.0, 112_500.0],
            "volume": [1_000.0, 1_100.0],
        }
    )
    correction = first_batch.iloc[[1]].copy()
    correction.loc[:, "close"] = 112_750.0

    inserted = db_writer.DbWriter(
        postgres_connection,
        mock_logger,
        "btc_usd_ohlcv",
        first_batch,
        "run-1",
    ).save_batch()
    updated = db_writer.DbWriter(
        postgres_connection,
        mock_logger,
        "btc_usd_ohlcv",
        correction,
        "run-2",
    ).save_batch()

    with postgres_connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT date, close, run_id, ingest_date_time IS NOT NULL
            FROM bronze.btc_usd_ohlcv
            ORDER BY date
            """
        )
        rows = cursor.fetchall()

    assert inserted == 2
    assert updated == 1
    assert rows == [
        (date(2026, 8, 28), 111_500.0, "run-1", True),
        (date(2026, 8, 29), 112_750.0, "run-2", True),
    ]
    assert db_writer.get_latest_date(postgres_connection, "btc_usd_ohlcv") == date(
        2026, 8, 29
    )


@pytest.mark.parametrize(
    ("table_name", "frame", "value_column", "expected_value"),
    [
        (
            "eth_usd_ohlcv",
            pd.DataFrame(
                {
                    "time": pd.to_datetime(["2026-08-29"]),
                    "low": [4_500.0],
                    "high": [4_700.0],
                    "open": [4_550.0],
                    "close": [4_650.0],
                    "volume": [12_000.0],
                }
            ),
            "close",
            4_650.0,
        ),
        (
            "usd_chf_rates",
            pd.DataFrame(
                {"time": pd.to_datetime(["2026-08-29"]), "rate": [0.80]}
            ),
            "rate",
            0.80,
        ),
        (
            "usd_eur_rates",
            pd.DataFrame(
                {"time": pd.to_datetime(["2026-08-29"]), "rate": [0.86]}
            ),
            "rate",
            0.86,
        ),
        (
            "bgeometrics_btc_technical_indicators",
            pd.DataFrame(
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
            ),
            "rsi",
            52.1,
        ),
    ],
)
def test_writer_supports_each_allow_listed_bronze_table(
    postgres_connection,
    mock_logger,
    table_name,
    frame,
    value_column,
    expected_value,
):
    db_writer.DbWriter(
        postgres_connection, mock_logger, table_name, frame, "run-all-tables"
    ).save_batch()

    with postgres_connection.cursor() as cursor:
        cursor.execute(
            f'SELECT "{value_column}" FROM bronze."{table_name}" WHERE date = %s',
            (date(2026, 8, 29),),
        )
        value = cursor.fetchone()[0]

    assert value == expected_value


def test_batch_failure_rolls_back_every_row_and_logs(postgres_connection, mock_logger):
    invalid_batch = pd.DataFrame(
        {
            "time": pd.to_datetime(["2026-08-28", "2026-08-29"]),
            "low": [110_000.0, 111_000.0],
            "high": [112_000.0, 113_000.0],
            "open": [111_000.0, 112_000.0],
            "close": [111_500.0, "not-a-number"],
            "volume": [1_000.0, 1_100.0],
        }
    )

    with pytest.raises(psycopg.DataError):
        db_writer.DbWriter(
            postgres_connection,
            mock_logger,
            "btc_usd_ohlcv",
            invalid_batch,
            "failed-run",
        ).save_batch()

    with postgres_connection.cursor() as cursor:
        cursor.execute("SELECT to_regclass('bronze.btc_usd_ohlcv')")
        table_name = cursor.fetchone()[0]

    assert table_name is None
    mock_logger.exception.assert_called_once()
