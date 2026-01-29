# Agent Instructions

## Weekly dbt Documentation Maintenance

**Goal:** Ensure all dbt models have up-to-date documentation and metadata.

**Instructions for Agents:**
If you are working on this repository (specifically on Thursdays, or when asked to perform maintenance):

1.  **Scan for New Models:** Check the `dbt_silver_gold/models` directory for any SQL files that do not have a corresponding entry in a `properties.yml` file.
2.  **Generate Documentation:** For each undocumented model:
    *   Analyze the SQL logic to understand the table's purpose.
    *   Identify all columns and their data types/usage.
    *   Create or update the `properties.yml` file in the same directory.
    *   Add a clear description for the model.
    *   Add descriptions for all columns.
3.  **Update Existing Documentation:** If a model has changed (e.g., new columns added), update the `properties.yml` to reflect these changes.

**Note:** This replaces the need for automated scripts. Use your internal capabilities to generate high-quality, context-aware descriptions.
