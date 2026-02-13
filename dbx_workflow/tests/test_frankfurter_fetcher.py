"""Tests for FrankfurterFetcher class."""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
import pandas as pd
from raw_ingest.FrankfurterFetcher import FrankfurterFetcher

class TestFrankfurterFetcherInit:
    """Test FrankfurterFetcher initialization."""

    def test_init_sets_attributes_correctly(self, mock_logger):
        fetcher = FrankfurterFetcher(
            logger=mock_logger,
            ticker="USD",
            currency="EUR",
            catalog="dev",
            schema="bronze"
        )

        assert fetcher.ticker == "USD"
        assert fetcher.currency == "EUR"
        assert fetcher.ticker_id == "USD-EUR"
        assert fetcher.table_name == "usd_eur_rates"
        assert fetcher.base_url == "https://api.frankfurter.dev/v1"

class TestFrankfurterFetcherFetchHistoricalData:
    """Test FrankfurterFetcher.fetch_historical_data method."""

    @patch('requests.get')
    def test_fetch_historical_data_success(self, mock_get, mock_logger):
        """Test successful historical data fetch."""
        # Setup mock response with dynamic dates relative to now
        # This ensures request range and response data overlap semantically.
        start_date = datetime.now() - pd.Timedelta(days=5)

        # Generate dates within the requested range
        date1 = (start_date + pd.Timedelta(days=1)).strftime("%Y-%m-%d")
        date2 = (start_date + pd.Timedelta(days=2)).strftime("%Y-%m-%d")

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "amount": 1.0,
            "base": "USD",
            "rates": {
                date1: {"EUR": 0.90},
                date2: {"EUR": 0.91}
            }
        }
        mock_get.return_value = mock_response

        fetcher = FrankfurterFetcher(
            logger=mock_logger,
            ticker="USD",
            currency="EUR",
            catalog="dev",
            schema="bronze"
        )

        df = fetcher.fetch_historical_data(start_date_time=start_date)

        assert not df.empty
        assert len(df) == 2
        assert list(df.columns) == ["time", "rate"]
        
        # Verify values — compare date strings to avoid timezone offset issues
        # Note: fetcher produces rows in order of rates keys (insertion order in Python 3.7+)
        assert df.iloc[0]["time"].strftime("%Y-%m-%d") == date1
        assert df.iloc[0]["rate"] == 0.90

    @patch('requests.get')
    def test_fetch_historical_data_404(self, mock_get, mock_logger):
        """Test 404 handling."""
        mock_response = Mock()
        mock_response.status_code = 404
        mock_get.return_value = mock_response

        fetcher = FrankfurterFetcher(
            logger=mock_logger,
            ticker="USD",
            currency="EUR",
            catalog="dev",
            schema="bronze"
        )

        # Short range
        start_date = datetime.now() - pd.Timedelta(days=2)
        df = fetcher.fetch_historical_data(start_date_time=start_date)

        assert df.empty

