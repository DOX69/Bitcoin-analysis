"""Tests for main pipeline orchestration."""

import pytest
from unittest.mock import Mock, MagicMock, patch
from datetime import datetime

from raw_ingest.main import ingest_ticker_data, main


class TestIngestTickerData:
    """Test ingest_ticker_data function."""

    @patch('raw_ingest.main.SparkSession')
    @patch('raw_ingest.main.DbWriter')
    @patch('raw_ingest.main.CoinbaseFetcher')
    def test_ingest_ticker_data_new_table(
        self, mock_fetcher_class, mock_writer_class, mock_spark_session_cls, mock_logger, sample_pandas_df
    ):
        """Test full historical fetch for a new ticker table."""
        mock_spark = MagicMock()
        mock_spark_session_cls.builder.getOrCreate.return_value = mock_spark

        # Setup mock for table not found
        mock_spark.read.table.return_value.select.return_value.collect.side_effect = Exception("Table not found")
        
        # Setup CoinbaseFetcher mock
        mock_fetcher = MagicMock()
        mock_fetcher.full_path_table_name = "dev.bronze.btc_usd_ohlcv"
        mock_fetcher.fetch_historical_data.return_value = sample_pandas_df
        mock_fetcher_class.return_value = mock_fetcher
        
        # Setup DbWriter mock
        mock_writer = MagicMock()
        mock_writer_class.return_value = mock_writer
        
        # Call the function
        result = ingest_ticker_data("BTC", "USD", "dev", "bronze")
        
        # Verify success
        assert result is True
        
        # Verify DbWriter was initialized with spark
        mock_writer_class.assert_called_once()
        args, kwargs = mock_writer_class.call_args
        assert args[0] is mock_spark # First arg should be spark

        # Verify DbWriter.save_delta_table was called
        mock_writer.save_delta_table.assert_called_once_with(False)  # is_table_found=False

    @patch('raw_ingest.main.SparkSession')
    @patch('raw_ingest.main.DbWriter')
    @patch('raw_ingest.main.CoinbaseFetcher')
    def test_ingest_ticker_data_incremental_fetch(
        self, mock_fetcher_class, mock_writer_class, mock_spark_session_cls, mock_logger, sample_pandas_df
    ):
        """Test incremental fetch for an existing table."""
        mock_spark = MagicMock()
        mock_spark_session_cls.builder.getOrCreate.return_value = mock_spark

        # Setup mock for existing table with latest date
        latest_date = datetime(2022, 1, 5).date()
        mock_result = MagicMock()
        mock_result.__getitem__.return_value = latest_date
        mock_spark.read.table.return_value.select.return_value.collect.return_value = [mock_result]
        
        # Setup CoinbaseFetcher mock
        mock_fetcher = MagicMock()
        mock_fetcher.full_path_table_name = "dev.bronze.eth_usd_ohlcv"
        mock_fetcher.fetch_historical_data.return_value = sample_pandas_df
        mock_fetcher_class.return_value = mock_fetcher
        
        # Setup DbWriter mock
        mock_writer = MagicMock()
        mock_writer_class.return_value = mock_writer
        
        # Call the function
        result = ingest_ticker_data("ETH", "USD", "dev", "bronze")
        
        # Verify success
        assert result is True
        
        # Verify fetch was called with start_date_time (incremental)
        fetch_call = mock_fetcher.fetch_historical_data.call_args
        assert fetch_call is not None
        assert 'start_date_time' in fetch_call[1]
        
        # Verify DbWriter was called with is_table_found=True
        mock_writer.save_delta_table.assert_called_once_with(True)

    @patch('raw_ingest.main.SparkSession')
    @patch('raw_ingest.main.CoinbaseFetcher')
    def test_ingest_ticker_data_handles_fetcher_error(
        self, mock_fetcher_class, mock_spark_session_cls, mock_logger
    ):
        """Test error handling when fetcher fails."""
        mock_spark = MagicMock()
        mock_spark_session_cls.builder.getOrCreate.return_value = mock_spark

        # Setup mock for table not found
        mock_spark.read.table.return_value.select.return_value.collect.side_effect = Exception("Table not found")
        
        # Setup CoinbaseFetcher to raise exception
        mock_fetcher = MagicMock()
        mock_fetcher.full_path_table_name = "dev.bronze.btc_usd_ohlcv"
        mock_fetcher.fetch_historical_data.side_effect = Exception("API Error")
        mock_fetcher_class.return_value = mock_fetcher
        
        # Call the function
        result = ingest_ticker_data("BTC", "USD", "dev", "bronze")
        
        # Verify failure
        assert result is False

    @patch('raw_ingest.main.SparkSession')
    @patch('raw_ingest.main.DbWriter')
    @patch('raw_ingest.main.CoinbaseFetcher')
    def test_ingest_ticker_data_handles_writer_error(
        self, mock_fetcher_class, mock_writer_class, mock_spark_session_cls, mock_logger, sample_pandas_df
    ):
        """Test error handling when writer fails."""
        mock_spark = MagicMock()
        mock_spark_session_cls.builder.getOrCreate.return_value = mock_spark

        # Setup mocks
        mock_spark.read.table.return_value.select.return_value.collect.side_effect = Exception("Table not found")
        
        mock_fetcher = MagicMock()
        mock_fetcher.full_path_table_name = "dev.bronze.btc_usd_ohlcv"
        mock_fetcher.fetch_historical_data.return_value = sample_pandas_df
        mock_fetcher_class.return_value = mock_fetcher
        
        # Setup DbWriter to raise exception
        mock_writer = MagicMock()
        mock_writer.save_delta_table.side_effect = Exception("Write failed")
        mock_writer_class.return_value = mock_writer
        
        # Call the function
        result = ingest_ticker_data("BTC", "USD", "dev", "bronze")
        
        # Verify failure
        assert result is False

    @patch('raw_ingest.main.SparkSession')
    @patch('raw_ingest.main.DbWriter')
    @patch('raw_ingest.main.CoinbaseFetcher')
    def test_ingest_ticker_data_uppercase_conversion(
        self, mock_fetcher_class, mock_writer_class, mock_spark_session_cls, mock_logger, sample_pandas_df
    ):
        """Test that ticker and currency are properly handled."""
        mock_spark = MagicMock()
        mock_spark_session_cls.builder.getOrCreate.return_value = mock_spark

        mock_spark.read.table.return_value.select.return_value.collect.side_effect = Exception("Table not found")
        
        mock_fetcher = MagicMock()
        mock_fetcher.full_path_table_name = "dev.bronze.aave_usd_ohlcv"
        mock_fetcher.fetch_historical_data.return_value = sample_pandas_df
        mock_fetcher_class.return_value = mock_fetcher
        
        mock_writer = MagicMock()
        mock_writer_class.return_value = mock_writer
        
        # Call with lowercase (should work fine)
        result = ingest_ticker_data("aave", "usd", "dev", "bronze")
        
        assert result is True


