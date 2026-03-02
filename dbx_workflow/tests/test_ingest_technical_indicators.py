"""Tests for technical indicators ingestion entry point."""

import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime
import pandas as pd

from raw_ingest.ingest_technical_indicators import ingest_technical_indicators

class TestIngestTechnicalIndicators:
    """Test ingest_technical_indicators function."""

    @patch('raw_ingest.ingest_technical_indicators.SparkSession')
    @patch('raw_ingest.ingest_technical_indicators.DbWriter')
    @patch('raw_ingest.ingest_technical_indicators.BGeometricsFetcher')
    def test_ingest_tech_indicators_new_table(
        self, mock_fetcher_class, mock_writer_class, mock_spark_session_cls, sample_pandas_df
    ):
        """Test full historical fetch for a new table."""
        mock_spark = MagicMock()
        mock_spark_session_cls.builder.getOrCreate.return_value = mock_spark

        # Setup mock for table not found
        mock_spark.read.table.return_value.select.return_value.collect.side_effect = Exception("Table not found")
        
        # Setup BGeometricsFetcher mock
        mock_fetcher = MagicMock()
        mock_fetcher.full_path_table_name = "dev.bronze.bgeometrics_btc_technical_indicators"
        mock_fetcher.fetch_historical_data.return_value = sample_pandas_df # Any DF works to prove wiring
        mock_fetcher_class.return_value = mock_fetcher
        
        # Setup DbWriter mock
        mock_writer = MagicMock()
        mock_writer_class.return_value = mock_writer
        
        # Call the function
        result = ingest_technical_indicators("dev", "bronze")
        
        # Verify success
        assert result is True
        
        # Verify DbWriter was initialized appropriately
        mock_writer_class.assert_called_once()
        args, kwargs = mock_writer_class.call_args
        assert args[0] is mock_spark 

        # Verify full fetch (no start_date_time)
        mock_fetcher.fetch_historical_data.assert_called_once_with()

        # Verify DbWriter.save_delta_table was called as a new table
        mock_writer.save_delta_table.assert_called_once_with(False)

    @patch('raw_ingest.ingest_technical_indicators.SparkSession')
    @patch('raw_ingest.ingest_technical_indicators.DbWriter')
    @patch('raw_ingest.ingest_technical_indicators.BGeometricsFetcher')
    def test_ingest_tech_indicators_incremental(
        self, mock_fetcher_class, mock_writer_class, mock_spark_session_cls, sample_pandas_df
    ):
        """Test incremental fetch for an existing table."""
        mock_spark = MagicMock()
        mock_spark_session_cls.builder.getOrCreate.return_value = mock_spark

        # Setup mock for existing table with latest date
        latest_date = datetime(2026, 2, 24).date()
        mock_result = MagicMock()
        mock_result.__getitem__.return_value = latest_date
        mock_spark.read.table.return_value.select.return_value.collect.return_value = [mock_result]
        
        mock_fetcher = MagicMock()
        mock_fetcher.full_path_table_name = "dev.bronze.bgeometrics_btc_technical_indicators"
        mock_fetcher.fetch_historical_data.return_value = sample_pandas_df
        mock_fetcher_class.return_value = mock_fetcher
        
        mock_writer = MagicMock()
        mock_writer_class.return_value = mock_writer
        
        # Call the function
        result = ingest_technical_indicators("dev", "bronze")
        
        assert result is True
        
        # Verify fetch was called with start_date_time
        fetch_call = mock_fetcher.fetch_historical_data.call_args
        assert fetch_call is not None
        assert 'start_date_time' in fetch_call[1]
        
        mock_writer.save_delta_table.assert_called_once_with(True)

    @patch('raw_ingest.ingest_technical_indicators.SparkSession')
    @patch('raw_ingest.ingest_technical_indicators.BGeometricsFetcher')
    def test_ingest_tech_indicators_fetcher_error(
        self, mock_fetcher_class, mock_spark_session_cls
    ):
        """Test error handling when fetcher fails."""
        mock_spark = MagicMock()
        mock_spark_session_cls.builder.getOrCreate.return_value = mock_spark
        mock_spark.read.table.return_value.select.return_value.collect.side_effect = Exception("Table not found")
        
        mock_fetcher = MagicMock()
        mock_fetcher.fetch_historical_data.side_effect = Exception("API Error")
        mock_fetcher_class.return_value = mock_fetcher
        
        result = ingest_technical_indicators("dev", "bronze")
        
        assert result is False
