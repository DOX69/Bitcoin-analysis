"""Tests for CoinbaseFetcher class."""

import pytest
from unittest.mock import Mock, patch
from datetime import datetime
import pandas as pd
import requests

from raw_ingest.CoinbaseFetcher import CoinbaseFetcher


class TestCoinbaseFetcherInit:
    """Test CoinbaseFetcher initialization."""

    def test_init_sets_attributes_correctly(self, mock_logger):
        """Test that initialization sets all attributes correctly."""
        fetcher = CoinbaseFetcher(
            logger=mock_logger,
            ticker="BTC",
            currency="USD",
            catalog="dev",
            schema="bronze"
        )

        assert fetcher.ticker == "BTC"
        assert fetcher.currency == "USD"
        assert fetcher.ticker_id == "BTC-USD"
        assert fetcher.base_url == "https://api.exchange.coinbase.com"
        assert fetcher.price_endpoint == "/products/BTC-USD/candles"

    def test_init_sets_table_name(self, mock_logger):
        """Test that table name is constructed correctly."""
        fetcher = CoinbaseFetcher(
            logger=mock_logger,
            ticker="ETH",
            currency="EUR",
            catalog="prod",
            schema="raw"
        )

        assert fetcher.table_name == "eth_eur_ohlcv"
        assert fetcher.full_path_table_name == "prod.raw.eth_eur_ohlcv"

    def test_init_with_custom_base_url(self, mock_logger):
        """Test initialization with custom base URL."""
        custom_url = "https://custom-api.example.com"
        fetcher = CoinbaseFetcher(
            logger=mock_logger,
            ticker="BTC",
            currency="USD",
            catalog="dev",
            schema="bronze",
            base_url=custom_url
        )

        assert fetcher.base_url == custom_url


