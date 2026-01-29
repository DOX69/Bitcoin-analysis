import json
import logging
import os
import subprocess
import sys
from datetime import datetime, timedelta
import requests

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Constants
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTPUT_DIR = os.path.join(BASE_DIR, "src", "raw_ingest", "api_models")

def ensure_output_dir():
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)
        # Create __init__.py
        init_file = os.path.join(OUTPUT_DIR, "__init__.py")
        if not os.path.exists(init_file):
            with open(init_file, "w") as f:
                f.write("")

def fetch_json(url, params=None):
    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        logger.error(f"Failed to fetch data from {url}: {e}")
        sys.exit(1)

def generate_model(json_data, output_file, class_name):
    # Save JSON to temp file
    temp_json = f"temp_{class_name}.json"
    with open(temp_json, "w") as f:
        json.dump(json_data, f)

    try:
        # Determine executable path
        # Assuming we are running in a venv where datamodel-codegen is alongside python
        bin_dir = os.path.dirname(sys.executable)
        codegen_cmd = os.path.join(bin_dir, "datamodel-codegen")

        # If not found (e.g. windows or different structure), try just the command
        if not os.path.exists(codegen_cmd):
            codegen_cmd = "datamodel-codegen"

        cmd = [
            codegen_cmd,
            "--input", temp_json,
            "--input-file-type", "json",
            "--output", output_file,
            "--class-name", class_name,
            "--output-model-type", "pydantic_v2.BaseModel",
            "--use-double-quotes",
            "--disable-timestamp"
        ]

        logger.info(f"Running: {' '.join(cmd)}")
        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode != 0:
            logger.error(f"datamodel-codegen failed: {result.stderr}")
            sys.exit(1)

        logger.info(f"Successfully generated model for {class_name} at {output_file}")

    finally:
        if os.path.exists(temp_json):
            os.remove(temp_json)

def main():
    ensure_output_dir()

    # 1. Coinbase
    logger.info("Processing Coinbase schema...")
    # Fetching candles as it's the main data used
    cb_url = "https://api.exchange.coinbase.com/products/BTC-USD/candles"
    cb_data = fetch_json(cb_url, params={"granularity": 86400})

    generate_model(cb_data, os.path.join(OUTPUT_DIR, "coinbase.py"), "CoinbaseCandleResponse")

    # 2. Frankfurter
    logger.info("Processing Frankfurter schema...")
    end_date = datetime.now()
    start_date = end_date - timedelta(days=7)
    f_url = f"https://api.frankfurter.dev/v1/{start_date.strftime('%Y-%m-%d')}..{end_date.strftime('%Y-%m-%d')}"

    f_data = fetch_json(f_url, params={"base": "USD", "symbols": "EUR"})

    # Normalize rates to avoid daily diffs due to changing dates
    # We replace the specific dates with a generic key to encourage Dict generation or a stable single field
    if "rates" in f_data and isinstance(f_data["rates"], dict) and f_data["rates"]:
        first_key = next(iter(f_data["rates"]))
        first_val = f_data["rates"][first_key]
        # We use a fixed key so the schema remains stable
        f_data["rates"] = {"CurrencyRates": first_val}

    f_model_path = os.path.join(OUTPUT_DIR, "frankfurter.py")
    generate_model(f_data, f_model_path, "FrankfurterResponse")

    # Post-process Frankfurter model to use Dict for rates
    # We want Rates to be a Dict[str, CurrencyRates] instead of a class with a single field
    with open(f_model_path, "r") as f:
        content = f.read()

    import re
    # Replace the Rates class definition with a type alias
    # Expecting: class Rates(BaseModel):\n    CurrencyRates: CurrencyRates = Field(..., alias="CurrencyRates")
    # Note: datamodel-codegen might use CurrencyRates_1 if there is a conflict, but usually not with CamelCase if logic allows.
    # We use a regex that is slightly flexible on the field name part just in case.
    pattern = r"class Rates\(BaseModel\):\n\s+CurrencyRates(_\d+)?: CurrencyRates = Field\(..., alias=\"CurrencyRates\"\)"
    replacement = "Rates = dict[str, CurrencyRates]"

    new_content = re.sub(pattern, replacement, content)

    if new_content != content:
        with open(f_model_path, "w") as f:
            f.write(new_content)
        logger.info("Successfully post-processed Frankfurter model to use Dict for Rates")
    else:
        logger.warning("Could not find Rates class to replace in Frankfurter model")

if __name__ == "__main__":
    main()
