"""Tests for FrankfurterFetcher class."""

from unittest.mock import Mock, patch
from datetime import datetime
import pandas as pd
import pytest
import requests
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
        assert all(
            0 < call.kwargs["timeout"] <= 30 for call in mock_get.call_args_list
        )

    @patch('requests.get')
    def test_fetch_historical_data_404(self, mock_get, mock_logger):
        """Test 404 handling."""
        mock_response = Mock()
        mock_response.status_code = 404
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError(
            "404 Client Error"
        )
        mock_get.return_value = mock_response

        fetcher = FrankfurterFetcher(
            logger=mock_logger,
            ticker="USD",
            currency="EUR",
            catalog="dev",
            schema="bronze"
        )

        start_date = datetime.now() - pd.Timedelta(days=2)

        with pytest.raises(requests.exceptions.HTTPError):
            fetcher.fetch_historical_data(start_date_time=start_date)

    @pytest.mark.parametrize(
        "failure",
        [
            requests.exceptions.Timeout("Request timed out"),
            requests.exceptions.ConnectionError("Network unavailable"),
        ],
    )
    @patch('requests.get')
    def test_failure_after_a_successful_page_raises(
        self, mock_get, failure, mock_logger
    ):
        successful_page = Mock(status_code=200)
        successful_page.json.return_value = {
            "rates": {"2025-08-30": {"EUR": 0.90}}
        }
        mock_get.side_effect = [successful_page, failure]
        fetcher = FrankfurterFetcher(
            logger=mock_logger,
            ticker="USD",
            currency="EUR",
            catalog="dev",
            schema="bronze",
        )

        with pytest.raises(type(failure)):
            fetcher.fetch_historical_data(
                start_date_time=datetime.now() - pd.Timedelta(days=400)
            )

        assert mock_get.call_count == 2

    @patch('requests.get')
    def test_non_2xx_after_a_successful_page_raises(self, mock_get, mock_logger):
        successful_page = Mock(status_code=200)
        successful_page.json.return_value = {
            "rates": {"2025-08-30": {"EUR": 0.90}}
        }
        failed_page = Mock(status_code=503, text="Service unavailable")
        failed_page.raise_for_status.side_effect = requests.exceptions.HTTPError(
            "503 Server Error"
        )
        mock_get.side_effect = [successful_page, failed_page]
        fetcher = FrankfurterFetcher(
            logger=mock_logger,
            ticker="USD",
            currency="EUR",
            catalog="dev",
            schema="bronze",
        )

        with pytest.raises(requests.exceptions.HTTPError):
            fetcher.fetch_historical_data(
                start_date_time=datetime.now() - pd.Timedelta(days=400)
            )

        assert mock_get.call_count == 2

    @patch('requests.get')
    def test_redirect_response_raises(self, mock_get, mock_logger):
        response = Mock(status_code=302, text="Redirect")
        response.json.return_value = {
            "rates": {"2026-08-29": {"EUR": 0.90}}
        }
        mock_get.return_value = response
        fetcher = FrankfurterFetcher(
            logger=mock_logger,
            ticker="USD",
            currency="EUR",
            catalog="dev",
            schema="bronze",
        )

        with pytest.raises(requests.exceptions.HTTPError):
            fetcher.fetch_historical_data(
                start_date_time=datetime.now() - pd.Timedelta(days=2)
            )

    @patch('requests.get')
    def test_invalid_payload_after_a_successful_page_raises(
        self, mock_get, mock_logger
    ):
        successful_page = Mock(status_code=200)
        successful_page.json.return_value = {
            "rates": {"2025-08-30": {"EUR": 0.90}}
        }
        invalid_page = Mock(status_code=200)
        invalid_page.json.return_value = {"base": "USD"}
        mock_get.side_effect = [successful_page, invalid_page]
        fetcher = FrankfurterFetcher(
            logger=mock_logger,
            ticker="USD",
            currency="EUR",
            catalog="dev",
            schema="bronze",
        )

        with pytest.raises(ValueError):
            fetcher.fetch_historical_data(
                start_date_time=datetime.now() - pd.Timedelta(days=400)
            )

        assert mock_get.call_count == 2

    @patch('requests.get')
    def test_invalid_element_after_a_valid_element_raises(
        self, mock_get, mock_logger
    ):
        response = Mock(status_code=200)
        response.json.return_value = {
            "rates": {
                "2026-08-28": {"EUR": 0.90},
                "2026-08-29": {},
            }
        }
        mock_get.return_value = response
        fetcher = FrankfurterFetcher(
            logger=mock_logger,
            ticker="USD",
            currency="EUR",
            catalog="dev",
            schema="bronze",
        )

        with pytest.raises(ValueError):
            fetcher.fetch_historical_data(
                start_date_time=datetime.now() - pd.Timedelta(days=2)
            )

