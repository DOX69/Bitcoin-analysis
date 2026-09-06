import importlib
from datetime import date, datetime, timezone
from types import SimpleNamespace
from unittest.mock import Mock

import psycopg
import pytest
from psycopg import sql

from raw_ingest.ingest_market_price_data import ingest_ticker_data
from raw_ingest.ingest_technical_indicators import ingest_technical_indicators


class FixedDatetime(datetime):
    @classmethod
    def now(cls):
        return cls(2026, 3, 1)


@pytest.fixture(params=[("BTC", "USD"), ("ETH", "USD"), ("USD", "EUR"), ("USD", "CHF"), None])
def adapter(request, monkeypatch, postgres_connection, mock_logger, mock_bgeometrics_api_response):
    pair = request.param
    kind = "indicators" if pair is None else "rates" if pair[0] == "USD" else "market"
    module_name = {"market": "CoinbaseFetcher", "rates": "FrankfurterFetcher", "indicators": "BGeometricsFetcher"}[kind]
    module = importlib.import_module(f"raw_ingest.{module_name}")
    monkeypatch.setattr(module, "datetime", FixedDatetime)
    table = (
        "bgeometrics_btc_technical_indicators" if pair is None
        else "_".join(pair).lower() + ("_rates" if kind == "rates" else "_ohlcv")
    )
    value_column = {"market": "close", "rates": "rate", "indicators": "rsi"}[kind]
    state = SimpleNamespace(values={"2026-02-24": 10.0, "2026-02-25": 20.0}, starts=[], invalid=False)

    def get(url, *, params, timeout):
        assert timeout == 10
        if kind == "market":
            start, end = params["start"][:10], params["end"][:10]
            assert params["granularity"] == 86400
        elif kind == "rates":
            start, end = url.rsplit("/", 1)[1].split("..")
            assert params == {"base": "USD", "symbols": pair[1]}
        else:
            start, end = params.get("startday"), params.get("endday", "2026-03-01")
        state.starts.append(start)
        values = {day: value for day, value in state.values.items() if (start is None or start <= day) and day <= end}
        if kind == "market":
            payload = [
                [int(datetime.fromisoformat(day).replace(tzinfo=timezone.utc).timestamp()), 1, 100, 5, value, 7]
                for day, value in values.items()
            ]
        elif kind == "rates":
            payload = {"rates": {day: {pair[1]: value} for day, value in values.items()}}
        else:
            payload = [{**mock_bgeometrics_api_response[0], "d": day, "rsi": value} for day, value in values.items()]
        return Mock(status_code=200, json=Mock(return_value={"invalid": True} if state.invalid else payload))

    monkeypatch.setattr(module.requests, "get", get)

    def ingest(run_id):
        if pair is None:
            return ingest_technical_indicators(postgres_connection, run_id, logger=mock_logger)
        return ingest_ticker_data(postgres_connection, *[part.lower() for part in pair], run_id, logger=mock_logger)

    def rows():
        query = sql.SQL(
            "SELECT date, {}, run_id, ingest_date_time FROM bronze.{} ORDER BY date"
        ).format(sql.Identifier(value_column), sql.Identifier(table))
        return postgres_connection.execute(query).fetchall()

    return SimpleNamespace(ingest=ingest, rows=rows, state=state, table=table, value_column=value_column, kind=kind)


def test_real_adapters_full_history_then_inclusive_replay(adapter):
    assert adapter.ingest("initial") == 2
    initial = adapter.rows()
    expected_start = {"market": "2013-03-04", "rates": "2010-01-01", "indicators": None}
    assert adapter.state.starts[0] == expected_start[adapter.kind]

    adapter.state.values = {"2026-02-25": 25.0, "2026-02-26": 30.0}
    adapter.state.starts.clear()
    assert adapter.ingest("replay") == 2
    assert adapter.state.starts[0] == "2026-02-25"
    rows = adapter.rows()
    assert rows[0] == initial[0]
    assert [row[:3] for row in rows] == [
        (date(2026, 2, 24), 10.0, "initial"),
        (date(2026, 2, 25), 25.0, "replay"),
        (date(2026, 2, 26), 30.0, "replay"),
    ]
    assert all(row[3] is not None for row in rows)


def test_real_adapters_fetch_failure_and_empty_result_preserve_rows(adapter):
    assert adapter.ingest("initial") == 2
    initial = adapter.rows()
    adapter.state.invalid = True
    with pytest.raises(ValueError):
        adapter.ingest("failed")
    assert adapter.rows() == initial

    adapter.state.invalid = False
    adapter.state.values = {}
    assert adapter.ingest("empty") == 0
    assert adapter.rows() == initial


def test_real_adapters_write_failure_rolls_back_replay(adapter, postgres_connection):
    assert adapter.ingest("initial") == 2
    initial = adapter.rows()
    postgres_connection.execute(
        sql.SQL("ALTER TABLE bronze.{} ADD CHECK ({} < 100)").format(
            sql.Identifier(adapter.table), sql.Identifier(adapter.value_column)
        )
    )
    adapter.state.values = {"2026-02-25": 25.0, "2026-02-26": 100.0}
    with pytest.raises(psycopg.errors.CheckViolation):
        adapter.ingest("failed-write")
    assert adapter.rows() == initial
