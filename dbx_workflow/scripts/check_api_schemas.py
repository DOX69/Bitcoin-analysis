import requests
import json
import subprocess
import os
import sys
from datetime import datetime, timedelta

# Configuration
COINBASE_TICKER = "BTC-USD"
COINBASE_URL = f"https://api.exchange.coinbase.com/products/{COINBASE_TICKER}/candles"
FRANKFURTER_BASE = "USD"
FRANKFURTER_SYMBOL = "EUR"
FRANKFURTER_URL = "https://api.frankfurter.dev/v1"

# Paths
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR) # dbx_workflow
SRC_DIR = os.path.join(PROJECT_ROOT, "src", "raw_ingest", "api_models")

def fetch_coinbase_schema():
    print(f"Fetching Coinbase schema for {COINBASE_TICKER}...")
    # Fetch just one candle to get the structure
    end_date = datetime.now()
    start_date = end_date - timedelta(days=1)
    params = {
        "start": start_date.isoformat(),
        "end": end_date.isoformat(),
        "granularity": 86400
    }
    try:
        response = requests.get(COINBASE_URL, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()

        # Save to temp file
        temp_file = os.path.join(SCRIPT_DIR, "temp_coinbase.json")
        with open(temp_file, "w") as f:
            json.dump(data, f, indent=2)

        return temp_file
    except Exception as e:
        print(f"Error fetching Coinbase schema: {e}")
        return None

def fetch_frankfurter_schema():
    print(f"Fetching Frankfurter schema for {FRANKFURTER_BASE}/{FRANKFURTER_SYMBOL}...")
    # Fetch a small range
    end_date = datetime.now()
    start_date = end_date - timedelta(days=5)
    start_str = start_date.strftime("%Y-%m-%d")
    end_str = end_date.strftime("%Y-%m-%d")

    url = f"{FRANKFURTER_URL}/{start_str}..{end_str}"
    params = {
        "base": FRANKFURTER_BASE,
        "symbols": FRANKFURTER_SYMBOL
    }

    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()

        # Determine if we can use smart schema generation
        use_smart_schema = False
        if "rates" in data and isinstance(data["rates"], dict):
            # Check if values are dicts (standard case)
            if data["rates"] and isinstance(next(iter(data["rates"].values())), dict):
                use_smart_schema = True

        if use_smart_schema:
            print("Detected standard Frankfurter structure (rates dict). Generating JSON Schema...")
            schema = generate_frankfurter_jsonschema(data)
            temp_file = os.path.join(SCRIPT_DIR, "temp_frankfurter_schema.json")
            with open(temp_file, "w") as f:
                json.dump(schema, f, indent=2)
            return temp_file, "jsonschema"
        else:
            print("Detected non-standard structure. Using raw JSON.")
            temp_file = os.path.join(SCRIPT_DIR, "temp_frankfurter.json")
            with open(temp_file, "w") as f:
                json.dump(data, f, indent=2)
            return temp_file, "json"

    except Exception as e:
        print(f"Error fetching Frankfurter schema: {e}")
        return None, None

def generate_frankfurter_jsonschema(data):
    """
    Manually generate a JSON Schema that forces 'rates' to be a dict of objects.
    """
    schema = {
        "$schema": "http://json-schema.org/draft-07/schema#",
        "type": "object",
        "properties": {},
        "required": [],
        "title": "FrankfurterResponse"
    }

    for key, value in data.items():
        schema["required"].append(key)

        if key == "rates":
            # We already checked it's a dict of dicts
            first_val = next(iter(value.values()))

            inner_props = {}
            for k, v in first_val.items():
                if isinstance(v, (int, float)):
                    inner_props[k] = {"type": "number"}
                elif isinstance(v, str):
                    inner_props[k] = {"type": "string"}

            # Use 'CurrencyRates' as title for the inner object so codegen uses that name
            schema["properties"][key] = {
                "type": "object",
                "additionalProperties": {
                    "type": "object",
                    "properties": inner_props,
                    "required": list(inner_props.keys()),
                    "title": "CurrencyRates"
                }
            }

        elif isinstance(value, (int, float)):
             schema["properties"][key] = {"type": "number"}
        elif isinstance(value, str):
             schema["properties"][key] = {"type": "string"}
        elif isinstance(value, bool):
             schema["properties"][key] = {"type": "boolean"}
        else:
             # Fallback
             schema["properties"][key] = {}

    return schema

def generate_models(input_file, output_file, class_name, model_type="pydantic_v2.BaseModel", input_type="json"):
    print(f"Generating model for {input_file} -> {output_file} ({input_type})...")
    # Use sys.executable to run the module directly
    cmd = [
        sys.executable, "-m", "datamodel_code_generator",
        "--input", input_file,
        "--output", output_file,
        "--class-name", class_name,
        "--output-model-type", model_type,
        "--input-file-type", input_type,
        "--use-schema-description",
        "--use-annotated",
        "--disable-timestamp"
    ]

    try:
        subprocess.run(cmd, check=True)
        print(f"Successfully generated {output_file}")
    except subprocess.CalledProcessError as e:
        print(f"Error generating model: {e}")

def main():
    # Ensure output directory exists
    os.makedirs(SRC_DIR, exist_ok=True)

    # Coinbase
    coinbase_json = fetch_coinbase_schema()
    if coinbase_json:
        output_path = os.path.join(SRC_DIR, "coinbase.py")
        generate_models(coinbase_json, output_path, "CoinbaseCandleResponse", "pydantic_v2.BaseModel", "json")
        os.remove(coinbase_json)

    # Frankfurter
    frankfurter_file, file_type = fetch_frankfurter_schema()
    if frankfurter_file:
        output_path = os.path.join(SRC_DIR, "frankfurter.py")
        generate_models(frankfurter_file, output_path, "FrankfurterResponse", "pydantic_v2.BaseModel", file_type)
        os.remove(frankfurter_file)

if __name__ == "__main__":
    main()
