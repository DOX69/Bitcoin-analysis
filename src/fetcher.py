"""
Bitcoin Data Fetcher from CoinGecko API (Free tier)
- Historique complet disponible
- Pas de limite de rate (gratuit)
- JSON response structuré
"""

import os
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional
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


class CoinGeckoFetcher:
    """
    Fetch Bitcoin data from CoinGecko API (Free tier - no API key required)

    Features:
    - Historical data (years back)
    - Real-time price
    - Volume & market cap
    - No rate limits on free tier
    """

    # CoinGecko API endpoints
    BASE_URL = "https://api.coingecko.com/api/v3"
    PRICE_ENDPOINT = f"{BASE_URL}/simple/price"
    MARKET_DATA_ENDPOINT = f"{BASE_URL}/coins/bitcoin/market_chart"

    def __init__(
            self,
            crypto_id: str = "bitcoin",
            currency: str = "usd",
            data_dir: str = "data"
    ):
        """
        Initialize fetcher

        Args:
            crypto_id: CoinGecko crypto ID (default: bitcoin)
            currency: Currency (default: usd)
            data_dir: Directory to store data
        """
        self.crypto_id = crypto_id
        self.currency = currency.lower()
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(exist_ok=True)

        logger.info(f"✓ CoinGeckoFetcher initialized for {crypto_id.upper()}/{currency.upper()}")

    def fetch_historical_data(
            self,
            days: int = 365,
            vs_currency: str = "usd"
    ) -> pd.DataFrame:
        """
        Fetch historical OHLCV data from CoinGecko

        Args:
            days: Number of days to fetch (1, 7, 30, 365, max)
            vs_currency: Currency (usd, eur, gbp, jpy, etc.)

        Returns:
            DataFrame with columns: timestamp, open, high, low, close, volume

        Raises:
            requests.RequestException: If API request fails
            ValueError: If response is invalid
        """
        try:
            logger.info(f"📥 Fetching {self.crypto_id} historical data ({days} days)")

            # Parameters pour l'API
            params = {
                "vs_currency": vs_currency,
                "days": days,
                "interval": "daily"
            }

            # Endpoint spécifique pour données OHLC
            url = f"{self.BASE_URL}/coins/{self.crypto_id}/ohlc"

            # Requête
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()  # Raise exception si erreur HTTP

            data = response.json()

            # Validation réponse
            if not isinstance(data, list) or len(data) == 0:
                raise ValueError(f"Invalid response from CoinGecko: {data}")

            # Transformer en DataFrame
            # Format: [timestamp, open, high, low, close]
            df = pd.DataFrame(
                data,
                columns=['timestamp', 'open', 'high', 'low', 'close']
            )

            # Convertir timestamp (ms) en datetime
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            df['date'] = df['timestamp'].dt.date

            # Ajouter colonnes supplémentaires
            df['crypto'] = self.crypto_id.upper()
            df['currency'] = vs_currency.upper()

            # Vérifier données nulles
            if df[['open', 'high', 'low', 'close']].isnull().any().any():
                logger.warning("⚠️  Found null values in OHLC data")

            logger.info(f"✓ Fetched {len(df)} rows of historical data")
            logger.info(f"  Date range: {df['date'].min()} to {df['date'].max()}")
            logger.info(f"  Price range: ${df['close'].min():.2f} - ${df['close'].max():.2f}")

            return df

        except requests.exceptions.Timeout:
            logger.error("✗ Request timeout - CoinGecko API not responding")
            raise
        except requests.exceptions.RequestException as e:
            logger.error(f"✗ API request failed: {e}")
            raise
        except ValueError as e:
            logger.error(f"✗ Invalid response data: {e}")
            raise

    def fetch_latest_price(self) -> Dict[str, float]:
        """
        Fetch current Bitcoin price (real-time)

        Returns:
            Dict with keys: price, market_cap, volume_24h, change_24h
        """
        try:
            logger.info(f"💰 Fetching latest {self.crypto_id} price")

            params = {
                "ids": self.crypto_id,
                "vs_currencies": self.currency,
                "include_market_cap": "true",
                "include_24hr_vol": "true",
                "include_24hr_change": "true"
            }

            response = requests.get(self.PRICE_ENDPOINT, params=params, timeout=5)
            response.raise_for_status()

            data = response.json()

            if self.crypto_id not in data:
                raise ValueError(f"Crypto {self.crypto_id} not found in response")

            crypto_data = data[self.crypto_id]

            result = {
                'timestamp': datetime.now().isoformat(),
                'crypto': self.crypto_id.upper(),
                'currency': self.currency.upper(),
                'price': crypto_data.get(self.currency),
                'market_cap': crypto_data.get(f"{self.currency}_market_cap"),
                'volume_24h': crypto_data.get(f"{self.currency}_24h_vol"),
                'change_24h': crypto_data.get(f"{self.currency}_24h_change")
            }

            logger.info(f"✓ Current price: ${result['price']:.2f}")
            return result

        except Exception as e:
            logger.error(f"✗ Failed to fetch latest price: {e}")
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
                    subset=['timestamp'],
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
    fetcher = CoinGeckoFetcher()

    # Fetch historique (1 an)
    historical = fetcher.fetch_historical_data(days=1)
    logger.info("\n📊 Historique (dernier jour):")
    logger.info(historical.tail(10))

    # Sauvegarder
    fetcher.save_to_csv(historical, filename="bitcoin_full_day.csv")

    # Fetch prix actuel
    latest = fetcher.fetch_latest_price()
    logger.info(f"\n💰 Prix actuel: ${latest['price']:.2f}")

    # Sauvegarder prix actuel
    latest_df = pd.DataFrame([latest])
    fetcher.save_to_csv(latest_df, filename="bitcoin_latest.csv", append=True)


if __name__ == "__main__":
    main()