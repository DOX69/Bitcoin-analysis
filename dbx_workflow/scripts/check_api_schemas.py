import json
import logging
import os
import subprocess
import sys
from datetime import datetime, timedelta
import requests
from genson import SchemaBuilder

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Constants
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTPUT_DIR = os.path.join(BASE_DIR, "src", "raw_ingest", "api_models")

def ensure_output_dir():
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)

    # Create __init__.py if not exists
    init_file = os.path.join(OUTPUT_DIR, "__init__.py")
    if not os.path.exists(init_file):
        with open(init_file, "w") as f:
            f.write("")

    # Create README.md if not exists
    readme_file = os.path.join(OUTPUT_DIR, "README.md")
    if not os.path.exists(readme_file):
        with open(readme_file, "w") as f:
            f.write("# API Models\n\nThis directory contains auto-generated Pydantic models. Do not edit manually.")

def fetch_json(url, params=None):
    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        logger.error(f"Failed to fetch data from {url}: {e}")
        sys.exit(1)

def run_codegen(input_file, output_file, class_name, input_type="json"):
    try:
        # Determine executable path
        bin_dir = os.path.dirname(sys.executable)
        codegen_cmd = os.path.join(bin_dir, "datamodel-codegen")
        if not os.path.exists(codegen_cmd):
            codegen_cmd = "datamodel-codegen"

        cmd = [
            codegen_cmd,
            "--input", input_file,
            "--input-file-type", input_type,
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
        pass

def process_coinbase():
    logger.info("Processing Coinbase schema...")
    # Fetching candles as it's the main data used
    cb_url = "https://api.exchange.coinbase.com/products/BTC-USD/candles"
    cb_data = fetch_json(cb_url, params={"granularity": 86400})

    # Save temp json
    temp_json = "temp_coinbase.json"
    with open(temp_json, "w") as f:
        json.dump(cb_data, f)

    try:
        generate_to = os.path.join(OUTPUT_DIR, "coinbase.py")
        run_codegen(temp_json, generate_to, "CoinbaseCandleResponse", input_type="json")
    finally:
        if os.path.exists(temp_json):
            os.remove(temp_json)

def process_frankfurter():
    logger.info("Processing Frankfurter schema...")
    end_date = datetime.now()
    start_date = end_date - timedelta(days=7)
    f_url = f"https://api.frankfurter.dev/v1/{start_date.strftime('%Y-%m-%d')}..{end_date.strftime('%Y-%m-%d')}"

    f_data = fetch_json(f_url, params={"base": "USD", "symbols": "EUR"})

    # Validate structure
    if "rates" not in f_data or not isinstance(f_data["rates"], dict):
        logger.error("Frankfurter response missing 'rates' dict")
        sys.exit(1)

    if not f_data["rates"]:
        logger.warning("Frankfurter response 'rates' dict is empty. Skipping schema update.")
        return

    # 1. Generate schema for the inner rate object (CurrencyRates)
    # Take the first available rate object as sample
    first_key = next(iter(f_data["rates"]))
    sample_rate_obj = f_data["rates"][first_key]

    builder = SchemaBuilder()
    builder.add_object(sample_rate_obj)
    inner_schema = builder.to_schema()

    # 2. Construct the full schema with additionalProperties for rates
    # We remove rates temporarily to build the base schema without the dynamic keys
    rates_backup = f_data.pop("rates")
    outer_builder = SchemaBuilder()
    outer_builder.add_object(f_data)
    full_schema = outer_builder.to_schema()

    # Inject rates back into schema
    # We want rates to be Dict[str, inner_schema]
    # In JSON Schema: "rates": {"type": "object", "additionalProperties": inner_schema}

    if "properties" not in full_schema:
        full_schema["properties"] = {}

    full_schema["properties"]["rates"] = {
        "type": "object",
        "additionalProperties": inner_schema
    }
    # Ensure 'rates' is required if it was in the original data
    if "required" not in full_schema:
        full_schema["required"] = []
    if "rates" not in full_schema["required"]:
        full_schema["required"].append("rates")

    # Save temp schema
    temp_schema = "temp_frankfurter_schema.json"
    with open(temp_schema, "w") as f:
        json.dump(full_schema, f, indent=2)

    try:
        generate_to = os.path.join(OUTPUT_DIR, "frankfurter.py")
        run_codegen(temp_schema, generate_to, "FrankfurterResponse", input_type="jsonschema")
    finally:
        if os.path.exists(temp_schema):
            os.remove(temp_schema)

def main():
    ensure_output_dir()
    process_coinbase()
    process_frankfurter()

if __name__ == "__main__":
    main()
