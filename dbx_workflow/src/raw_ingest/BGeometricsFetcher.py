from datetime import datetime
import requests
import pandas as pd
from raw_ingest.BaseFetcher import BaseFetcher

class BGeometricsFetcher(BaseFetcher):
    """
    Fetch technical indicators from BGeometrics API
    
    Data Source: https://bitcoin-data.com/api/v1/technical-indicators
    Provides daily BTC technical indicators.
    """

    def __init__(
            self,
            logger,
            ticker: str,
            currency: str,
            catalog: str,
            schema: str,
            base_url: str = "https://bitcoin-data.com/api"
    ):
        super().__init__(logger, ticker, currency, catalog, schema, base_url)
        
        self.table_name = "bgeometrics_btc_technical_indicators"
        self.full_path_table_name = f"{catalog}.{schema}.{self.table_name}"
        self.endpoint = "/v1/technical-indicators"
        
        self.logger.info("-" * 80)
        self.logger.info(f"✓ BGeometricsFetcher initialized for {self.ticker_id}")
        self.logger.info("-" * 80)

    def fetch_historical_data(
            self,
            start_date_time: datetime = None
    ) -> pd.DataFrame:
        """
        Fetch historical technical indicators from BGeometrics

        Args:
            start_date_time: Start date for incremental load. If None, fetches full history.

        Returns:
            pd.DataFrame exactly as returned by API, plus a 'time' column for Delta partitioning.
        """
        params = {}
        msg = "full historical"
        
        if start_date_time:
            # Incremental load: API uses 'startday' and 'endday' format YYYY-MM-DD
            start_str = start_date_time.strftime("%Y-%m-%d")
            end_str = datetime.now().strftime("%Y-%m-%d")
            params['startday'] = start_str
            params['endday'] = end_str
            msg = f"incremental historical from {start_str} to {end_str}"
            
        url = self.base_url + self.endpoint
        
        try:
            self.logger.info(f"📥 Fetching BGeometrics {self.ticker_id} {msg} data from {url}")
            response = requests.get(url, params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                
                if not data: # Handle empty list
                    self.logger.warning("⚠️ API returned empty data.")
                    return pd.DataFrame(columns=["time"]) # Return empty DataFrame with required 'time' column
                    
                df = pd.DataFrame(data)
                
                # We need a 'time' column for the DbWriter partitioning mapping (col("time").cast("date"))
                # BaseFetcher/DbWriter convention: the fetcher must return a 'time' column 
                if 'd' in df.columns:
                    df['time'] = pd.to_datetime(df['d'])
                elif 'unixTs' in df.columns:
                    df['time'] = pd.to_datetime(df['unixTs'], unit='s')
                
                self.logger.info(f"✓ Fetching {len(df)} rows of data succeeded")
                if not df.empty and 'time' in df.columns:
                    self.logger.info(f"  Date range: {df['time'].min()} to {df['time'].max()}")
                
                return df
            else:
                self.logger.error(f"Error: {response.status_code} - {response.text}")
                raise ValueError(f"API Error {response.status_code}: {response.text}")
                
        except requests.exceptions.Timeout:
            self.logger.error("✗ Request timeout - BGeometrics API not responding")
            raise
        except requests.exceptions.RequestException as e:
            self.logger.error(f"✗ API request failed: {e}")
            raise
