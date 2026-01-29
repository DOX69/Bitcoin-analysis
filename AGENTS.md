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

## Macro Documentation

**Goal:** Maintain clear documentation for reusable dbt macros.

**Instructions for Agents:**
If you create or modify a macro in the `macros/` directory:
1.  **Find or Create Schema File:** Look for a `schema.yml` (or `_macros.yml`) in the same directory as the macro. If it doesn't exist, create it.
2.  **Document the Macro:** Add an entry under `macros:` including:
    *   `name`: The name of the macro.
    *   `description`: What the macro does.
    *   `arguments`: A list of arguments with descriptions.

## Data Quality

**Goal:** Ensure data integrity through comprehensive testing.

**Instructions for Agents:**
1.  **Primary Keys:** Always add `unique` and `not_null` tests for primary keys (e.g., `date`, `id`).
2.  **Financial Data:** Apply `positive_value` tests to price, revenue, or cost columns.
3.  **Completeness:** Add `not_null` tests for critical columns (e.g., foreign keys, timestamps).
4.  **Ranges:** Use `percentage_range` (0-100) for ratios or indices like RSI.

**Note:** This replaces the need for automated scripts. Use your internal capabilities to generate high-quality, context-aware descriptions.
