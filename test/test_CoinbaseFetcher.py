"""
Bitcoin Data Fetcher from Coinbase API (Free tier)
- Historique complet disponible
- Pas de limite de rate (gratuit)
- JSON response structuré
"""

import os
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional
import requests
import pandas as pd
from dotenv import load_dotenv

# Charger variables d'environnement
load_dotenv()

# Configuration logging
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class CoinbaseFetcher:
    """
    Fetch Bitcoin data from Coinbase API

    Features:
    - Historical data (years back)
    - Real-time price
    - Volume & market cap
    - No rate limits on free tier
    """

    def __init__(
            self,
            ticker_id: str,
            data_dir: str = "data",
            base_url: str = os.getenv("BASE_COINBASE_API_URL")
    ):
        """
        Initialize fetcher

        Args:
            ticker_id: Coinbase crypto ID (default: BTC-USD)
            data_dir: Directory to store data
            base_url: base api url
        """
        self.ticker_id = ticker_id
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(exist_ok=True)
        self.base_url = base_url
        self.price_endpoint = f"/products/{self.ticker_id}/candles"


        logger.info(f"✓ CoinbaseFetcher initialized for {ticker_id.upper()}")

    def fetch_historical_data(
            self,
            ticker_id: str,
            days: int = 365,
            granularity: int = 86400 # daily
    ) -> pd.DataFrame:
        """
        Fetch historical OHLCV data from Coinbase

        Args:
            ticker_id : coin ticker with currency. E.g. BTC-USD
            days: Number of days to fetch (1, 7, 30, 365, max)
            granularity:

        Returns:
            DataFrame with columns: timestamp, open, high, low, close, volume

        Raises:
            requests.RequestException: If API request fails
            ValueError: If response is invalid
        """
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        delta = timedelta(days=200)
        all_data = []
        current_start = start_date
        try:
            logger.info(f"📥 Fetching {ticker_id} historical data ({days} days)")

            while current_start < end_date:
                current_end = min(current_start + delta, end_date)
                params = {
                    "start": current_start.isoformat(),
                    "end": current_end.isoformat(),
                    "granularity": granularity
                }

                response = requests.get(self.base_url + self.price_endpoint, params=params)

                if response.status_code == 200:
                    data = response.json()
                    # Ensure all values are cast to the correct type
                    for row in data:
                        # Coinbase returns: [ time, low, high, open, close, volume ]
                        all_data.append([
                            int(row[0]),         # time (unix timestamp)
                            float(row[1]),       # low
                            float(row[2]),       # high
                            float(row[3]),       # open
                            float(row[4]),       # close
                            float(row[5])        # volume
                        ])
                else:
                    print(f"Error: {response.status_code} - {response.text}")
                    break

                current_start = current_end

            columns = ["time", "low", "high", "open", "close", "volume"]
            df = pd.DataFrame(all_data, columns=columns)
            df["time"] = pd.to_datetime(df["time"], unit="s")
            # df["month_name_year"] = df["time"].dt.strftime("%Y-%B")
            # df["last_close_month_name_year"] = df.groupby("month_name_year")["close"].transform("first")
            # df_agg = df.groupby("month_name_year", as_index=False).agg({"last_close_month_name_year": "max"})
            # df_agg = df_agg.rename(columns={"last_close_month_name_year": "close"})

            # Vérifier données nulles
            if df[['open', 'high', 'low', 'close']].isnull().any().any():
                logger.warning("⚠️  Found null values in OHLC data")

            logger.info(f"✓ Fetched {len(df)} rows of historical data")
            logger.info(f"  Date range: {df['time'].min()} to {df['time'].max()}")
            logger.info(f"  Price range: ${df['close'].min():.2f} - ${df['close'].max():.2f}")

            return df

        except requests.exceptions.Timeout:
            logger.error("✗ Request timeout - Coinbase API not responding")
            raise
        except requests.exceptions.RequestException as e:
            logger.error(f"✗ API request failed: {e}")
            raise
        except ValueError as e:
            logger.error(f"✗ Invalid response data: {e}")
            raise

    def save_to_csv(
            self,
            df: pd.DataFrame,
            filename: Optional[str] = None,
            append: bool = False
    ) -> Path:
        """
        Save DataFrame to CSV

        Args:
            df: DataFrame to save
            filename: Custom filename (default: bitcoin_YYYYMMDD_HHMMSS.csv)
            append: If True, append to existing file instead of overwriting

        Returns:
            Path to saved file
        """
        try:
            if filename is None:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"bitcoin_{timestamp}.csv"

            filepath = self.data_dir / filename

            if append and filepath.exists():
                # Lire le fichier existant
                existing_df = pd.read_csv(filepath)
                # Concaténer et supprimer les doublons basés sur timestamp
                combined_df = pd.concat(
                    [existing_df, df],
                    ignore_index=True
                )
                combined_df = combined_df.drop_duplicates(
                    subset=['time'],
                    keep='last'
                )
                combined_df.to_csv(filepath, index=False)
                logger.info(f"✓ Appended to {filepath} ({len(combined_df)} rows total)")
            else:
                df.to_csv(filepath, index=False)
                logger.info(f"✓ Saved to {filepath} ({len(df)} rows)")

            return filepath

        except Exception as e:
            logger.error(f"✗ Failed to save CSV: {e}")
            raise

def main():
    """
    Démonstration d'utilisation
    """
    # Parameters
    ticker_id = "BTC-EUR"
    fetcher = CoinbaseFetcher(ticker_id)
    days = 100 #365 * 13
    # Fetch historique (1 jour)
    historical = fetcher.fetch_historical_data(ticker_id,days= days)
    logger.info(f"\n📊 Historique (dernier {days} jour):")
    logger.info(historical.sort_values(by="time",ascending=False).tail(10))

    # Sauvegarder
    fetcher.save_to_csv(historical, filename=f"bitcoin_full_{days}_day.csv",append=True)

if __name__ == "__main__":
    main()