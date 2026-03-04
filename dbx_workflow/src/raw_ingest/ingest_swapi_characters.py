import argparse
import logging
import os
import sys
from pathlib import Path
import pandas as pd
from dotenv import load_dotenv
from pyspark.sql import SparkSession
from pyspark.sql import functions as f
from raw_ingest.SwapiFetcher import SwapiFetcher
from raw_ingest.DbWriter import DbWriter
from raw_ingest.logger import CustomFormatter

# Charger config
load_dotenv()

# Setup logging
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

def ingest_swapi_characters(catalog: str, schema: str) -> bool:
    """
    Pipeline d'ingestion SWAPI
    """
    try:
        spark = SparkSession.builder.getOrCreate()
        fetcher = SwapiFetcher(logger, catalog, schema)
        full_path_table_name = fetcher.full_path_table_name

        try:
            # Check for latest data (partitioned by 'created' date usually, 
            # but for Star Wars maybe we just daily full refresh or look at 'edited')
            # For simplicity, let's look at the 'edited' column if it exists to see if we need a full refresh.
            # However, the requirement says "fetches all star wars characters".
            # SWAPI is small, usually we do a full refresh.
            spark.read.table(full_path_table_name).limit(1).collect()
            is_table_found = True
        except Exception:
            logger.info(f"🔎 No table {full_path_table_name} found.")
            is_table_found = False

        logger.info(f"🚀 Starting SWAPI characters ingestion into {full_path_table_name}...")
        
        # SWAPI is small and doesn't support date filters easily via URL params
        # (mostly page numbers), so we do a full fetch.
        fetched_pandas_df = fetcher.fetch_historical_data()

        if not fetched_pandas_df.empty:
            # Bronze layer: raw data
            # SWAPI 'created' and 'edited' are strings, we might want to cast them to timestamp in silver,
            # but for partitioning in DbWriter, we need a 'time' column.
            if 'created' in fetched_pandas_df.columns:
                fetched_pandas_df['time'] = pd.to_datetime(fetched_pandas_df['created'])
            
            DbWriter(spark, logger, full_path_table_name, fetched_pandas_df).save_delta_table(is_table_found)
            logger.info(f"✅ Successfully ingested {len(fetched_pandas_df)} characters.")
        else:
            logger.warning("No data fetched from SWAPI.")

        return True

    except Exception as e:
        logger.error(f"\n❌ SWAPI INGESTION FAILED: {e}", exc_info=True)
        return False

def main():
    parser = argparse.ArgumentParser(description="SWAPI Characters Ingestion")
    parser.add_argument("--catalog", required=True, help="Target catalog")
    parser.add_argument("--schema", required=True, help="Target schema")
    args = parser.parse_args()

    success = ingest_swapi_characters(args.catalog, args.schema)
    if not success:
        sys.exit(1)

if __name__ == "__main__":
    main()
