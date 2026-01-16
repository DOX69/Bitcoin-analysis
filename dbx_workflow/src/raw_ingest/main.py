import argparse
import logging
import os
import sys
from pathlib import Path
import pandas as pd
from dotenv import load_dotenv
from databricks.sdk.runtime import spark
from pyspark.sql import functions as f
from raw_ingest.CoinbaseFetcher import CoinbaseFetcher
from raw_ingest.DbWriter import DbWriter
from raw_ingest.logger import CustomFormatter

# Charger config
load_dotenv()

# Setup logging
log_dir = Path(os.getenv("LOG_DIR", "logs"))
log_dir.mkdir(exist_ok=True)

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format='%(asctime)s - %(pathname)s:%(lineno)d - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)

logger = logging.getLogger(__name__)

for handler in logger.handlers:
    handler.setFormatter(CustomFormatter())

for handler in logging.root.handlers:
    handler.setFormatter(CustomFormatter())

def ingest_ticker_data(ticker: str, currency: str,catalog: str, schema: str) -> bool:
    """
    Pipeline d'ingestion crypto
    À appeler tous les jours
    """
    try:
        # Initialiser fetcher
        fetcher = CoinbaseFetcher(
            logger,
            ticker,
            currency,
            catalog,
            schema
        )
        full_path_table_name: str = fetcher.full_path_table_name

        try:
            latest_date = spark.read.table(full_path_table_name).select(f.max("date")).collect()[0][0]
        except Exception :
            logger.info(f"🔎 No table {full_path_table_name} found for {ticker}-{currency}.")
            latest_date = None
            pass
        is_table_found = True if latest_date is not None else False

        # ÉTAPE 1 : Fetch dernière date dans la table bronze
        logger.info(f"[1/2] Fetching latest ingested data date for {full_path_table_name} ...")
        if is_table_found:
            latest_date_time = pd.to_datetime(latest_date)
            logger.info(f"[2/2] Historical data already exists - skipping full fetch - Incremental fetch from {latest_date}...")
            fetched_pandas_df = fetcher.fetch_historical_data(start_date_time=latest_date_time)
        else:
            logger.info("[2/2] First run detected - Fetching full historical ... ")
            fetched_pandas_df = fetcher.fetch_historical_data()

        # Save delta table
        DbWriter(logger, full_path_table_name, fetched_pandas_df).save_delta_table(is_table_found)

        logger.info("-" * 80)
        logger.info(f"End ingesting {ticker.upper()}-{currency.upper()} data.")
        logger.info("-" * 80)

        return True

    except Exception as e:
        logger.error(f"\n❌ PIPELINE FAILED: {e}", exc_info=True)
        return False


def main():
    logger.info("=" * 80)
    logger.info("🚀 CRYPTO DATA INGESTION PIPELINE STARTED")
    logger.info("=" * 80)

    # Process command-line arguments
    parser = argparse.ArgumentParser(
        description="Databricks job with catalog and schema parameters",
    )
    parser.add_argument("--catalog", required=True, default="dev")
    parser.add_argument("--schema", required=True)
    args = parser.parse_args()

    ticker_ids = [
        ("BTC", "USD"),
        ("BTC", "EUR"),
        ("AAVE", "USD"),
        ("ETH", "USD"),
        ("ETH", "EUR"),
        ("ETH", "BTC"),
    ]
    for ticker, currency in ticker_ids:
        succeed = ingest_ticker_data(ticker.upper(),currency.upper(),args.catalog,args.schema)
        if not succeed:
            sys.exit(0)

    logger.info("=" * 80)
    logger.info("🚀 CRYPTO DATA INGESTION PIPELINE ENDED")
    logger.info("=" * 80)



if __name__ == "__main__":
    main()
