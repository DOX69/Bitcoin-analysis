---
description: How to add a new raw bronze delta table from an external API (Raw Ingest)
---

# Workflow: Adding a New Raw Bronze Delta Table

This workflow guides you through implementing a new data ingestion pipeline (bronze layer) from an external API into Databricks Delta tables.

It adheres to strict project constraints, including immutable **Test-Driven Development (TDD)**, systematic debugging, validation-before-completion, and Databricks entrypoint conventions.

## 0. Prerequisites & Branching

Before writing any code, establish a clean workspace and define your naming conventions.

**Agent Skill Management (CRITICAL)**
- Use `aph list`, `aph search`, and `aph add` to find and install skills. `aph` is NOT for executing skills.
- After installing a skill, always read its `.agent/skills/<skill_name>/SKILL.md` file to understand how to use it.
- For GitHub operations, you also have access to the built-in GitHub MCP Server.

1. **Naming Convention Check:**
   - Table name MUST follow the format: `{source}_{data_type}` (e.g., `bgeometrics_btc_technical_indicators`, `coinbase_btc_usd_ohlcv`).
   - Determine the source abbreviation and what the data represents.

2. **Git Branching:**
   - **CRITICAL:** Before creating a side branch, you MUST fetch the latest changes from the default integration branch (`main` or `staging`) so that your branch has a clean, up-to-date base and avoids mixing unrelated commits into your Pull Request. 
     ```bash
     git checkout staging # Or main, depending on target
     git pull
     git checkout -b feature/add-{source}-{table_name}
     ```
     *(Example: `git checkout -b feature/add-bgeometrics-btc-technical-indicators`)*

3. **Activate Environment:**
   - Ensure the virtual environment is active:
     ```bash
     source .venv/bin/activate  # On Linux/Mac
     # OR
     .\.venv\Scripts\activate   # On Windows
     ```

## 1. Schema Drift Detection (Mandatory)

Every new API source MUST have a Pydantic model generated for schema drift detection.

1. Add a sample data fetch function for your new API in `dbx_workflow/scripts/check_api_schemas.py`.
2. Generate the Pydantic model using `datamodel-code-generator` within the script.
3. Run the script:
   ```bash
   cd dbx_workflow
   uv run python scripts/check_api_schemas.py
   ```
4. Verify the new model exists in `dbx_workflow/src/raw_ingest/api_models/`.

## 2. Test-Driven Development (TDD) - RED Phase

Write failing tests BEFORE writing the implementation.

1. **Mock Fixture:** Add a sample API response mock fixture (e.g., `mock_{source}_api_response`) in `dbx_workflow/tests/conftest.py`.
2. **Fetcher Tests:** Create `test_{source}_fetcher.py` in `dbx_workflow/tests/`.
   - Test `__init__`: Verify attributes, correct table name convention, and dev/prod catalog variants.
   - Test `fetch_historical_data`:
     - Full history fetch correctly queries API APIs.
     - Incremental fetch correctly uses date parameters.
     - API Error/Timeout handling (`requests.exceptions.RequestException`).
     - Empty response handling returns empty DataFrame.
     - **CRITICAL:** Ensure raw API columns are preserved exactly as they are without renaming or casting types.
     - **Mock Logger:** Use a `mock_logger` fixture to verify logging behavior in both Fetcher and Entry Point tests.
     - **Mock Spark Session:** In entry point tests, use a complete `MagicMock` for the `SparkSession` rather than the real session to avoid side effects and allow precise control over `spark.read.table` behavior.
3. **Entry Point Tests:** Create `test_ingest_{new_task}.py` testing:
   - Behavior on first run (full history).
   - Behavior when table exists (incremental).
   - Error handling.
4. **Run Tests to watch them FAIL (RED):**
   ```bash
   cd dbx_workflow
   uv run pytest -v
   ```

## 3. Implementation - GREEN Phase

Write the minimal code necessary to make the tests pass.

1. **Concrete Fetcher:** Create `{Source}Fetcher.py` in `dbx_workflow/src/raw_ingest/`.
   - Extend `BaseFetcher` and match its `__init__(self, logger, ticker, currency, catalog, schema, base_url)` signature EXACTLY. 
   - Use `self.logger` for all internal logging (passed from the entry point). Do NOT use a global logger if not already defined in the project.
   - Set `self.table_name` following the `{source}_{data_type}` convention.
   - **CRITICAL:** Return the `pandas DataFrame` EXACTLY as received from the API. Do not rename columns (even time/date columns) and do not cast schema types. The bronze layer stores data raw.
   - **Partitioning:** If the dataset is small or doesn't support date filters, implement a full fetch. However, for `DbWriter` partitioning to work, you MUST ensure the DataFrame has a `time` column (casted from a native timestamp/date field like `created` or `updated`).