class TestCoinbaseFetcherFetchHistoricalData:
    """Test CoinbaseFetcher.fetch_historical_data method."""

    @patch('requests.get')
    def test_fetch_historical_data_success(self, mock_get, mock_logger, mock_coinbase_api_response):
        """Test successful historical data fetch."""
        # Setup mock response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_coinbase_api_response
        mock_get.return_value = mock_response

        fetcher = CoinbaseFetcher(
            logger=mock_logger,
            ticker="BTC",
            currency="USD",
            catalog="dev",
            schema="bronze"
        )

        # Fetch data for a short period to avoid pagination
        df = fetcher.fetch_historical_data(days=5)

        # Verify DataFrame structure
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 5
        assert list(df.columns) == ["time", "low", "high", "open", "close", "volume"]
        
        # Verify data types
        assert df["time"].dtype == "datetime64[ns]"
        assert df["low"].dtype == float
        assert df["high"].dtype == float
        assert df["open"].dtype == float
        assert df["close"].dtype == float
        assert df["volume"].dtype == float

    @patch('requests.get')
    def test_fetch_historical_data_with_start_date(self, mock_get, mock_logger, mock_coinbase_api_response):
        """Test fetch with custom start date."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_coinbase_api_response
        mock_get.return_value = mock_response

        fetcher = CoinbaseFetcher(
            logger=mock_logger,
            ticker="BTC",
            currency="USD",
            catalog="dev",
            schema="bronze"
        )

        start_date = datetime(2022, 1, 1)
        fetcher.fetch_historical_data(start_date_time=start_date)

        # Verify API was called with a start date (the exact format might vary slightly)
        assert mock_get.called
        call_args = mock_get.call_args
        assert 'start' in call_args[1]['params']

    @patch('requests.get')
    def test_fetch_historical_data_handles_pagination(self, mock_get, mock_logger):
        """Test that pagination works correctly for large date ranges."""
        # Create mock response that simulates multiple API calls
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = [
            [1640995200, 46000.0, 47500.0, 46500.0, 47000.0, 1500.5]
        ]
        mock_get.return_value = mock_response

        fetcher = CoinbaseFetcher(
            logger=mock_logger,
            ticker="BTC",
            currency="USD",
            catalog="dev",
            schema="bronze"
        )

        # Fetch 400 days (should trigger pagination - 2 calls with 200-day chunks)
        fetcher.fetch_historical_data(days=400)

        # Verify multiple API calls were made (at least 2 for 400 days)
        assert mock_get.call_count >= 2
        assert all(
            0 < call.kwargs["timeout"] <= 30 for call in mock_get.call_args_list
        )

    @patch('requests.get')
    def test_fetch_historical_data_type_casting(self, mock_get, mock_logger):
        """Test that all values are correctly cast to proper types."""
        # Response with string values to test casting
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = [
            ["1640995200", "46000", "47500", "46500", "47000", "1500.5"]
        ]
        mock_get.return_value = mock_response

        fetcher = CoinbaseFetcher(
            logger=mock_logger,
            ticker="BTC",
            currency="USD",
            catalog="dev",
            schema="bronze"
        )

        df = fetcher.fetch_historical_data(days=1)

        # Verify types after casting
        assert isinstance(df.iloc[0]["time"], pd.Timestamp)
        assert isinstance(df.iloc[0]["low"], float)
        assert isinstance(df.iloc[0]["high"], float)
        assert isinstance(df.iloc[0]["open"], float)
        assert isinstance(df.iloc[0]["close"], float)
        assert isinstance(df.iloc[0]["volume"], float)

    @patch('requests.get')
    def test_fetch_historical_data_timeout(self, mock_get, mock_logger):
        """Test timeout handling."""
        mock_get.side_effect = requests.exceptions.Timeout("Request timed out")

        fetcher = CoinbaseFetcher(
            logger=mock_logger,
            ticker="BTC",
            currency="USD",
            catalog="dev",
            schema="bronze"
        )

        with pytest.raises(requests.exceptions.Timeout):
            fetcher.fetch_historical_data(days=1)

    @patch('requests.get')
    def test_fetch_historical_data_api_error(self, mock_get, mock_logger):
        """Test API error response handling."""
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError(
            "500 Server Error"
        )
        mock_get.return_value = mock_response

        fetcher = CoinbaseFetcher(
            logger=mock_logger,
            ticker="BTC",
            currency="USD",
            catalog="dev",
            schema="bronze"
        )

        with pytest.raises(requests.exceptions.HTTPError):
            fetcher.fetch_historical_data(days=1)

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
        successful_page.json.return_value = [
            [1640995200, 46000.0, 47500.0, 46500.0, 47000.0, 1500.5]
        ]
        mock_get.side_effect = [successful_page, failure]
        fetcher = CoinbaseFetcher(
            logger=mock_logger,
            ticker="BTC",
            currency="USD",
            catalog="dev",
            schema="bronze",
        )

        with pytest.raises(type(failure)):
            fetcher.fetch_historical_data(days=400)

        assert mock_get.call_count == 2

    @patch('requests.get')
    def test_non_2xx_after_a_successful_page_raises(self, mock_get, mock_logger):
        successful_page = Mock(status_code=200)
        successful_page.json.return_value = [
            [1640995200, 46000.0, 47500.0, 46500.0, 47000.0, 1500.5]
        ]
        failed_page = Mock(status_code=503, text="Service unavailable")
        failed_page.raise_for_status.side_effect = requests.exceptions.HTTPError(
            "503 Server Error"
        )
        mock_get.side_effect = [successful_page, failed_page]
        fetcher = CoinbaseFetcher(
            logger=mock_logger,
            ticker="BTC",
            currency="USD",
            catalog="dev",
            schema="bronze",
        )

        with pytest.raises(requests.exceptions.HTTPError):
            fetcher.fetch_historical_data(days=400)

        assert mock_get.call_count == 2

    @patch('requests.get')
    def test_redirect_response_raises(self, mock_get, mock_logger):
        response = Mock(status_code=302, text="Redirect")
        response.json.return_value = [
            [1640995200, 46000.0, 47500.0, 46500.0, 47000.0, 1500.5]
        ]
        mock_get.return_value = response
        fetcher = CoinbaseFetcher(
            logger=mock_logger,
            ticker="BTC",
            currency="USD",
            catalog="dev",
            schema="bronze",
        )

        with pytest.raises(requests.exceptions.HTTPError):
            fetcher.fetch_historical_data(days=1)

    @patch('requests.get')
    def test_invalid_payload_after_a_successful_page_raises(
        self, mock_get, mock_logger
    ):
        successful_page = Mock(status_code=200)
        successful_page.json.return_value = [
            [1640995200, 46000.0, 47500.0, 46500.0, 47000.0, 1500.5]
        ]
        invalid_page = Mock(status_code=200)
        invalid_page.json.return_value = [
            [1641081600, 47000.0, 48000.0, 47000.0, 47800.0]
        ]
        mock_get.side_effect = [successful_page, invalid_page]
        fetcher = CoinbaseFetcher(
            logger=mock_logger,
            ticker="BTC",
            currency="USD",
            catalog="dev",
            schema="bronze",
        )

        with pytest.raises(ValueError):
            fetcher.fetch_historical_data(days=400)

        assert mock_get.call_count == 2

    @patch('requests.get')
    def test_fetch_historical_data_request_exception(self, mock_get, mock_logger):
        """Test general request exception handling."""
        mock_get.side_effect = requests.exceptions.RequestException("Network error")

        fetcher = CoinbaseFetcher(
            logger=mock_logger,
            ticker="BTC",
            currency="USD",
            catalog="dev",
            schema="bronze"
        )

        with pytest.raises(requests.exceptions.RequestException):
            fetcher.fetch_historical_data(days=1)

    @patch('requests.get')
    def test_fetch_historical_data_validates_price_range(self, mock_get, mock_logger, mock_coinbase_api_response):
        """Test that valid price ranges are returned."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_coinbase_api_response
        mock_get.return_value = mock_response

        fetcher = CoinbaseFetcher(
            logger=mock_logger,
            ticker="BTC",
            currency="USD",
            catalog="dev",
            schema="bronze"
        )

        df = fetcher.fetch_historical_data(days=5)

        # Verify OHLC relationships (high >= open/close, low <= open/close)
        assert (df['high'] >= df['open']).all()
        assert (df['high'] >= df['close']).all()
        assert (df['low'] <= df['open']).all()
        assert (df['low'] <= df['close']).all()

    @patch('requests.get')
    def test_fetch_historical_data_null_value_warning(self, mock_get, mock_logger):
        """Test that null values invalidate the payload."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = [
            [1640995200, None, 47500.0, 46500.0, 47000.0, 1500.5]
        ]
        mock_get.return_value = mock_response

        fetcher = CoinbaseFetcher(
            logger=mock_logger,
            ticker="BTC",
            currency="USD",
            catalog="dev",
            schema="bronze"
        )

        with pytest.raises(ValueError):
            fetcher.fetch_historical_data(days=1)
