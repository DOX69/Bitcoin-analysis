import os
import json
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    from ruamel.yaml import YAML
except ImportError:
    print("Error: ruamel.yaml is required. Install it with 'pip install ruamel.yaml'")
    sys.exit(1)

try:
    from openai import OpenAI
except ImportError:
    print("Warning: openai is not installed. AI descriptions will be skipped.")
    OpenAI = None

# Initialize YAML handler
yaml = YAML()
yaml.preserve_quotes = True
yaml.indent(mapping=2, sequence=4, offset=2)

PROJECT_DIR = Path("dbt_silver_gold")
TARGET_DIR = PROJECT_DIR / "target"
MANIFEST_PATH = TARGET_DIR / "manifest.json"
CATALOG_PATH = TARGET_DIR / "catalog.json"

def run_dbt_docs_generate():
    """Runs dbt docs generate to produce manifest and catalog."""
    print("Running dbt docs generate...")
    try:
        # Assuming dbt is in PATH and we are at repo root
        # Removed --profiles-dir to rely on default or env var DBT_PROFILES_DIR
        subprocess.run(
            ["dbt", "docs", "generate", "--project-dir", str(PROJECT_DIR)],
            check=True,
            capture_output=True, # Capture output to avoid cluttering logs unless error
            text=True
        )
        print("dbt docs generate completed successfully.")
    except subprocess.CalledProcessError as e:
        print(f"Error running dbt docs generate:\n{e.stderr}")
        # Check if manifest and catalog exist anyway (maybe previous run)
        if not MANIFEST_PATH.exists() or not CATALOG_PATH.exists():
             sys.exit(1)
        print("Using existing manifest/catalog despite error.")

def load_json(path: Path) -> Dict[str, Any]:
    with open(path, "r") as f:
        return json.load(f)

def get_openai_description(column_name: str, model_name: str) -> str:
    """Generates a description for a column using OpenAI."""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key or not OpenAI:
        return "TODO: Add description"

    client = OpenAI(api_key=api_key)

    prompt = f"Provide a concise, one-sentence description for the column '{column_name}' in the database table/model '{model_name}'. The description should be suitable for data documentation."

    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a helpful data assistant."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=50,
            temperature=0.3
        )
        description = response.choices[0].message.content.strip()
        # Remove trailing periods if present for consistency, or keep them. Let's keep them if complete sentence.
        return description
    except Exception as e:
        print(f"Error generating description for {column_name}: {e}")
        return "TODO: Add description"

def update_properties_file(properties_path: Path, model_name: str, columns: Dict[str, Any]):
    """Updates the properties.yml file with new columns."""

    if not properties_path.exists():
        # Create new file structure
        data = {"version": 2, "models": []}
    else:
        with open(properties_path, "r") as f:
            data = yaml.load(f) or {"version": 2, "models": []}

    # Find or create model entry
    model_entry = None
    if "models" in data:
        for model in data["models"]:
            if model["name"] == model_name:
                model_entry = model
                break

    if not model_entry:
        model_entry = {"name": model_name, "columns": []}
        data.setdefault("models", []).append(model_entry)

    # Update columns
    existing_columns = {col["name"]: col for col in model_entry.get("columns", [])}

    updated = False

    # Process columns from catalog
    sorted_cols = sorted(columns.items(), key=lambda x: x[1]['index'])

    new_columns_list = []

    for col_name, col_meta in sorted_cols:
        col_name_lower = col_name.lower()
        if col_name_lower in existing_columns:
            # Check if description is missing/empty
            current_col = existing_columns[col_name_lower]
            if "description" not in current_col or not current_col["description"]:
                description = get_openai_description(col_name, model_name)
                current_col["description"] = description
                updated = True
                print(f"Updated description for {model_name}.{col_name}")
            new_columns_list.append(current_col)
        else:
            # New column
            description = get_openai_description(col_name, model_name)
            new_col = {
                "name": col_name_lower,
                "description": description
            }
            # Add type info if available from catalog? dbt catalog provides 'type'
            if "type" in col_meta:
                 # Optional: add data_type or similar comment?
                 # Usually dbt users just want name and description.
                 pass

            new_columns_list.append(new_col)
            updated = True
            print(f"Added column {model_name}.{col_name}")

    # Replace columns list to maintain order (or append? replacing ensures order matches DB usually)
    # But we might lose manual metadata on existing columns if we just replace.
    # So better: Keep existing columns object, append new ones, maybe reorder?
    # For now, let's just append new ones to the list if they aren't there.

    # Re-reading existing columns to preserve custom keys (tests, tags, etc)
    final_columns = []

    # Use a dict for fast lookup of existing processed columns
    # We want to preserve the order from the DB catalog preferably, or keep existing order?
    # Let's append new columns at the end.

    existing_col_names = set()
    if "columns" in model_entry:
         for col in model_entry["columns"]:
             existing_col_names.add(col["name"])
             final_columns.append(col)

    for col_name, col_meta in sorted_cols:
        col_name_lower = col_name.lower()
        if col_name_lower not in existing_col_names:
            description = get_openai_description(col_name, model_name)
            new_col = {
                "name": col_name_lower,
                "description": description
            }
            final_columns.append(new_col)
            updated = True
            print(f"Added column {model_name}.{col_name}")

    model_entry["columns"] = final_columns

    if updated:
        with open(properties_path, "w") as f:
            yaml.dump(data, f)
        print(f"Updated {properties_path}")

def main():
    # 1. Run dbt docs generate
    run_dbt_docs_generate()

    # 2. Load manifest and catalog
    if not MANIFEST_PATH.exists() or not CATALOG_PATH.exists():
        print("Manifest or Catalog not found. Exiting.")
        sys.exit(1)

    manifest = load_json(MANIFEST_PATH)
    catalog = load_json(CATALOG_PATH)

    # 3. Iterate over models
    for node_id, node in manifest["nodes"].items():
        if node["resource_type"] != "model":
            continue

        # Check if model is in this project (not a dependency)
        if node["package_name"] != "dbt_silver_gold":
            continue

        model_name = node["name"]

        # Find corresponding catalog entry
        catalog_entry = catalog["nodes"].get(node_id)
        if not catalog_entry:
            print(f"Warning: No catalog entry for {model_name}. Skipping.")
            continue

        # Get columns from catalog
        columns = catalog_entry["columns"]

        # Determine properties.yml path
        # 'original_file_path' is relative to project root, e.g. "models/gold/crypto_prices/daily_ohlc.sql"
        # We want the schema file in the same directory.
        original_file_path = Path(node["original_file_path"])
        model_dir = PROJECT_DIR / original_file_path.parent

        # Check for existing schema.yml or properties.yml
        properties_path = model_dir / "properties.yml"
        if not properties_path.exists():
             schema_path = model_dir / "schema.yml"
             if schema_path.exists():
                 properties_path = schema_path

        # Update it
        update_properties_file(properties_path, model_name, columns)

if __name__ == "__main__":
    main()
