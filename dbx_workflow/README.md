# master_orchestrator_job

The 'master_orchestrator_job' project defines the Data Ingestion pipeline for crypto price data and technical indicators into the Delta Lake Bronze layer.

* `src/`: Python source code for data fetchers (`CoinbaseFetcher`, `FrankfurterFetcher`, `BGeometricsFetcher`) and Databricks entry points.
* `scripts/`: Utilities such as `check_api_schemas.py` for API schema drift monitoring.
* `resources/`: Resource configurations (jobs, pipelines, etc.), including `master_orchestrator_job.yml` which defines parallel tasks `raw_ingest_crypto` and `raw_ingest_technical_indicators`.
* `api_models/`: Auto-generated Pydantic schemas tracking third-party API configurations.
* `tests/`: Unit tests and mocks for local TDD verification.
* `fixtures/`: Fixtures for data sets (primarily used for testing).


## Getting started

Choose how you want to work on this project:

(a) Directly in your Databricks workspace, see
    https://docs.databricks.com/dev-tools/bundles/workspace.

(b) Locally with an IDE like Cursor or VS Code, see
    https://docs.databricks.com/dev-tools/vscode-ext.html.

(c) With command line tools, see https://docs.databricks.com/dev-tools/cli/databricks-cli.html

If you're developing with an IDE, dependencies for this project should be installed using uv:

*  Make sure you have the UV package manager installed.
   It's an alternative to tools like pip: https://docs.astral.sh/uv/getting-started/installation/.
*  Run `uv sync --dev` to install the project's dependencies.


# Using this project using the CLI

The Databricks workspace and IDE extensions provide a graphical interface for working
with this project. It's also possible to interact with it directly using the CLI:

1. Authenticate to your Databricks workspace, if you have not done so already:
    ```
    $ databricks configure
    ```

2. To deploy a development copy of this project, type:
    ```
    $ databricks bundle deploy --target dev
    ```
    (Note that "dev" is the default target, so the `--target` parameter
    is optional here.)

    This deploys everything that's defined for this project.
    You can find that resource by opening your workspace and clicking on **Jobs & Pipelines**.
    The primary job is `master_orchestrator_job` which concurrently runs:
    - `raw_ingest_crypto`
    - `raw_ingest_technical_indicators`

3. Similarly, to deploy a production copy, type:
   ```
   $ databricks bundle deploy --target prod
   ```
   Note the default template has a includes a job that runs the pipeline every day
   (defined in resources/sample_job.job.yml). The schedule
   is paused when deploying in development mode (see
   https://docs.databricks.com/dev-tools/bundles/deployment-modes.html).

## Troubleshooting: Databricks `python_wheel_task` Configuration

If you see an error like this during a Databricks Job run:

```text
AttributeError: module 'raw_ingest' has no attribute 'ingest_market_price_data'
---------------------------------------------------------------------------
AttributeError                            Traceback (most recent call last)
File ~/.ipykernel/3789/command--1-2525349055:23
     21 import importlib
     22 module = importlib.import_module("raw_ingest")
---> 23 module.ingest_market_price_data()

AttributeError: module 'raw_ingest' has no attribute 'ingest_market_price_data'
Workload failed, see run output for details
```

**Why it happens:**
Databricks `python_wheel_task` uses the `entry_point` specified in `master_orchestrator_job.yml` differently than standard Python CLI scripts mapped in `pyproject.toml`. 
Behind the scenes, Databricks generates a runner script that imports your root package (`import raw_ingest`) and attempts to call a function on it with the exact name of the `entry_point` (e.g., `raw_ingest.ingest_market_price_data()`).
If the root `__init__.py` file of your package does not explicitly expose this function, the `AttributeError` is raised.

**How to resolve:**
Ensure that your entry point functions are imported into the root `__init__.py` file of the `src/raw_ingest` package:

```python
# src/raw_ingest/__init__.py
from .ingest_market_price_data import main as ingest_market_price_data
from .ingest_technical_indicators import main as ingest_technical_indicators
```

4. To run a job or pipeline, use the "run" command:
   ```
   $ databricks bundle run
   ```

5.### Run unit tests

To run unit tests, ensure you have initialized your Python environment from the repository root:
```sh
uv sync
```

Then, from the root or within this directory, run the tests using:
```sh
uv run pytest
```
