from datetime import datetime, timedelta
import requests
import pandas as pd
from raw_ingest.BaseFetcher import BaseFetcher, require_2xx

class FrankfurterFetcher(BaseFetcher):
    """
    Fetch forex data from Frankfurter API (ECB data)
    
    Features:
    - Daily reference rates
    - No authentication required
    - Bulk fetching support
    """

    def __init__(
            self,
            logger,
            ticker: str,
            currency: str,
            catalog: str,
            schema: str,
            base_url: str = "https://api.frankfurter.dev/v1"
    ):
        super().__init__(logger, ticker, currency, catalog, schema, base_url)
        
        # Ticker is Base (USD), Currency is Quote (EUR) -> usd_eur_rates
        self.table_name = f"{ticker.lower()}_{currency.lower()}_rates"
        self.full_path_table_name = self.qualify_table_name(self.table_name)
        
        self.logger.info("-" * 80)
        self.logger.info(f"✓ FrankfurterFetcher initialized for {self.ticker_id}")
        self.logger.info("-" * 80)

    def fetch_historical_data(
            self,
            start_date_time: datetime = None
    ) -> pd.DataFrame:
        """
        Fetch historical rates from Frankfurter

        Args:
            start_date_time: Start date. Defaults to 2010-01-01 if None.

        Returns:
            pd.DataFrame with columns: time, rate
        """
        end_date = datetime.now()
        # Default start date 1999-01-04 (Frankfurter max) but user mentioned 2010
        if start_date_time is None:
            start_date_time = datetime(2010, 1, 1)
        
        # Ensure we don't fetch future
        if start_date_time > end_date:
            self.logger.info("Start date is in the future, nothing to fetch.")
            return pd.DataFrame(columns=["time", "rate"])

        # Loop in batches of 365 days
        delta = timedelta(days=365)
        current_start = start_date_time
        all_data = []

        try:
            self.logger.info(f"📥 Trying to fetch {self.ticker_id} historical data from {current_start.date()}")

            while current_start < end_date:
                # Frankfurter range is inclusive? The example is 2010-01-01..2024-12-31
                # Let's use current_start .. current_end
                current_end = min(current_start + delta, end_date)
                
                # Format: YYYY-MM-DD
                s_str = current_start.strftime("%Y-%m-%d")
                e_str = current_end.strftime("%Y-%m-%d")
                
                # If start == end, endpoint handled differently or just single day?
                # Range endpoint is /start..end
                # If s_str == e_str, maybe /date, but let's ensure we move forward.
                if s_str == e_str:
                    current_start += timedelta(days=1)
                    continue

                endpoint = f"/{s_str}..{e_str}"
                params = {
                    "base": self.ticker.upper(),
                    "symbols": self.currency.upper()
                }

                url = self.base_url + endpoint
                self.logger.debug(f"Requesting {url}")
                
                response = requests.get(url, params=params, timeout=10)
                require_2xx(response)
                data = response.json()
                if not isinstance(data, dict) or not isinstance(
                    data.get("rates"), dict
                ):
                    raise ValueError("Invalid Frankfurter payload: missing rates")

                for date_str, rate_dict in data["rates"].items():
                    if not isinstance(rate_dict, dict) or self.currency.upper() not in rate_dict:
                        raise ValueError(
                            f"Invalid Frankfurter rate for {date_str}"
                        )
                    all_data.append(
                        [date_str, float(rate_dict[self.currency.upper()])]
                    )
                
                # Next batch
                current_start = current_end + timedelta(days=1)
                # Polite sleep?
                # time.sleep(0.2) 

            columns = ["time", "rate"]
            df = pd.DataFrame(all_data, columns=columns)
            if not df.empty:
                df["time"] = pd.to_datetime(df["time"])

            self.logger.info(f"✓ Fetching {len(df)} rows of data succeeded")
            if not df.empty:
                self.logger.info(f"  Date range: {df['time'].min()} to {df['time'].max()}")
            
            return df

        except requests.exceptions.Timeout:
            self.logger.error("✗ Request timeout - Frankfurter API not responding")
            raise
        except requests.exceptions.RequestException as e:
            self.logger.error(f"✗ API request failed: {e}")
            raise
        except ValueError as e:
            self.logger.error(f"✗ Invalid response data: {e}")
            raise
