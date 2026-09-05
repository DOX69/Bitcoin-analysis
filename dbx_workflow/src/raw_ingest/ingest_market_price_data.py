import logging
import os
from uuid import uuid4

import psycopg

from raw_ingest.CoinbaseFetcher import CoinbaseFetcher
from raw_ingest.DbWriter import BRONZE_SCHEMA
from raw_ingest.FrankfurterFetcher import FrankfurterFetcher
from raw_ingest.ingest import ingest_fetcher_data


logger = logging.getLogger(__name__)
MARKET_PAIRS = (
    ("BTC", "USD"),
    ("ETH", "USD"),
    ("USD", "EUR"),
    ("USD", "CHF"),
)


def get_fetcher(ticker, currency, pipeline_logger=logger):
    fetcher_class = (
        FrankfurterFetcher
        if ticker == "USD" and currency in {"CHF", "EUR"}
        else CoinbaseFetcher
    )
    return fetcher_class(
        pipeline_logger,
        ticker,
        currency,
        None,
        BRONZE_SCHEMA,
    )


def ingest_ticker_data(
    connection,
    ticker,
    currency,
    run_id,
    *,
    fetcher=None,
    logger=logger,
):
    ticker = ticker.upper()
    currency = currency.upper()
    fetcher = fetcher or get_fetcher(ticker, currency, logger)
    return ingest_fetcher_data(connection, fetcher, run_id, logger)


def ingest_market_data(connection, run_id, pipeline_logger=logger):
    return sum(
        ingest_ticker_data(
            connection,
            ticker,
            currency,
            run_id,
            logger=pipeline_logger,
        )
        for ticker, currency in MARKET_PAIRS
    )


def main():
    database_url = os.environ["DATABASE_URL"]
    with psycopg.connect(database_url, autocommit=True) as connection:
        ingest_market_data(connection, str(uuid4()))


if __name__ == "__main__":
    main()
