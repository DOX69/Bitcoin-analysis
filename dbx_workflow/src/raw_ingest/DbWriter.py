import pandas as pd
from pyspark.sql.functions import col, current_timestamp


class DbWriter:
    def __init__(
            self,
            spark,
            logger,
            full_path_table_name : str,
            pandas_df: pd.DataFrame
    ):
        self.spark = spark
        self.logger = logger
        self.full_path_table_name = full_path_table_name
        self.pandas_df = pandas_df

        self.logger.info("-" * 80)
        self.logger.info(f"✓ DbWriter initialized for {self.full_path_table_name} delta table.")
        self.logger.info("-" * 80)
        
    def save_delta_table(self, is_table_found: bool) -> None:
        """
        Save DataFrame to bronze table
        Returns:
            Delta table saved
        """
        spark_df = (
                    self.spark.createDataFrame(self.pandas_df)
                    .withColumn("date",col("time").cast("date"))
                    .withColumn("ingest_date_time",current_timestamp())
                    )

        try:
            if is_table_found:
                spark_df.write.mode("append").saveAsTable(self.full_path_table_name)
                self.logger.info(f"✓ Append to {self.full_path_table_name} succeeded ({spark_df.count()} rows appended)")
            else:
                # Create new table
                spark_df.write.partitionBy("date").mode("overwrite").option("mergeSchema", "true").saveAsTable(self.full_path_table_name)
                self.logger.info(f"✓ Saved to {self.full_path_table_name} succeeded ({spark_df.count()} rows)")
        except Exception as e:
            self.logger.error(f"✗ Failed to save to table: {e}")
            raise
