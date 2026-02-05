import os
import json
import subprocess
import sys
from pathlib import Path

# Try imports
try:
    from ruamel.yaml import YAML
except ImportError:
    print("ruamel.yaml not found. Please run with 'uv run --with ruamel.yaml ...'")
    sys.exit(1)

try:
    import openai
except ImportError:
    openai = None

DBT_PROJECT_DIR = Path("dbt_silver_gold")
PROFILES_DIR = Path.home() / ".dbt"

def setup_profile():
    """Sets up a temporary profiles.yml for connection."""
    PROFILES_DIR.mkdir(parents=True, exist_ok=True)

    host = os.environ.get('DATABRICKS_HOST', '')
    token = os.environ.get('DATABRICKS_TOKEN', '')
    http_path = os.environ.get('DATABRICKS_HTTP_PATH', '')

    if not (host and token and http_path):
        print("Missing Databricks credentials (HOST, TOKEN, HTTP_PATH). Skipping dbt docs generate.")
        # If we can't connect, we can't fetch the DB schema, so we can't discover NEW columns from the DB.
        # But we can still ensure the YAML structure exists for models found in 'dbt parse'.
        return False

    profiles_content = f"""
dbt_silver_gold:
  target: prod
  outputs:
    prod:
      type: databricks
      host: "{host}"
      http_path: "{http_path}"
      token: "{token}"
      schema: "gold"
      threads: 1
"""
    with open(PROFILES_DIR / "profiles.yml", "w") as f:
        f.write(profiles_content)
    return True

def run_dbt_docs():
    """Runs dbt docs generate to populate catalog.json."""
    print("Running dbt docs generate...")
    try:
        subprocess.run(
            ["dbt", "docs", "generate", "--project-dir", str(DBT_PROJECT_DIR)],
            check=True,
            capture_output=True
        )
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error running dbt docs generate: {e.stderr.decode()}")
        return False

def get_manifest_and_catalog():
    """Loads manifest and catalog JSONs."""
    manifest_path = DBT_PROJECT_DIR / "target" / "manifest.json"
    catalog_path = DBT_PROJECT_DIR / "target" / "catalog.json"

    # Ensure manifest exists (try parse if not)
    if not manifest_path.exists():
        print("Manifest missing, running dbt parse...")
        subprocess.run(["dbt", "parse", "--project-dir", str(DBT_PROJECT_DIR)], check=False)

    if not manifest_path.exists():
        print("Manifest not found.")
        return None, None

    with open(manifest_path) as f:
        manifest = json.load(f)

    catalog = {}
    if catalog_path.exists():
        with open(catalog_path) as f:
            catalog = json.load(f)
    else:
        print("Catalog not found (dbt docs generate did not run or failed). proceeding with manifest only.")

    return manifest, catalog

def generate_description(model_name, column_name, context=None):
    """Generates a description using OpenAI if available."""
    if not openai or not os.environ.get("OPENAI_API_KEY"):
        return "TODO: Add description"

    prompt = f"Write a short, clear description for the column '{column_name}' in the table '{model_name}'."
    if context:
        prompt += f" Context: {context}"

    try:
        client = openai.OpenAI()
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a data analyst documenting database schemas."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=50
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"Error calling OpenAI: {e}")
        return "TODO: Add description"

def update_properties(manifest, catalog):
    """Updates properties.yml files."""
    yaml = YAML()
    yaml.preserve_quotes = True
    yaml.indent(mapping=2, sequence=4, offset=2)

    for node_name, node in manifest['nodes'].items():
        if node['resource_type'] != 'model':
            continue

        model_name = node['name']
        original_file_path = Path(node['original_file_path'])

        # dbt parse returns original_file_path relative to project root (e.g. models/silver/my_model.sql)
        # We need to find where the properties file should be.
        model_dir = DBT_PROJECT_DIR / original_file_path.parent

        # Look for existing properties file that contains this model
        properties_file = None

        # First scan existing YMLs in the folder
        potential_files = list(model_dir.glob("*.yml"))
        for f in potential_files:
            try:
                # We do a quick check to see if model is already defined here
                # Loading everything is safer
                with open(f) as yf:
                    data = yaml.load(yf)
                    if data and 'models' in data:
                        for m in data['models']:
                            if m['name'] == model_name:
                                properties_file = f
                                break
            except Exception:
                continue
            if properties_file:
                break

        # If not found, use _schema.yml (create if needed)
        if not properties_file:
            properties_file = model_dir / "_schema.yml"

        # Load existing YAML
        data = {'version': 2, 'models': []}
        if properties_file.exists():
            with open(properties_file) as f:
                try:
                    loaded = yaml.load(f)
                    if loaded:
                        data = loaded
                except Exception as e:
                    print(f"Error loading {properties_file}: {e}")
                    continue

        # Find the model entry
        model_entry = None
        if 'models' not in data:
            data['models'] = []

        for m in data['models']:
            if m['name'] == model_name:
                model_entry = m
                break

        if not model_entry:
            model_entry = {'name': model_name, 'description': "TODO: Add model description", 'columns': []}
            data['models'].append(model_entry)
            print(f"Adding model {model_name} to {properties_file}")

        # Get columns from Catalog (DB)
        db_columns = {}
        if catalog and node_name in catalog.get('nodes', {}):
            db_columns = catalog['nodes'][node_name]['columns']

        # Helper to find column in YAML
        def find_col(cols, name):
            for c in cols:
                if c['name'] == name:
                    return c
            return None

        # Existing columns in YAML
        existing_cols = model_entry.get('columns', [])
        if existing_cols is None:
            existing_cols = []
            model_entry['columns'] = existing_cols

        # Add columns found in DB (Catalog)
        if db_columns:
            for col_name, col_meta in db_columns.items():
                existing = find_col(existing_cols, col_name)
                if not existing:
                    desc = generate_description(model_name, col_name, col_meta.get('type'))
                    new_col = {'name': col_name, 'description': desc}
                    existing_cols.append(new_col)
                    print(f"Added column {col_name} to {model_name}")
        else:
             # If no catalog (e.g. model not in DB yet), we can't discover columns unless we parse SQL.
             # dbt parse doesn't give columns unless they are already in config/yaml.
             pass

        # Save back
        with open(properties_file, 'w') as f:
            yaml.dump(data, f)

import shutil

if __name__ == "__main__":
    dbt_path = shutil.which("dbt")
    print(f"DEBUG: dbt found at {dbt_path}")
    if dbt_path:
        subprocess.run(["dbt", "--version"], check=False)
    else:
        print("WARNING: dbt not found in PATH. 'dbt docs generate' will fail.")

    if setup_profile():
        run_dbt_docs()

    manifest, catalog = get_manifest_and_catalog()
    if manifest:
        update_properties(manifest, catalog)
    else:
        print("Failed to load manifest.")
        sys.exit(1)
