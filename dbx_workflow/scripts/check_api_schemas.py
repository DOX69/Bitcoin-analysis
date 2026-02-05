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

def generate_model(input_data, output_file, class_name, input_type="json"):
    """
    Generates a Pydantic model using datamodel-code-generator.

    Args:
        input_data: The JSON data (list or dict) or the JSON Schema dict.
        output_file: The path to save the generated model.
        class_name: The name of the root class.
        input_type: "json" or "jsonschema".
    """
    # Save input data to temp file
    temp_file = f"temp_{class_name}.json"
    with open(temp_file, "w") as f:
        json.dump(input_data, f)

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
            "--input", temp_file,
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
        if os.path.exists(temp_file):
            os.remove(temp_file)

def main():
    ensure_output_dir()

    # 1. Coinbase
    logger.info("Processing Coinbase schema...")
    # Fetching candles as it's the main data used
    cb_url = "https://api.exchange.coinbase.com/products/BTC-USD/candles"
    cb_data = fetch_json(cb_url, params={"granularity": 86400})

    generate_model(cb_data, os.path.join(OUTPUT_DIR, "coinbase.py"), "CoinbaseCandleResponse", input_type="json")

    # 2. Frankfurter
    logger.info("Processing Frankfurter schema...")
    end_date = datetime.now()
    start_date = end_date - timedelta(days=7)
    f_url = f"https://api.frankfurter.dev/v1/{start_date.strftime('%Y-%m-%d')}..{end_date.strftime('%Y-%m-%d')}"

    f_data = fetch_json(f_url, params={"base": "USD", "symbols": "EUR"})

    # Separate 'rates' to handle them as dynamic keys (Dict[str, CurrencyRates])
    # The 'rates' object contains date keys like "2023-01-01": {"EUR": 0.93}
    rates_data = f_data.pop("rates", {})

    # Build schema for the main response (without rates for now)
    builder = SchemaBuilder()
    builder.add_object(f_data)
    schema = builder.to_schema()

    # Build schema for the rate values
    # We collect all values from the rates dict to infer a unified schema
    if rates_data:
        rate_builder = SchemaBuilder()
        for rate_val in rates_data.values():
            rate_builder.add_object(rate_val)
        rate_value_schema = rate_builder.to_schema()

        # Inject 'rates' into the main schema with additionalProperties
        if "properties" not in schema:
            schema["properties"] = {}

        # Define 'rates' as an object where keys are arbitrary strings (dates) and values match rate_value_schema
        schema["properties"]["rates"] = {
            "type": "object",
            "additionalProperties": rate_value_schema,
            "title": "Rates" # Helps generate a nice type alias name
        }

        # Ensure 'rates' is required if it was in the original data
        if "required" not in schema:
            schema["required"] = []
        if "rates" not in schema["required"]:
            schema["required"].append("rates")

    f_model_path = os.path.join(OUTPUT_DIR, "frankfurter.py")
    generate_model(schema, f_model_path, "FrankfurterResponse", input_type="jsonschema")

if __name__ == "__main__":
    main()
