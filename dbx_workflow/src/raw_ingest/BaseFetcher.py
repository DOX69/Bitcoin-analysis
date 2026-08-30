from abc import ABC, abstractmethod
from datetime import datetime
import pandas as pd
import requests


def require_2xx(response):
    if not 200 <= response.status_code < 300:
        raise requests.exceptions.HTTPError(
            f"HTTP {response.status_code}: {response.text}",
            response=response,
        )

class BaseFetcher(ABC):
    """
    Abstract Base Class for Crypto/Forex Data Fetchers
    """
    
    def __init__(
            self,
            logger,
            ticker: str,
            currency: str,
            catalog: str | None,
            schema: str,
            base_url: str
    ):
        self.logger = logger
        self.ticker = ticker
        self.currency = currency
        self.catalog = catalog
        self.schema = schema
        self.base_url = base_url
        
        # Common identifiers
        self.ticker_id = f"{ticker.upper()}-{currency.upper()}"
        
        # Naming convention: ticker_currency_suffix (suffix handled by subclass usually, 
        # but Coinbase does ohlcv. Frankfurter might do rates.)
        # Defaulting generic table name here or letting subclass define it.
        # CoinbaseFetcher defines table_name = ticker.lower() + "_" + currency.lower() + "_ohlcv"
        self.full_path_table_name = None 

    def qualify_table_name(self, table_name: str) -> str:
        if self.catalog is None:
            return f"{self.schema}.{table_name}"
        return f"{self.catalog}.{self.schema}.{table_name}"

    @abstractmethod
    def fetch_historical_data(
            self,
            start_date_time: datetime = None
    ) -> pd.DataFrame:
        """
        Fetch historical data from source.
        
        Args:
            start_date_time: The start date for fetching history.
                             If None, implies full history or default range.
                             
        Returns:
            pd.DataFrame with 'time' column and data columns.
        """
        pass
