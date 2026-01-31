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

def run_codegen(input_file, input_type, output_file, class_name):
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

def generate_coinbase_model(data):
    # Coinbase is a list of lists, we can use simple JSON input
    temp_json = "temp_CoinbaseCandleResponse.json"
    with open(temp_json, "w") as f:
        json.dump(data, f)

    try:
        run_codegen(temp_json, "json", os.path.join(OUTPUT_DIR, "coinbase.py"), "CoinbaseCandleResponse")
    finally:
        if os.path.exists(temp_json):
            os.remove(temp_json)

def generate_frankfurter_model(data):
    # Frankfurter has dynamic keys in 'rates', so we build a schema and adjust it
    builder = SchemaBuilder()
    builder.add_object(data)
    schema = builder.to_schema()

    # Locate 'rates' and convert to additionalProperties
    if "properties" in schema and "rates" in schema["properties"]:
        rates_schema = schema["properties"]["rates"]
        if "properties" in rates_schema:
            # Collect all value schemas from the dynamic keys
            value_builder = SchemaBuilder()
            for prop_name, prop_schema in rates_schema["properties"].items():
                value_builder.add_schema(prop_schema)

            unified_value_schema = value_builder.to_schema()

            # Replace properties with additionalProperties
            rates_schema["additionalProperties"] = unified_value_schema
            del rates_schema["properties"]

            # Remove required since keys are dynamic
            if "required" in rates_schema:
                del rates_schema["required"]

    temp_schema = "temp_FrankfurterResponse_schema.json"
    with open(temp_schema, "w") as f:
        json.dump(schema, f)

    try:
        run_codegen(temp_schema, "jsonschema", os.path.join(OUTPUT_DIR, "frankfurter.py"), "FrankfurterResponse")
    finally:
        if os.path.exists(temp_schema):
            os.remove(temp_schema)

def main():
    ensure_output_dir()

    # 1. Coinbase
    logger.info("Processing Coinbase schema...")
    cb_url = "https://api.exchange.coinbase.com/products/BTC-USD/candles"
    cb_data = fetch_json(cb_url, params={"granularity": 86400})
    generate_coinbase_model(cb_data)

    # 2. Frankfurter
    logger.info("Processing Frankfurter schema...")
    end_date = datetime.now()
    start_date = end_date - timedelta(days=7)
    f_url = f"https://api.frankfurter.dev/v1/{start_date.strftime('%Y-%m-%d')}..{end_date.strftime('%Y-%m-%d')}"
    f_data = fetch_json(f_url, params={"base": "USD", "symbols": "EUR"})
    generate_frankfurter_model(f_data)

if __name__ == "__main__":
    main()
