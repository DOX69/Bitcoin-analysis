import argparse
import logging
import os
from datetime import datetime
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv
from pyspark.shell import spark
from pyspark.sql import functions as f
from raw_ingest import CoinbaseFetcher
from raw_ingest import taxis

# Charger config
load_dotenv()

# Setup logging
log_dir = Path(os.getenv("LOG_DIR", "logs"))
log_dir.mkdir(exist_ok=True)

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_dir / f"bitcoin_ingest_{datetime.now().strftime('%Y%m%d')}.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


def ingest_ticker_data(ticker: str, currency: str,catalog: str, schema: str):
    """
    Pipeline d'ingestion Bitcoin
    À appeler tous les jours
    """
    try:
        # Initialiser fetcher
        fetcher = CoinbaseFetcher.CoinbaseFetcher(
            ticker,
            currency,
            catalog,
            schema
        )
        full_path_table_name = fetcher.full_path_table_name
        is_table_exists = spark.catalog.tableExists(full_path_table_name)
        # ÉTAPE 1 : Fetch dernière date dans la table bronze
        logger.info(f"\n[1/2] Fetching latest ingested data date for {full_path_table_name} ...")
        if is_table_exists:
            latest_date = spark.read.table(full_path_table_name).select(f.min("date")).collect()[0][0]
            logger.info(f"\n[2/2] Historical data already exists - skipping full fetch - Incremental fetch from {latest_date}...")
            latest_date_time = pd.to_datetime(latest_date)
            historical = fetcher.fetch_historical_data(start_date_time=latest_date_time)
            fetcher.save_bronze_table(historical)
        else:
            logger.info("\n[2/2] First run detected - Fetching full historical ... ")
            historical = fetcher.fetch_historical_data()
            fetcher.save_bronze_table(historical)

        logger.info("\n" + "=" * 80)
        logger.info("✅ INGESTION PIPELINE COMPLETED SUCCESSFULLY")
        logger.info("=" * 80)

        return True

    except Exception as e:
        logger.error(f"\n❌ PIPELINE FAILED: {e}", exc_info=True)
        return False


def main():
    logger.info("=" * 80)
    logger.info("🚀 TICKER DATA INGESTION PIPELINE STARTED")
    logger.info("=" * 80)
    # Process command-line arguments
    parser = argparse.ArgumentParser(
        description="Databricks job with catalog and schema parameters",
    )
    parser.add_argument("--catalog", required=True, default="dev")
    parser.add_argument("--schema", required=True)
    args = parser.parse_args()

    # Set the default catalog and schema
    spark.sql(f"USE CATALOG {args.catalog}")
    spark.sql(f"USE SCHEMA {args.schema}")

    # Example: just find all taxis from a sample catalog
    taxis.find_all_taxis().show(5)

    ingest_ticker_data('BTC','USD',args.catalog,args.schema)



if __name__ == "__main__":
    main()
