import pandas as pd

from raw_ingest.DbWriter import DbWriter, get_latest_date


def ingest_fetcher_data(connection, fetcher, run_id, logger):
    latest_date = get_latest_date(connection, fetcher.table_name)
    if latest_date is None:
        logger.info("Fetching full history for %s", fetcher.table_name)
        frame = fetcher.fetch_historical_data()
    else:
        logger.info("Fetching %s from %s", fetcher.table_name, latest_date)
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
