import logging
import os
from uuid import uuid4

import pandas as pd
import psycopg

from raw_ingest.BGeometricsFetcher import BGeometricsFetcher
from raw_ingest.DbWriter import BRONZE_SCHEMA, DbWriter, get_latest_date


logger = logging.getLogger(__name__)


def get_fetcher(pipeline_logger=logger):
    return BGeometricsFetcher(
        pipeline_logger,
        "BTC",
        "USD",
        None,
        BRONZE_SCHEMA,
    )


def ingest_technical_indicators(
    connection,
    run_id,
    *,
    fetcher=None,
    logger=logger,
):
    fetcher = fetcher or get_fetcher(logger)
    latest_date = get_latest_date(connection, fetcher.table_name)

    if latest_date is None:
        logger.info("Fetching full BGeometrics indicator history")
        frame = fetcher.fetch_historical_data()
    else:
        logger.info("Fetching BGeometrics indicators from %s", latest_date)
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


def main():
    database_url = os.environ["DATABASE_URL"]
    with psycopg.connect(database_url, autocommit=True) as connection:
        ingest_technical_indicators(connection, str(uuid4()))


if __name__ == "__main__":
    main()
