import json
import logging
import os
import shutil
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

    init_file = os.path.join(OUTPUT_DIR, "__init__.py")
    if not os.path.exists(init_file):
        with open(init_file, "w") as f:
            f.write("")

def fetch_json(url, params=None):
    try:
        response = requests.get(url, params=params, timeout=10, headers={"User-Agent": "SchemaCheck/1.0"})
        response.raise_for_status()
        return response.json()
    except Exception as e:
        logger.error(f"Failed to fetch data from {url}: {e}")
        raise

def get_codegen_cmd():
    # Try to find datamodel-codegen in the same directory as the python executable
    bin_dir = os.path.dirname(sys.executable)
    codegen = os.path.join(bin_dir, "datamodel-codegen")
    if os.path.exists(codegen):
        return [codegen]

    if shutil.which("datamodel-codegen"):
        return ["datamodel-codegen"]

    # Fallback to running as module if possible (though not standard for this tool)
    return ["datamodel-codegen"]

def generate_model(input_data, input_type, output_file, class_name):
    cmd_base = get_codegen_cmd()
    temp_json = f"temp_{class_name}.json"

    # Save input to temp file
    with open(temp_json, "w") as f:
        json.dump(input_data, f)

    try:
        cmd = cmd_base + [
            "--input", temp_json,
            "--input-file-type", input_type,
            "--output", output_file,
            "--class-name", class_name,
            "--output-model-type", "pydantic_v2.BaseModel",
            "--use-double-quotes",
            "--disable-timestamp"
        ]

        logger.info(f"Running codegen for {class_name}...")
        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode != 0:
            logger.error(f"datamodel-codegen failed for {class_name}: {result.stderr}")
            raise RuntimeError(f"Codegen failed for {class_name}")

        logger.info(f"Successfully generated model for {class_name} at {output_file}")

    finally:
        if os.path.exists(temp_json):
            os.remove(temp_json)

def check_coinbase():
    logger.info("Processing Coinbase schema...")
    # Fetching candles
    cb_url = "https://api.exchange.coinbase.com/products/BTC-USD/candles"
    # Granularity 86400 = 1 day
    data = fetch_json(cb_url, params={"granularity": 86400})

    output_file = os.path.join(OUTPUT_DIR, "coinbase.py")
    generate_model(data, "json", output_file, "CoinbaseCandleResponse")

def check_frankfurter():
    logger.info("Processing Frankfurter schema...")

    # Check if we are running in an environment with weird dates (like sandbox 2026)
    # If so, fallback to hardcoded dates to ensure API works.
    current_year = datetime.now().year
    if current_year > 2025:
        logger.warning(f"System year is {current_year}, which seems futuristic. Using hardcoded 2024 dates for Frankfurter.")
        end_date = datetime(2024, 1, 8)
        start_date = datetime(2024, 1, 1)
    else:
        end_date = datetime.now()
        start_date = end_date - timedelta(days=7)

    url = f"https://api.frankfurter.dev/v1/{start_date.strftime('%Y-%m-%d')}..{end_date.strftime('%Y-%m-%d')}"

    logger.info(f"Fetching Frankfurter data from {url}")
    data = fetch_json(url)

    # Build Schema using Genson
    builder = SchemaBuilder()
    builder.add_object(data)
    schema = builder.to_schema()

    # Post-process schema to handle dynamic dates in 'rates'
    if "properties" in schema and "rates" in schema["properties"]:
        rates_prop = schema["properties"]["rates"]

        # We want to convert specific date keys to additionalProperties
        # Find a sample value schema (the inner dictionary of a rate)
        sample_val = None

        # rates_prop["properties"] contains keys like "2024-01-01", "2024-01-02"
        if "properties" in rates_prop and rates_prop["properties"]:
            first_key = next(iter(rates_prop["properties"]))
            sample_val = rates_prop["properties"][first_key]

        if sample_val:
            # Clear specific properties and required fields
            rates_prop.pop("properties", None)
            rates_prop.pop("required", None)
            # Set additionalProperties to the sample schema
            rates_prop["additionalProperties"] = sample_val
            # Ensure type is object
            rates_prop["type"] = "object"
            logger.info("Modified Frankfurter schema to handle dynamic date keys in 'rates'")
        else:
            logger.warning("Could not find sample rate properties to generalize.")

    output_file = os.path.join(OUTPUT_DIR, "frankfurter.py")
    generate_model(schema, "jsonschema", output_file, "FrankfurterResponse")

def main():
    ensure_output_dir()

    failed = False
    try:
        check_coinbase()
    except Exception as e:
        logger.error(f"Coinbase check failed: {e}")
        failed = True

    try:
        check_frankfurter()
    except Exception as e:
        logger.error(f"Frankfurter check failed: {e}")
        failed = True

    if failed:
        sys.exit(1)

if __name__ == "__main__":
    main()
