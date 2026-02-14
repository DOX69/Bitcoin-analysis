"""Tests for DbWriter class and overwrite_replace_where function."""

import pytest
from unittest.mock import MagicMock, call

from raw_ingest.DbWriter import DbWriter, overwrite_replace_where


class TestOverwriteReplaceWhere:
    """Test overwrite_replace_where function."""

    def test_overwrite_replace_where_calls_write_correctly(self):
        """Test that overwrite_replace_where writes with correct options."""
        # Mock the write operations
        mock_df = MagicMock()
        mock_writer = MagicMock()
        mock_df.write = mock_writer
        
        # Setup the chain of method calls
        mock_writer.partitionBy.return_value = mock_writer
        mock_writer.mode.return_value = mock_writer
        mock_writer.option.return_value = mock_writer

        # Call the function
        overwrite_replace_where(
            spark_df=mock_df,
            partitioned_cols=["date"],
            full_path_table_name="test_catalog.test_schema.test_table",
            replace_where_condition="date >= '2022-01-01'"
        )

        # Verify the chain of calls
        mock_writer.partitionBy.assert_called_once_with(["date"])
        mock_writer.mode.assert_called_once_with("overwrite")
        
        # Verify options were set
        option_calls = mock_writer.option.call_args_list
        assert call("replaceWhere", "date >= '2022-01-01'") in option_calls
        assert call("mergeSchema", "true") in option_calls

    def test_overwrite_replace_where_with_multiple_partitions(self):
        """Test with multiple partition columns."""
        mock_df = MagicMock()
        mock_writer = MagicMock()
        mock_df.write = mock_writer
        
        mock_writer.partitionBy.return_value = mock_writer
        mock_writer.mode.return_value = mock_writer
        mock_writer.option.return_value = mock_writer

        overwrite_replace_where(
            spark_df=mock_df,
            partitioned_cols=["date", "ticker"],
            full_path_table_name="test.table",
            replace_where_condition="date >= '2022-01-01'"
        )

        mock_writer.partitionBy.assert_called_once_with(["date", "ticker"])


class TestDbWriterInit:
    """Test DbWriter initialization."""

    def test_init_sets_attributes(self, mock_logger, sample_pandas_df):
        """Test that initialization sets attributes correctly."""
        mock_spark = MagicMock()
        writer = DbWriter(
            spark=mock_spark,
            logger=mock_logger,
            full_path_table_name="catalog.schema.table",
            pandas_df=sample_pandas_df
        )

        assert writer.full_path_table_name == "catalog.schema.table"
        assert writer.pandas_df is sample_pandas_df
        assert writer.logger is mock_logger
        assert writer.spark is mock_spark

    def test_init_logs_initialization(self, mock_logger, sample_pandas_df):
        """Test that initialization logs the table name."""
        mock_spark = MagicMock()
        DbWriter(
            spark=mock_spark,
            logger=mock_logger,
            full_path_table_name="dev.bronze.btc_usd_ohlcv",
            pandas_df=sample_pandas_df
        )

        # Check that info was logged with the table name
        info_calls = [call for call in mock_logger.method_calls if 'info' in str(call)]
        assert len(info_calls) > 0


