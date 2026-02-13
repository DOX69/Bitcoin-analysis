import json
import subprocess
import sys
import requests
from pathlib import Path
from datetime import datetime, timedelta
from genson import Schema

# Constants
COINBASE_URL = "https://api.exchange.coinbase.com/products/BTC-USD/candles?granularity=86400"
FRANKFURTER_BASE_URL = "https://api.frankfurter.dev/v1"

# Paths
SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent
API_MODELS_DIR = PROJECT_ROOT / "src" / "raw_ingest" / "api_models"

def fetch_coinbase_data():
    """Fetches a sample of Coinbase candle data."""
    # We fetch only a few candles to get the structure
    try:
        response = requests.get(COINBASE_URL, timeout=10)
        response.raise_for_status()
        data = response.json()
        # Take a slice to keep it small but representative
        return data[:5] if isinstance(data, list) else data
    except Exception as e:
        print(f"Error fetching Coinbase data: {e}")
        sys.exit(1)

def fetch_frankfurter_data():
    """Fetches a sample of Frankfurter rates data."""
    # Dynamic date range: last 30 days to ensure we get multiple dates
    end_date = datetime.now()
    start_date = end_date - timedelta(days=30)

    # If system date is way in the future (test env), cap it
    if start_date.year > 2025:
        start_date = datetime(2024, 1, 1)
        end_date = datetime(2024, 1, 31)

    start_str = start_date.strftime("%Y-%m-%d")
    end_str = end_date.strftime("%Y-%m-%d")

    url = f"{FRANKFURTER_BASE_URL}/{start_str}..{end_str}?base=USD&symbols=EUR"

    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"Error fetching Frankfurter data: {e}")
        sys.exit(1)

def generate_json_schema(data):
    """Generates a JSON Schema from data using Genson."""
    schema_builder = Schema()
    schema_builder.add_object(data)
    return schema_builder.to_dict()

def generate_frankfurter_smart_schema(data):
    """
    Generates a schema for Frankfurter response where 'rates' is treated as a Dict[str, Inner].
    This prevents generating specific fields for each date.
    """
    # 1. Generate the full schema first to get outer structure
    builder = Schema()
    builder.add_object(data)
    schema = builder.to_dict()

    # 2. Fix 'rates' to use additionalProperties instead of specific properties
    props = schema.get('properties', {})
    if 'rates' in props:
        rates_schema = props['rates']

        # Build a schema for the inner values (the daily rates)
        inner_builder = Schema()
        for val in data.get('rates', {}).values():
            inner_builder.add_object(val)

        # Replace specific date properties with generic additionalProperties
        rates_schema.pop('properties', None)
        rates_schema.pop('required', None)
        rates_schema['additionalProperties'] = inner_builder.to_dict()

    return schema

def run_datamodel_codegen(input_file: Path, output_file: Path, class_name: str, input_type: str = "json"):
    """Runs datamodel-code-generator."""
    cmd = [
        sys.executable, "-m", "datamodel_code_generator",
        "--input", str(input_file),
        "--output", str(output_file),
        "--class-name", class_name,
        "--input-file-type", input_type,
        "--output-model-type", "pydantic_v2.BaseModel",
        "--disable-timestamp"  # Avoid noise in diffs
    ]

    try:
        subprocess.check_call(cmd)
        print(f"Generated {output_file.name}")
    except subprocess.CalledProcessError as e:
        print(f"Error generating model for {class_name}: {e}")
        sys.exit(1)

def main():
    print("Starting API schema check...")

    # Ensure output directory exists
    API_MODELS_DIR.mkdir(parents=True, exist_ok=True)

    # --- Coinbase ---
    print("Fetching Coinbase data...")
    coinbase_data = fetch_coinbase_data()
    temp_coinbase = SCRIPT_DIR / "temp_coinbase.json"
    with open(temp_coinbase, "w") as f:
        json.dump(coinbase_data, f)

    print("Generating Coinbase model...")
    run_datamodel_codegen(
        temp_coinbase,
        API_MODELS_DIR / "coinbase.py",
        "CoinbaseCandleResponse",
        input_type="json"
    )

    # --- Frankfurter ---
    print("Fetching Frankfurter data...")
    frankfurter_data = fetch_frankfurter_data()

    # Generate Schema using Genson to handle dynamic date keys in 'rates'
    # Genson will see {"rates": {"2023-01-01": {...}, "2023-01-02": {...}}}
    # and generalize it to "rates": {"patternProperties": {".*": {...}}} or similar structure
    # which datamodel-code-generator interprets as Dict[str, ...]
    print("Generating Frankfurter schema...")
    # Use smart schema generation to handle dynamic dates
    frankfurter_schema = generate_frankfurter_smart_schema(frankfurter_data)
    temp_frankfurter_schema = SCRIPT_DIR / "temp_frankfurter_schema.json"
    with open(temp_frankfurter_schema, "w") as f:
        json.dump(frankfurter_schema, f)

    print("Generating Frankfurter model...")
    run_datamodel_codegen(
        temp_frankfurter_schema,
        API_MODELS_DIR / "frankfurter.py",
        "FrankfurterResponse",
        input_type="jsonschema"
    )

    # Cleanup
    if temp_coinbase.exists():
        temp_coinbase.unlink()
    if temp_frankfurter_schema.exists():
        temp_frankfurter_schema.unlink()

    print("Schema check complete.")

if __name__ == "__main__":
    main()
