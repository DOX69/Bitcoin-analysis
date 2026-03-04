import requests
import pandas as pd
from raw_ingest.BaseFetcher import BaseFetcher

class SwapiFetcher(BaseFetcher):
    def __init__(self, logger, catalog: str, schema: str):
        super().__init__(
            logger=logger,
            ticker="swapi",
            currency="characters",
            catalog=catalog,
            schema=schema,
            base_url="https://swapi.dev/api/people"
        )
        self.table_name = "characters"
        self.full_path_table_name = f"{catalog}.{schema}.{self.table_name}"

    def fetch_historical_data(self):
        """Fetches all characters from SWAPI with pagination."""
        all_results = []
        next_url = self.base_url

        while next_url:
            self.logger.info(f"Fetching SWAPI characters from {next_url}")
            response = requests.get(next_url)
            response.raise_for_status()
            data = response.json()
            
            all_results.extend(data.get("results", []))
            next_url = data.get("next")

        if not all_results:
            return pd.DataFrame()

        return pd.DataFrame(all_results)

    def fetch_characters(self):
        """Helper method for testing and specific character fetching."""
        return self.fetch_historical_data()
