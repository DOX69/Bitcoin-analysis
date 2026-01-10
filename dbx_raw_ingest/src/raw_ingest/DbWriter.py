from datetime import datetime
from pathlib import Path
from typing import Optional
import logging
import pandas as pd
import os
from dotenv import load_dotenv

# Charger variables d'environnement
load_dotenv()

# Configuration logging
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class DbWriter:
    def __init__(self):
        self.data_dir = None

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