class TestDbWriterSaveDeltaTable:
    """Test DbWriter.save_delta_table method."""

    def test_save_delta_table_creates_new_table(self, mock_logger, sample_pandas_df):
        """Test creating a new table with partitioning."""
        mock_spark = MagicMock()
        # Setup mock Spark DataFrame
        mock_spark_df = MagicMock()
        mock_spark.createDataFrame.return_value = mock_spark_df
        
        # Setup method chaining
        mock_spark_df.withColumn.return_value = mock_spark_df
        mock_spark_df.count.return_value = 5
        
        # Setup write chain
        mock_writer = MagicMock()
        mock_spark_df.write = mock_writer
        mock_writer.partitionBy.return_value = mock_writer
        mock_writer.mode.return_value = mock_writer
        mock_writer.option.return_value = mock_writer

        # Create writer and save
        writer = DbWriter(
            spark=mock_spark,
            logger=mock_logger,
            full_path_table_name="test.bronze.btc_usd",
            pandas_df=sample_pandas_df
        )
        writer.save_delta_table(is_table_found=False)

        # Verify DataFrame was created from pandas
        mock_spark.createDataFrame.assert_called_once()

        # Verify columns were added
        assert mock_spark_df.withColumn.call_count == 2
        
        # Verify write operations for new table
        mock_writer.partitionBy.assert_called_once_with("date")
        mock_writer.mode.assert_called_once_with("overwrite")
        mock_writer.option.assert_called_once_with("mergeSchema", "true")

    def test_save_delta_table_appends_to_existing_table(self, mock_logger, sample_pandas_df):
        """Test appending to an existing table."""
        mock_spark = MagicMock()
        # Setup mock Spark DataFrame
        mock_spark_df = MagicMock()
        mock_spark.createDataFrame.return_value = mock_spark_df
        
        # Setup method chaining
        mock_spark_df.withColumn.return_value = mock_spark_df
        mock_spark_df.count.return_value = 5
        
        # Setup write chain
        mock_writer = MagicMock()
        mock_spark_df.write = mock_writer
        mock_writer.mode.return_value = mock_writer

        # Create writer and save
        writer = DbWriter(
            spark=mock_spark,
            logger=mock_logger,
            full_path_table_name="test.bronze.btc_usd",
            pandas_df=sample_pandas_df
        )
        writer.save_delta_table(is_table_found=True)

        # Verify append mode was used
        mock_writer.mode.assert_called_once_with("append")
        mock_writer.saveAsTable.assert_called_once_with("test.bronze.btc_usd")

    def test_save_delta_table_adds_date_column(self, mock_logger, sample_pandas_df):
        """Test that date column is added from time column."""
        mock_spark = MagicMock()
        # Setup mock Spark DataFrame
        mock_spark_df = MagicMock()
        mock_spark.createDataFrame.return_value = mock_spark_df
        
        # Track withColumn calls
        with_column_calls = []
        def track_with_column(col_name, col_expr):
            with_column_calls.append(col_name)
            return mock_spark_df
        
        mock_spark_df.withColumn.side_effect = track_with_column
        mock_spark_df.count.return_value = 5
        
        # Setup write chain
        mock_writer = MagicMock()
        mock_spark_df.write = mock_writer
        mock_writer.mode.return_value = mock_writer

        # Create writer and save
        writer = DbWriter(
            spark=mock_spark,
            logger=mock_logger,
            full_path_table_name="test.bronze.btc_usd",
            pandas_df=sample_pandas_df
        )
        writer.save_delta_table(is_table_found=True)

        # Verify both columns were added
        assert "date" in with_column_calls
        assert "ingest_date_time" in with_column_calls

    def test_save_delta_table_handles_exceptions(self, mock_logger, sample_pandas_df):
        """Test exception handling during save."""
        mock_spark = MagicMock()
        # Setup mock to raise exception
        mock_spark_df = MagicMock()
        mock_spark.createDataFrame.return_value = mock_spark_df
        mock_spark_df.withColumn.return_value = mock_spark_df
        
        # Make write raise an exception
        mock_writer = MagicMock()
        mock_spark_df.write = mock_writer
        mock_writer.mode.return_value = mock_writer
        mock_writer.saveAsTable.side_effect = Exception("Database connection failed")

        writer = DbWriter(
            spark=mock_spark,
            logger=mock_logger,
            full_path_table_name="test.bronze.btc_usd",
            pandas_df=sample_pandas_df
        )

        # Should raise the exception
        with pytest.raises(Exception, match="Database connection failed"):
            writer.save_delta_table(is_table_found=True)

        # Verify error was logged
        error_calls = [call for call in mock_logger.method_calls if 'error' in str(call)]
        assert len(error_calls) > 0

    def test_save_delta_table_logs_row_count(self, mock_logger, sample_pandas_df):
        """Test that row count is logged."""
        mock_spark = MagicMock()
        # Setup mock Spark DataFrame
        mock_spark_df = MagicMock()
        mock_spark.createDataFrame.return_value = mock_spark_df
        
        mock_spark_df.withColumn.return_value = mock_spark_df
        mock_spark_df.count.return_value = 42  # Specific count to verify
        
        # Setup write chain
        mock_writer = MagicMock()
        mock_spark_df.write = mock_writer
        mock_writer.mode.return_value = mock_writer

        writer = DbWriter(
            spark=mock_spark,
            logger=mock_logger,
            full_path_table_name="test.bronze.btc_usd",
            pandas_df=sample_pandas_df
        )
        writer.save_delta_table(is_table_found=True)

        # Verify count was called
        mock_spark_df.count.assert_called()

        # Verify logging included row count
        info_calls = [str(call) for call in mock_logger.method_calls if 'info' in str(call)]
        # Should have logged the count in one of the info messages
        assert any('42' in call for call in info_calls)
