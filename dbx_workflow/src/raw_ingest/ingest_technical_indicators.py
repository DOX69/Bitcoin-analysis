import logging
import os
from uuid import uuid4

import psycopg

from raw_ingest.BGeometricsFetcher import BGeometricsFetcher
from raw_ingest.DbWriter import BRONZE_SCHEMA
from raw_ingest.ingest import ingest_fetcher_data


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
    return ingest_fetcher_data(connection, fetcher, run_id, logger)


def main():
    database_url = os.environ["DATABASE_URL"]
    with psycopg.connect(database_url, autocommit=True) as connection:
        ingest_technical_indicators(connection, str(uuid4()))


if __name__ == "__main__":
    main()
