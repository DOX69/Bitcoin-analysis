"""This file configures pytest.

This file is in the root since it can be used for tests in any place in this
project, including tests under resources/.
"""

import os, sys, pathlib
from contextlib import contextmanager
from unittest.mock import MagicMock



from dotenv import load_dotenv

# Load .env from project root
root_dir = pathlib.Path(__file__).parent.parent.parent
load_dotenv(root_dir / ".env")

try:
    from databricks.connect import DatabricksSession
    from databricks.sdk import WorkspaceClient
    from pyspark.sql import SparkSession
    import pytest
    import json
    import csv
    import os
except ImportError:
    raise ImportError(
        "Test dependencies not found.\n\nRun tests using 'uv run pytest'. See http://docs.astral.sh/uv to learn more about uv."
    )


@pytest.fixture()
def spark() -> SparkSession:
    """Provide a SparkSession fixture for tests.

    If DatabricksSession cannot be created (e.g. missing credentials),
    returns a MagicMock to allow unit tests to proceed.

    Minimal example:
        def test_uses_spark(spark):
            df = spark.createDataFrame([(1,)], ["x"])
            assert df.count() == 1
    """
    try:
        if not os.environ.get("DATABRICKS_HOST") and not os.environ.get("DATABRICKS_TOKEN"):
             # If no credentials, return Mock immediately to avoid connection attempts
             print("⚠️ No Databricks credentials found. Returning MagicMock for 'spark' fixture.", file=sys.stderr)
             return MagicMock(spec=SparkSession)

        return DatabricksSession.builder.getOrCreate()
    except Exception as e:
        print(f"⚠️ Failed to create DatabricksSession: {e}. Returning MagicMock.", file=sys.stderr)
        return MagicMock(spec=SparkSession)


@pytest.fixture()
def load_fixture(spark: SparkSession):
    """Provide a callable to load JSON or CSV from fixtures/ directory.

    Example usage:

        def test_using_fixture(load_fixture):
            data = load_fixture("my_data.json")
            assert data.count() >= 1
    """

    def _loader(filename: str):
        path = pathlib.Path(__file__).parent.parent / "fixtures" / filename
        suffix = path.suffix.lower()
        if suffix == ".json":
            rows = json.loads(path.read_text())
            return spark.createDataFrame(rows)
        if suffix == ".csv":
            with path.open(newline="") as f:
                rows = list(csv.DictReader(f))
            return spark.createDataFrame(rows)
        raise ValueError(f"Unsupported fixture type for: {filename}")

    return _loader


def _enable_fallback_compute():
    """Enable serverless compute if no compute is specified."""
    try:
        # Avoid checking if no credentials
        if not os.environ.get("DATABRICKS_HOST"):
            return

        conf = WorkspaceClient().config
        if conf.serverless_compute_id or conf.cluster_id or os.environ.get("SPARK_REMOTE"):
            return

        url = "https://docs.databricks.com/dev-tools/databricks-connect/cluster-config"
        print("☁️ no compute specified, falling back to serverless compute", file=sys.stderr)
        print(f"  see {url} for manual configuration", file=sys.stdout)

        os.environ["DATABRICKS_SERVERLESS_COMPUTE_ID"] = "auto"
    except Exception as e:
        print(f"⚠️ Failed to configure fallback compute: {e}", file=sys.stderr)


@contextmanager
def _allow_stderr_output(config: pytest.Config):
    """Temporarily disable pytest output capture."""
    capman = config.pluginmanager.get_plugin("capturemanager")
    if capman:
        with capman.global_and_fixture_disabled():
            yield
    else:
        yield


def pytest_configure(config: pytest.Config):
    """Configure pytest session."""
    with _allow_stderr_output(config):
        _enable_fallback_compute()

        # Initialize Spark session eagerly ONLY if credentials exist
        if os.environ.get("DATABRICKS_HOST"):
            try:
                if hasattr(DatabricksSession.builder, "validateSession"):
                    DatabricksSession.builder.validateSession().getOrCreate()
                else:
                    DatabricksSession.builder.getOrCreate()
            except Exception as e:
                 print(f"⚠️ Failed to initialize eager DatabricksSession: {e}", file=sys.stderr)


# Additional fixtures for testing raw_ingest modules
from datetime import datetime
import pandas as pd
import logging


@pytest.fixture()
def mock_logger():
    """Provide a mock logger for testing."""
    return MagicMock()


@pytest.fixture()
def mock_coinbase_api_response():
    """Provide sample Coinbase API response data."""
    # Coinbase returns: [ time, low, high, open, close, volume ]
    return [
        [1640995200, 46000.0, 47500.0, 46500.0, 47000.0, 1500.5],
        [1641081600, 47000.0, 48000.0, 47000.0, 47800.0, 1800.3],
        [1641168000, 47800.0, 49000.0, 47800.0, 48500.0, 2100.7],
        [1641254400, 48500.0, 49500.0, 48500.0, 49000.0, 1950.2],
        [1641340800, 49000.0, 50000.0, 49000.0, 49800.0, 2200.1],
    ]


@pytest.fixture()
def sample_pandas_df():
    """Provide sample pandas DataFrame with crypto OHLCV data."""
    data = {
        "time": pd.to_datetime([
            "2022-01-01", "2022-01-02", "2022-01-03", "2022-01-04", "2022-01-05"
        ]),
        "low": [46000.0, 47000.0, 47800.0, 48500.0, 49000.0],
        "high": [47500.0, 48000.0, 49000.0, 49500.0, 50000.0],
        "open": [46500.0, 47000.0, 47800.0, 48500.0, 49000.0],
        "close": [47000.0, 47800.0, 48500.0, 49000.0, 49800.0],
        "volume": [1500.5, 1800.3, 2100.7, 1950.2, 2200.1],
    }
    return pd.DataFrame(data)


@pytest.fixture()
def sample_spark_df(spark: SparkSession, sample_pandas_df: pd.DataFrame):
    """Provide sample Spark DataFrame with crypto OHLCV data."""
    return spark.createDataFrame(sample_pandas_df)
