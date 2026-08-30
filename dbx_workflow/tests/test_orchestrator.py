import importlib
from pathlib import Path

import psycopg
import pytest
import requests


def test_pipeline_holds_lock_runs_in_order_and_releases_it(database_url):
    orchestrator = importlib.import_module("raw_ingest.orchestrator")
    events = []

    def ingest_market(connection, run_id):
        with psycopg.connect(database_url, autocommit=True) as competitor:
            with competitor.cursor() as cursor:
                cursor.execute(
                    "SELECT pg_try_advisory_lock(%s)", (orchestrator.LOCK_KEY,)
                )
                assert cursor.fetchone()[0] is False
        events.append(("market", run_id))

    def ingest_indicators(connection, run_id):
        events.append(("indicators", run_id))

    def run_dbt(database_url_arg):
        assert database_url_arg == database_url
        events.append(("dbt", None))

    exit_code = orchestrator.run_pipeline(
        database_url,
        run_id="pipeline-run",
        market_ingestor=ingest_market,
        indicator_ingestor=ingest_indicators,
        dbt_runner=run_dbt,
    )

    with psycopg.connect(database_url, autocommit=True) as competitor:
        with competitor.cursor() as cursor:
            cursor.execute(
                "SELECT pg_try_advisory_lock(%s)", (orchestrator.LOCK_KEY,)
            )
            lock_is_available = cursor.fetchone()[0]
            cursor.execute("SELECT pg_advisory_unlock(%s)", (orchestrator.LOCK_KEY,))

    assert exit_code == 0
    assert events == [
        ("market", "pipeline-run"),
        ("indicators", "pipeline-run"),
        ("dbt", None),
    ]
    assert lock_is_available is True


def test_pipeline_returns_nonzero_skips_dbt_and_unlocks_after_ingestion_failure(
    database_url,
):
    orchestrator = importlib.import_module("raw_ingest.orchestrator")
    dbt_calls = []

    def fail_indicators(connection, run_id):
        raise RuntimeError("indicator ingestion failed")

    exit_code = orchestrator.run_pipeline(
        database_url,
        run_id="failed-run",
        market_ingestor=lambda connection, run_id: None,
        indicator_ingestor=fail_indicators,
        dbt_runner=lambda database_url_arg: dbt_calls.append(database_url_arg),
    )

    with psycopg.connect(database_url, autocommit=True) as competitor:
        with competitor.cursor() as cursor:
            cursor.execute(
                "SELECT pg_try_advisory_lock(%s)", (orchestrator.LOCK_KEY,)
            )
            lock_is_available = cursor.fetchone()[0]
            cursor.execute("SELECT pg_advisory_unlock(%s)", (orchestrator.LOCK_KEY,))

    assert exit_code == 1
    assert dbt_calls == []
    assert lock_is_available is True


@pytest.mark.parametrize("failed_stage", ["market", "indicators"])
@pytest.mark.parametrize(
    "failure",
    [
        requests.exceptions.HTTPError("503 Server Error"),
        requests.exceptions.Timeout("Request timed out"),
        requests.exceptions.ConnectionError("Network unavailable"),
        ValueError("Invalid payload"),
    ],
)
def test_http_ingestion_failures_return_one_and_skip_dbt(
    database_url, failed_stage, failure
):
    orchestrator = importlib.import_module("raw_ingest.orchestrator")
    dbt_calls = []

    def fail(connection, run_id):
        raise failure

    exit_code = orchestrator.run_pipeline(
        database_url,
        run_id="failed-http-run",
        market_ingestor=fail if failed_stage == "market" else lambda *args: None,
        indicator_ingestor=(
            fail if failed_stage == "indicators" else lambda *args: None
        ),
        dbt_runner=lambda database_url_arg: dbt_calls.append(database_url_arg),
    )

    assert exit_code == 1
    assert dbt_calls == []


def test_dbt_runner_uses_root_context_and_database_url_pg_variables(monkeypatch):
    orchestrator = importlib.import_module("raw_ingest.orchestrator")
    calls = []

    def record_run(command, *, check, cwd, env):
        calls.append((command, check, cwd, env))

    monkeypatch.setenv("DBT_TARGET_SCHEMA", "silver_test")
    monkeypatch.setattr(orchestrator.subprocess, "run", record_run)

    orchestrator.run_dbt_build(
        "postgresql://ingestor:p%40ss@db.internal:5433/bitcoin?sslmode=require"
    )

    command, check, cwd, env = calls[0]
    assert command == [
        "uv",
        "run",
        "--locked",
        "--project",
        "dbx_workflow",
        "dbt",
        "build",
        "--project-dir",
        "dbt_silver_gold",
        "--profiles-dir",
        "dbt_silver_gold",
    ]
    assert check is True
    assert cwd == Path(__file__).parents[2]
    assert {
        key: env[key]
        for key in (
            "PGHOST",
            "PGPORT",
            "PGUSER",
            "PGPASSWORD",
            "PGDATABASE",
            "PGSSLMODE",
            "DBT_TARGET_SCHEMA",
        )
    } == {
        "PGHOST": "db.internal",
        "PGPORT": "5433",
        "PGUSER": "ingestor",
        "PGPASSWORD": "p@ss",
        "PGDATABASE": "bitcoin",
        "PGSSLMODE": "require",
        "DBT_TARGET_SCHEMA": "silver_test",
    }
