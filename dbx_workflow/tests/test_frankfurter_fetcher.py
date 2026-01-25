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
        # Setup mock response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "amount": 1.0,
            "base": "USD",
            "rates": {
                "2020-01-02": {"EUR": 0.90},
                "2020-01-03": {"EUR": 0.91}
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

        # Mock datetime logic inside the method is tricky without patching datetime.
        # But we can pass a start_date close to now to limit loops?
        # Or patch datetime.
        
        # Here we choose to patch the datetime used in the module or rely on 'now'
        # To avoid infinite loops or large ranges if defaults are used, provide start_date.
        # But if we want deterministic loop count (1 pass), ensure start_date is < now < start_date + 365.
        
        # Let's patch datetime in the fetcher module to have a fixed 'now'
        with patch('raw_ingest.FrankfurterFetcher.datetime') as mock_dt:
            mock_dt.now.return_value = datetime(2020, 1, 5)
            mock_dt.strptime = datetime.strptime # keep strptime working
            
            # Since we pass start_date_time, that type matters.
            # If we pass a real datetime object, and the code compares it with mock_dt.now().
            
            # Code: end_date = datetime.now()
            # If mock_dt is a MagicMock, it might fail comparison with real datetime.
            # Solution: make mock_dt inherit from datetime or use side_effect.
            # Easier: Just rely on short range start_date.
            pass
        
        # Simpler approach: Set start_date such that it only runs one loop iteration
        # End date is "now".
        # If we set start_date to "now - 2 days", it will run 1 loop.
        
        start_date = datetime.now() - pd.Timedelta(days=5)
        
        # IMPORTANT: Fix the mock response dates to match our dynamic start date?
        # actually the code doesn't check if returned dates match request range strictly.
        # It just parses what is returned.
        
        # Need to re-setup mock response to be generic or just ignore dates logic for this test?
        # The fetcher parses the keys in "rates".
        
        df = fetcher.fetch_historical_data(start_date_time=start_date)

        assert not df.empty
        assert len(df) == 2
        assert list(df.columns) == ["time", "rate"]
        
        # Verify values
        # 2020-01-02
        ts1 = datetime(2020, 1, 2).timestamp()
        assert df.iloc[0]["time"].timestamp() == ts1
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

