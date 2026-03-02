"""Tests for BGeometricsFetcher."""

import pytest
from unittest.mock import Mock, patch
from datetime import datetime
import pandas as pd
import requests

from raw_ingest.BGeometricsFetcher import BGeometricsFetcher

class TestBGeometricsFetcher:
    """Tests for the BGeometrics API Data Fetcher."""

    def test_init_attributes(self, mock_logger):
        """Test that init correctly sets up the fetcher."""
        fetcher = BGeometricsFetcher(mock_logger, "BTC", "USD", "dev", "bronze")
        
        assert fetcher.ticker == "BTC"
        assert fetcher.currency == "USD"
        assert fetcher.catalog == "dev"
        assert fetcher.schema == "bronze"
        assert fetcher.table_name == "bgeometrics_btc_technical_indicators"
        assert fetcher.full_path_table_name == "dev.bronze.bgeometrics_btc_technical_indicators"
        assert fetcher.base_url == "https://bitcoin-data.com/api"

    @patch('requests.get')
    def test_fetch_historical_data_full(self, mock_requests_get, mock_logger, mock_bgeometrics_api_response):
        """Test full historical fetch (no start date -> full history)."""
        fetcher = BGeometricsFetcher(mock_logger, "BTC", "USD", "dev", "bronze")
        
        # Setup mock response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_bgeometrics_api_response
        mock_requests_get.return_value = mock_response

        # Execute
        df = fetcher.fetch_historical_data(start_date_time=None)

        # Output columns should match API exactly + time column mapped from "d"
        assert not df.empty
        assert "time" in df.columns
        assert "rsi" in df.columns
        assert "macd" in df.columns
        assert "sma200" in df.columns
        assert "ema50" in df.columns
        
        # We verify we made 1 request to the full endpoint without date limits
        mock_requests_get.assert_called_once()
        args, kwargs = mock_requests_get.call_args
        assert "/v1/technical-indicators" in args[0]
        assert "startday" not in kwargs.get("params", {}) 
        assert "endday" not in kwargs.get("params", {})

    @patch('requests.get')
    def test_fetch_historical_data_incremental(self, mock_requests_get, mock_logger, mock_bgeometrics_api_response):
        """Test incremental fetch passing start_date_time."""
        fetcher = BGeometricsFetcher(mock_logger, "BTC", "USD", "dev", "bronze")
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_bgeometrics_api_response
        mock_requests_get.return_value = mock_response

        start_date = datetime(2026, 2, 24)
        df = fetcher.fetch_historical_data(start_date_time=start_date)

        assert not df.empty
        assert "time" in df.columns

        # Verify request parameters included startday and endday
        mock_requests_get.assert_called_once()
        args, kwargs = mock_requests_get.call_args
        params = kwargs.get("params", {})
        assert "startday" in params
        assert "endday" in params
        assert params["startday"] == "2026-02-24"
        assert params["endday"] == datetime.now().strftime("%Y-%m-%d")

    @patch('requests.get')
    def test_fetch_historical_data_empty_response(self, mock_requests_get, mock_logger):
        """Test fetch with empty response handles properly."""
        fetcher = BGeometricsFetcher(mock_logger, "BTC", "USD", "dev", "bronze")
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = [] # exact empty list
        mock_requests_get.return_value = mock_response

        df = fetcher.fetch_historical_data()

        assert df.empty
        assert "time" in df.columns

    @patch('requests.get')
    def test_fetch_historical_data_request_failure(self, mock_requests_get, mock_logger):
        """Test fetch handles failure."""
        fetcher = BGeometricsFetcher(mock_logger, "BTC", "USD", "dev", "bronze")
        
        # Setup mock to raise RequestException
        mock_requests_get.side_effect = requests.exceptions.RequestException("API completely down")

        with pytest.raises(requests.exceptions.RequestException):
            fetcher.fetch_historical_data()
