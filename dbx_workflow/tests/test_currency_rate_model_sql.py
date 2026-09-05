"""Run dbt against the disposable PostgreSQL test database, never a live profile."""
import os
from pathlib import Path
import subprocess
import sys

import pytest
from jinja2 import Environment
from psycopg.conninfo import conninfo_to_dict

ROOT = Path(__file__).parents[2]
PROJECT = ROOT / "dbt_silver_gold"
RELATIONS = {
    "rates": "dlh_silver__currency_rate.usd_to_other",
    "indicators": "dlh_silver__bgeometrics_technical_indicators.fact_btc",
    "daily": "dlh_silver__crypto_prices.obt_fact_day_btc",
    **{period: f"dlh_gold__crypto_prices.agg_{period}_btc" for period in ("week", "month", "quarter", "year")},
}


@pytest.fixture()
def dbt_build(postgres_connection, database_url, tmp_path):
    connection = conninfo_to_dict(database_url)
    postgres_connection.execute((PROJECT / "tests/fixtures/setup.sql").read_text())
    env = dict(os.environ, PGHOST=connection["host"], PGPORT=connection.get("port", "5432"),
               PGUSER=connection["user"], PGPASSWORD=connection.get("password", ""),
               PGDATABASE=connection["dbname"], DBT_TARGET_SCHEMA="ci")
    executable = str(Path(sys.executable).with_name("dbt.exe" if os.name == "nt" else "dbt"))

    def build(full_refresh=False):
        command = [executable, "build", "--project-dir", str(PROJECT), "--profiles-dir", str(PROJECT),
                   "--target-path", str(tmp_path / "target"), "--log-path", str(tmp_path / "logs"),
                   "--exclude", "tag:fixture"]
        if full_refresh:
            command.append("--full-refresh")
        result = subprocess.run(command, env=env, capture_output=True, text=True, timeout=120)
        assert result.returncode == 0, result.stdout + result.stderr

    return build


def snapshot(connection):
    # Build metadata changes each run; compare every business column and row.
    return {name: connection.execute(
        f"SELECT to_jsonb(t) - 'ingest_date_time' - 'update_date_time' - 'dbt_batch_id' "
        f"FROM {relation} t ORDER BY (to_jsonb(t) - 'ingest_date_time' - 'update_date_time' - 'dbt_batch_id')::text"
    ).fetchall() for name, relation in RELATIONS.items()}


def test_historical_dependency_corrections_match_full_refresh(postgres_connection, dbt_build):
    connection = postgres_connection
    # Daily, weekly, monthly and quarterly windows have at least 14 changes.
    connection.execute("""
        INSERT INTO bronze.btc_usd_ohlcv
        SELECT day, 80, 300, 100, 140 + 25 * sin(extract(epoch from day) / 86400 / 9),
               10, day::date, day + interval '2 hours'
        FROM generate_series(timestamp '2014-01-01', timestamp '2023-12-31', interval '1 day') day
    """)
    dbt_build(full_refresh=True)
    before = snapshot(connection)
    for sql in [
        "UPDATE bronze.bgeometrics_btc_technical_indicators SET macd=999, ingest_date_time=now() WHERE d='2024-01-01'",
        "UPDATE bronze.usd_eur_rates SET rate=0.5, ingest_date_time=now() WHERE date='2024-01-01'",
        "UPDATE bronze.usd_chf_rates SET rate=0.4, ingest_date_time=now() WHERE date='2024-01-01'",
        "UPDATE bronze.btc_usd_ohlcv SET close=290, ingest_date_time=now() WHERE date='2023-12-31'",
    ]:
        connection.execute(sql)
        dbt_build()
        normal = snapshot(connection)
        dbt_build()
        assert snapshot(connection) == normal, "Repeated normal builds changed business values"
        dbt_build(full_refresh=True)
        assert snapshot(connection) == normal, "Historical correction differs from full refresh"
    after = snapshot(connection)
    assert after["daily"] != before["daily"]
    for period in ("daily", "week", "month", "quarter"):
        column = "date_prices" if period == "daily" else "iso_week_start_date" if period == "week" else f"{period}_start_date"
        old_rsi = {row[0][column]: row[0]["rsi"] for row in before[period]}
        assert any(row[0][column] > "2023-12-31" and row[0]["rsi"] != old_rsi.get(row[0][column])
                   for row in after[period]), f"No downstream {period} RSI propagation"
    assert connection.execute("SELECT macd_usd, close_eur, close_chf FROM " + RELATIONS["daily"] +
                              " WHERE date_prices='2024-01-01'").fetchone() == (999, 57.5, 46)


@pytest.mark.parametrize("changes, expected", [
    ([None] + [1] * 14, 100),
    ([None] + [-1] * 14, 0),
    ([None] + [0] * 14, None),
    ([None] + [1] * 13, None),
    ([None] + [-1] * 13, None),
    ([None] * 15, None),
    ([1] * 7 + [None] + [1] * 7, None),
])
def test_rsi_edge_cases_execute_postgresql(postgres_connection, changes, expected):
    macro = Environment().from_string((PROJECT / "macros/rsi/rsi.sql").read_text()).module.rsi
    rows = ",".join(f"({index}, {'NULL' if change is None else change}::double precision)"
                    for index, change in enumerate(changes))
    result = postgres_connection.execute(
        f"WITH changes(date, change) AS (VALUES {rows}) "
        f"SELECT {macro('change', 14)} FROM changes ORDER BY date DESC LIMIT 1"
    ).fetchone()
    assert result[2] == expected
    assert result[3] == expected