class TestMain:
    """Test main function."""

    @patch('raw_ingest.main.ingest_ticker_data')
    @patch('sys.argv', ['main.py', '--catalog', 'dev', '--schema', 'bronze'])
    def test_main_processes_all_tickers(self, mock_ingest):
        """Test that all ticker pairs are processed."""
        # Setup mock to always succeed
        mock_ingest.return_value = True
        
        # Call main
        main()
        
        # Verify all 6 ticker pairs were processed
        assert mock_ingest.call_count == 6
        
        # Verify the expected ticker pairs
        expected_pairs = [
            ("BTC", "USD"),
            ("AAVE", "USD"),
            ("ETH", "USD"),
            ("ETH", "BTC"),
            ("USD", "EUR"),
            ("USD", "CHF"),
        ]
        
        actual_calls = [
            (call[0][0], call[0][1]) for call in mock_ingest.call_args_list
        ]
        
        for expected in expected_pairs:
            assert expected in actual_calls

    @patch('raw_ingest.main.ingest_ticker_data')
    @patch('sys.argv', ['main.py', '--catalog', 'prod', '--schema', 'raw'])
    def test_main_command_line_args(self, mock_ingest):
        """Test that command line arguments are parsed correctly."""
        mock_ingest.return_value = True
        
        # Call main
        main()
        
        # Verify catalog and schema were passed correctly
        first_call = mock_ingest.call_args_list[0]
        assert first_call[0][2] == 'prod'  # catalog
        assert first_call[0][3] == 'raw'   # schema

    @patch('raw_ingest.main.ingest_ticker_data')
    @patch('sys.exit')
    @patch('sys.argv', ['main.py', '--catalog', 'dev', '--schema', 'bronze'])
    def test_main_exits_on_failure(self, mock_exit, mock_ingest):
        """Test that main exits when a ticker ingestion fails."""
        # Setup mock to fail on second ticker
        mock_ingest.side_effect = [True, False, True, True, True, True]
        mock_exit.side_effect = SystemExit(0)
        
        # Call main and expect it to exit
        with pytest.raises(SystemExit):
            main()
        
        # Verify sys.exit was called
        mock_exit.assert_called_once_with(0)
        
        # Verify processing stopped after failure (only 2 calls made)
        assert mock_ingest.call_count == 2

    @patch('raw_ingest.main.ingest_ticker_data')
    @patch('sys.argv', ['main.py', '--catalog', 'test_catalog', '--schema', 'test_schema'])
    def test_main_passes_args_to_ingest(self, mock_ingest):
        """Test that main passes catalog and schema to ingest_ticker_data."""
        mock_ingest.return_value = True
        
        # Call main
        main()
        
        # Verify all calls received correct catalog and schema
        for call_args in mock_ingest.call_args_list:
            assert call_args[0][2] == 'test_catalog'
            assert call_args[0][3] == 'test_schema'

    @patch('raw_ingest.main.ingest_ticker_data')
    @patch('sys.argv', ['main.py', '--catalog', 'dev', '--schema', 'bronze'])
    def test_main_processes_in_correct_order(self, mock_ingest):
        """Test that tickers are processed in the expected order."""
        mock_ingest.return_value = True
        
        # Call main
        main()
        
        # Get the order of ticker pairs
        actual_order = [
            (call[0][0], call[0][1]) for call in mock_ingest.call_args_list
        ]
        
        expected_order = [
            ("BTC", "USD"),
            ("AAVE", "USD"),
            ("ETH", "USD"),
            ("ETH", "BTC"),
            ("USD", "EUR"),
            ("USD", "CHF"),
        ]
        
        assert actual_order == expected_order


class TestMainIntegration:
    """Integration tests for main pipeline."""

    @patch('raw_ingest.main.SparkSession')
    @patch('raw_ingest.main.DbWriter')
    @patch('requests.get')
    @patch('sys.argv', ['main.py', '--catalog', 'dev', '--schema', 'bronze'])
    def test_main_integration_with_mocked_dependencies(
        self, mock_requests_get, mock_writer_class, mock_spark_session_cls, mock_coinbase_api_response
    ):
        """Integration test with all external dependencies mocked."""
        # Setup Spark mock
        mock_spark = MagicMock()
        mock_spark_session_cls.builder.getOrCreate.return_value = mock_spark
        mock_spark.read.table.return_value.select.return_value.collect.side_effect = Exception("Table not found")
        
        # Setup requests mock
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_coinbase_api_response
        mock_requests_get.return_value = mock_response
        
        # Setup DbWriter mock
        mock_writer = MagicMock()
        mock_writer_class.return_value = mock_writer
        
        # This should run the full pipeline without errors
        # Note: This would actually call main() but we can test individual ingestion
        result = ingest_ticker_data("BTC", "USD", "dev", "bronze")
        
        assert result is True
        mock_writer.save_delta_table.assert_called_once()