2. **Entry Point:** Unless explicitly requested to augment an existing loop (like `ingest_market_price_data.py`), create a **NEW separate entry point** (e.g., `ingest_{new_task}.py`).
   - Use `argparse` to parse `--catalog` and `--schema`.
   - Call the new fetcher, query Databricks for the latest date, and pass data to `DbWriter`.
   - **CRITICAL:** Explicitly expose your new entry point inside `dbx_workflow/src/raw_ingest/__init__.py` (e.g., `from .ingest_{new_task} import main as ingest_{new_task}`). Overlooking this leads to `AttributeError` on Databricks when the PySpark wheel task dynamically imports it.

## 4. Configuration Updates

Wire the new entry point into the project execution and orchestration configurations.

1. **`pyproject.toml`:** Register the new entry point under `[project.scripts]`.
   ```toml
   [project.scripts]
   ingest_{new_task} = "raw_ingest.ingest_{new_task}:main"
   ```
2. **`master_orchestrator_job.yml`:**
   - Add a new `python_wheel_task` running in parallel to existing raw ingest tasks.
   - Specify the exact `entry_point` matching your `pyproject.toml`.
   - **CRITICAL:** Update downstream tasks (like `dbt_silver_gold`) `depends_on` list to include your new raw ingest task. Overlooking this breaks pipeline orchestration.

## 5. Verification Before Completion

Do NOT claim the task is complete without running verification.

1. **Run Local Tests:** Ensure the entire suite passes.
   ```bash
   cd dbx_workflow
   uv run pytest -v
   ```
2. **Bundle Verification:** Validate the Databricks configuration.
   ```bash
   databricks bundle validate -t dev -p DEFAULT
   ```
3. **Run Full Project Verification:** Validate entire repository health.
   ```bash
   ./check-all
   ```
4. **Deploy and Run on Databricks:**
   ```bash
   databricks bundle deploy -t dev -p DEFAULT
   databricks bundle run -t dev -p DEFAULT master_orchestrator_job --only raw_ingest_{new_task}
   ```
5. Only state the work is complete if ALL the above exit with `0` failures/errors and the Databricks run succeeds.

## 6. Git Commit and Push & CI/CD Verification

Use the `git-pushing` skill or the built-in GitHub MCP Server to commit and push changes cleanly.

1. If using the `git-pushing` skill, run the smart commit script with a conventional commit message:
   ```bash
   bash .agent/skills/git-pushing/scripts/smart_commit.sh "feat: add {source} raw bronze table pipeline"
   ```
2. Alternatively, use your built-in GitHub MCP tools to stage, commit, and push.
3. Verify changes are pushed to your remote branch.
4. **CRITICAL:** You MUST wait for and verify that the GitHub Actions CI/CD pipeline (e.g., "CI/CD Pipeline / Backend Tests") passes perfectly for your newly pushed side branch.
   - Use the `mcp_github-mcp-server_pull_request_read` tool or check GitHub directly. Do NOT conclude the task until these checks pass.

## Troubleshooting & Debugging

If tests fail or integrations error out, aggressively apply the **Systematic Debugging** skill:
- NO random fixes. Iterate systematically until all tests and runs succeed.
- Read full stack traces and error messages.
- Formulate ONE hypothesis at a time.
- Make ONE minimal change and test immediately.
- **NEVER CHANGE A TEST** simply to make it pass. Tests act as the ultimate source of truth. Any modification to existing test logic MUST be explicitly justified and approved by the user first.
- If 3+ fixes fail to resolve the issue, STOP and question the architectural assumptions. Do not keep layering patches.

### Common Databricks Errors
- **`AttributeError: module 'raw_ingest' has no attribute...`**: PySpark's wheel task dynamically imports the exact module name mapped in `pyproject.toml`. You MUST explicitly expose these entry points inside `dbx_workflow/src/raw_ingest/__init__.py`.
- **`_LEGACY_ERROR_TEMP_DELTA_0007` (Schema Mismatch)**: When writing to a newly created Bronze delta table or when the API schema evolves, Databricks natively raises this error. Ensure `DbWriter.py` append mode utilizes `.option("mergeSchema", "true")`.

## 7. Final Completion Checklist

Before considering this feature complete, verify every single point below:

- [ ] Pydantic schema generated and exists in `api_models/`
- [ ] Mocks created in `conftest.py`
- [ ] Fetcher tests written and passing (init, historical, incremental, errors, edge cases)
- [ ] Fetcher implemented and preserves raw columns exactly without schema casting
- [ ] Entry point tests written and passing
- [ ] Entry point implemented and retrieves arguments properly
- [ ] Entry point explicitly exposed in `src/raw_ingest/__init__.py`
- [ ] Entry point registered in `pyproject.toml`
- [ ] Parallel task added to `master_orchestrator_job.yml`
- [ ] Downstream (e.g., `dbt_silver_gold`) dependencies updated in `master_orchestrator_job.yml`
- [ ] Local tests (`uv run pytest -v`) pass with `0` failures
- [ ] Repository health (`./check-all`) passes with `0` errors
- [ ] Databricks deploy & run (`databricks bundle run`) succeeds
- [ ] All changes committed and pushed to `feature/add-{source}-{table_name}` branch
- [ ] GitHub Actions CI/CD pipeline for the pushed branch verifies perfectly (wait for the result)

If any box remains unchecked, the feature is **NOT** complete. Go back and finish the missing step.
