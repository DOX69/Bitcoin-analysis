import logging
import os
from uuid import uuid4

import pandas as pd
import psycopg

from raw_ingest.CoinbaseFetcher import CoinbaseFetcher
from raw_ingest.DbWriter import BRONZE_SCHEMA, DbWriter, get_latest_date
from raw_ingest.FrankfurterFetcher import FrankfurterFetcher


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
    latest_date = get_latest_date(connection, fetcher.table_name)

    if latest_date is None:
        logger.info("Fetching full history for %s-%s", ticker, currency)
        frame = fetcher.fetch_historical_data()
    else:
        logger.info("Fetching %s-%s from %s", ticker, currency, latest_date)
        frame = fetcher.fetch_historical_data(
            start_date_time=pd.Timestamp(latest_date)
        )

    return DbWriter(
        connection,
        logger,
        fetcher.table_name,
        frame,
        run_id,
    ).save_batch()


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
