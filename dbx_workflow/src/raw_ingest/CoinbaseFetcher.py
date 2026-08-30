from datetime import datetime, timedelta
import requests
import pandas as pd
from raw_ingest.BaseFetcher import BaseFetcher, require_2xx
from raw_ingest.api_models.coinbase import CoinbaseCandleResponse

class CoinbaseFetcher(BaseFetcher):
    """
    Fetch crypto data from Coinbase API

    Features:
    - Historical data (years back)
    - Real-time price
    - Volume & market cap
    - No rate limits on free tier
    """

    def __init__(
            self,
            logger,
            ticker: str,
            currency: str,
            catalog: str,
            schema: str,
            base_url: str = "https://api.exchange.coinbase.com"
    ):
        """
        Initialize fetcher

        Args:
            ticker: Coinbase crypto (e.g. BTC)
            currency: Coinbase currency (e.g. USD)
            base_url: base api url
        """
        super().__init__(logger, ticker, currency, catalog, schema, base_url)
        
        self.table_name = ticker.lower() + "_" + currency.lower() + "_ohlcv"
        self.full_path_table_name = self.qualify_table_name(self.table_name)
        self.price_endpoint = f"/products/{self.ticker_id}/candles"

        logger.info("-" * 80)
        logger.info(f"✓ CoinbaseFetcher initialized for {self.ticker_id}")
        logger.info("-" * 80)

    def fetch_historical_data(
            self,
            days: int = 365*13,
            granularity: int = 86400, # daily
            start_date_time: datetime = None
    ) -> pd.DataFrame:
        """
        Fetch historical OHLCV data from Coinbase

        Args:
            days: Number of days to fetch (1, 7, 30, 365, max)
            granularity: Here, by default 86400 (daily)
            start_date_time: date_time when history fetch begins

        Returns:
            Pandas DataFrame with columns: timestamp, open, high, low, close, volume

        Raises:
            requests.RequestException: If API request fails
            ValueError: If response is invalid
        """
        end_date = datetime.now()
        if start_date_time is None:
            start_date_time = end_date - timedelta(days=days)
        delta = timedelta(days=200)
        all_data = []
        current_start = start_date_time
        try:
            self.logger.info(f"📥 Trying to fetch {self.ticker_id} historical data from {current_start}")

            while current_start < end_date:
                current_end = min(current_start + delta, end_date)
                params = {
                    "start": current_start.isoformat(),
                    "end": current_end.isoformat(),
                    "granularity": granularity
                }

                response = requests.get(
                    self.base_url + self.price_endpoint,
                    params=params,
                    timeout=10,
                )
                require_2xx(response)
                data = response.json()
                CoinbaseCandleResponse.model_validate(data)
                if any(len(candle) != 6 for candle in data):
                    raise ValueError("Invalid Coinbase candle width")
                all_data.extend(data)

                current_start = current_end

            columns = ["time", "low", "high", "open", "close", "volume"]
            df = pd.DataFrame(all_data, columns=columns)

            # Convert numeric columns safely
            numeric_cols = ["low", "high", "open", "close", "volume"]
            for col in numeric_cols:
                # errors='coerce' turns None/invalid into NaN
                df[col] = pd.to_numeric(df[col], errors='coerce').astype('float64')

            # Convert time column
            df["time"] = pd.to_numeric(df["time"], errors='coerce')
            df["time"] = pd.to_datetime(df["time"], unit="s")

            # Vérifier données nulles
            if df[['open', 'high', 'low', 'close']].isnull().any().any():
                self.logger.warning("⚠️  Found null values in OHLC data")

            self.logger.info(f"✓ Fetching {len(df)} rows of historical data succeeded")
            self.logger.info(f"  Date range: {df['time'].min()} to {df['time'].max()}")
            self.logger.info(f"  Price range: ${df['close'].min():.2f} - ${df['close'].max():.2f}")

            return df

        except requests.exceptions.Timeout:
            self.logger.error("✗ Request timeout - Coinbase API not responding")
            raise
        except requests.exceptions.RequestException as e:
            self.logger.error(f"✗ API request failed: {e}")
            raise
        except ValueError as e:
            self.logger.error(f"✗ Invalid response data: {e}")
            raise
