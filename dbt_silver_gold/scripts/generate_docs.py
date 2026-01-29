import os
import glob
from pathlib import Path
import json
from ruamel.yaml import YAML
from openai import OpenAI

# Initialize YAML
yaml = YAML()
yaml.preserve_quotes = True
yaml.indent(mapping=2, sequence=4, offset=2)
# Ensure flow style is block for collections
yaml.default_flow_style = False

def get_openai_client():
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        print("Warning: OPENAI_API_KEY not set. Skipping generation.")
        return None
    return OpenAI(api_key=api_key)

def generate_docs(client, sql_content, model_name):
    if not client:
        return None

    prompt = f"""
    You are a data documentation assistant. Analyze the following dbt SQL model named '{model_name}' and provide a documentation description for the table and its columns.

    Output strictly valid JSON in the following format:
    {{
        "description": "Description of the table",
        "columns": [
            {{ "name": "column_name", "description": "Description of the column" }}
        ]
    }}

    SQL Code:
    {sql_content}
    """

    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "system", "content": "You are a helpful data assistant."},
                      {"role": "user", "content": prompt}],
            response_format={"type": "json_object"}
        )
        content = response.choices[0].message.content
        return json.loads(content)
    except Exception as e:
        print(f"Error generating docs for {model_name}: {e}")
        return None

def process_model(file_path, client):
    model_name = file_path.stem
    print(f"Processing {model_name}...")

    # Read SQL
    with open(file_path, "r") as f:
        sql_content = f.read()

    # Find properties.yml
    folder = file_path.parent
    yml_files = list(folder.glob("*.yml"))

    target_yml = None
    existing_data = None
    found_in_file = None

    # 1. Look for existing model entry in any yaml file in the folder
    for yml_file in yml_files:
        try:
            with open(yml_file, "r") as f:
                data = yaml.load(f)
                if data and "models" in data:
                    for m in data["models"]:
                        if m["name"] == model_name:
                            found_in_file = yml_file
                            target_yml = yml_file
                            existing_data = data
                            break
        except Exception:
            pass
        if found_in_file:
            break

    # 2. If not found, use properties.yml or create it
    if not target_yml:
        target_yml = folder / "properties.yml"
        if target_yml.exists():
            with open(target_yml, "r") as f:
                existing_data = yaml.load(f) or {}
        else:
            existing_data = {"version": 2, "models": []}

    if "models" not in existing_data:
        existing_data["models"] = []

    # Find model entry
    model_entry = next((m for m in existing_data["models"] if m["name"] == model_name), None)

    # Check if we need to generate docs
    # Logic: If model missing, OR description missing, OR columns likely missing (naive check)
    needs_generation = False

    if not model_entry:
        needs_generation = True
    elif not model_entry.get("description"):
        needs_generation = True

    # If we have a client and detect potential work, verify with generated data
    if client and (needs_generation or (model_entry and "columns" not in model_entry)):
        print(f"Generating docs for {model_name}...")
        generated = generate_docs(client, sql_content, model_name)

        if generated:
            if not model_entry:
                model_entry = {"name": model_name}
                existing_data["models"].append(model_entry)

            # Update Table Description
            if not model_entry.get("description"):
                model_entry["description"] = generated.get("description", "")

            # Update Columns
            existing_cols = {c["name"]: c for c in model_entry.get("columns", [])}
            new_columns_list = model_entry.get("columns", [])

            # If no columns exist yet, initialize list
            if model_entry.get("columns") is None:
                new_columns_list = []
                model_entry["columns"] = new_columns_list

            for gen_col in generated.get("columns", []):
                col_name = gen_col["name"]
                if col_name not in existing_cols:
                    new_columns_list.append({
                        "name": col_name,
                        "description": gen_col["description"]
                    })
                elif not existing_cols[col_name].get("description"):
                     existing_cols[col_name]["description"] = gen_col["description"]

            # Write back
            print(f"Updating {target_yml}...")
            with open(target_yml, "w") as f:
                yaml.dump(existing_data, f)

def main():
    # Run from the dbt_silver_gold directory
    root_dir = Path("models")
    if not root_dir.exists():
        print("Error: 'models' directory not found. Please run this script from the dbt project root.")
        return

    client = get_openai_client()

    for sql_file in root_dir.rglob("*.sql"):
        process_model(sql_file, client)

if __name__ == "__main__":
    main()
