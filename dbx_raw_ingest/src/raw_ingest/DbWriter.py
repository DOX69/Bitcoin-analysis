import logging
import pandas as pd
import os
from dotenv import load_dotenv
from pyspark.sql import DataFrame
from pyspark.sql.functions import col, current_timestamp
from databricks.sdk.runtime import spark

# Charger variables d'environnement
load_dotenv()

# Configuration logging
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def overwrite_replace_where(
        spark_df: DataFrame,
        partitioned_cols:list[str],
        full_path_table_name:str,
        replace_where_condition:str
) -> None:
    """
    Merge delta table
    :param replace_where_condition: replace where logic (e.g. "f"date >= '{start_date}'")
    :param full_path_table_name: Full path to table
    :param spark_df: Spark DataFrame
    :param partitioned_cols: List of columns to merge
    :return:  None
    """
    (
        spark_df.write
        .partitionBy(partitioned_cols)
        .mode("overwrite")
        .option("replaceWhere", replace_where_condition)
        .option("mergeSchema", "true")
        .saveAsTable(full_path_table_name)
    )
class DbWriter:
    def __init__(
            self,
            full_path_table_name : str,
            pandas_df: pd.DataFrame
    ):
        self.full_path_table_name = full_path_table_name
        self.pandas_df = pandas_df

        logger.info("-" * 80)
        logger.info(f"✓ DbWriter initialized for {self.full_path_table_name} delta table")
        logger.info("-" * 80)
    def save_delta_table(self, is_table_found: bool) -> None:
        """
        Save DataFrame to bronze table
        Returns:
            Delta table saved
        """
        spark_df = (
                    spark.createDataFrame(self.pandas_df)
                    .withColumn("date",col("time").cast("date"))
                    .withColumn("ingest_date_time",current_timestamp())
                    )

        try:
            if is_table_found:
                spark_df.write.mode("append").saveAsTable(self.full_path_table_name)
                logger.info(f"✓ Append to {self.full_path_table_name} ({spark_df.count()} rows appended)")
            else:
                # Create new table
                spark_df.write.partitionBy("date").mode("overwrite").option("mergeSchema", "true").saveAsTable(self.full_path_table_name)
                logger.info(f"✓ Saved to {self.full_path_table_name} ({spark_df.count()} rows)")

        except Exception as e:
            logger.error(f"✗ Failed to save to table: {e}")
            raise