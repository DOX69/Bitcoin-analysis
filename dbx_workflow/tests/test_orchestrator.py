import importlib
import json
import os
from pathlib import Path
import subprocess
import sys

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
        "--exclude",
        "tag:fixture",
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


@pytest.mark.parametrize(
    "test_name",
    [
        "parity_currency_rates.sql",
        "parity_daily_btc.sql",
        "parity_gold_ohlc.sql",
    ],
)
def test_fixture_parity_tests_are_tagged(test_name):
    repository_root = Path(__file__).parents[2]
    contents = (repository_root / "dbt_silver_gold" / "tests" / test_name).read_text()

    assert "{{ config(tags=['fixture']) }}" in contents


@pytest.mark.parametrize("failed_stage", [None, "market", "dbt", "forecast"])
@pytest.mark.parametrize("backup_fails", [False, True])
def test_backup_runs_under_lock_despite_pipeline_failures(
    database_url, failed_stage, backup_fails, caplog
):
    from raw_ingest import orchestrator

    events = []

    def stage(name):
        def run(*args):
            events.append(name)
            if failed_stage == name:
                raise RuntimeError("stage failed")

        return run

    def backup():
        events.append("backup")
        with psycopg.connect(database_url, autocommit=True) as competitor:
            assert not competitor.execute(
                "SELECT pg_try_advisory_lock(%s)", (orchestrator.LOCK_KEY,)
            ).fetchone()[0]
        if backup_fails:
            raise RuntimeError("postgresql://secret-password@private")
        return {"status": "completed"}

    code = orchestrator.run_pipeline(
        database_url,
        run_id="backup-test",
        market_ingestor=stage("market"),
        indicator_ingestor=stage("indicators"),
        dbt_runner=stage("dbt"),
        forecast_runner=stage("forecast"),
        backup_runner=backup,
    )
    assert events[-1] == "backup"
    assert events.count("backup") == 1
    assert code == int(failed_stage in ("market", "dbt"))
    assert "secret-password" not in caplog.text
    if backup_fails:
        assert "Forecast backup failed" in caplog.text


def test_backup_disabled_without_configuration(monkeypatch):
    from raw_ingest import orchestrator

    monkeypatch.delenv("FORECAST_BACKUP_CONFIG", raising=False)
    assert orchestrator.run_forecast_backup() == {"status": "disabled"}


def test_backup_supervisor_bounds_worker_and_does_not_log_raw_output(
    monkeypatch, tmp_path, caplog
):
    from raw_ingest import orchestrator
    from forecast import pipeline

    calls = []
    config = str(tmp_path / "backup.json")
    monkeypatch.setenv("FORECAST_BACKUP_CONFIG", config)

    def supervise(command, log_path, **limits):
        calls.append((command, limits))
        log_path.write_text(
            json.dumps(
                {
                    "manifest_key": "development/backups/20260909/manifest.json",
                    "bytes": 120,
                    "seconds": 0.5,
                    "debug": "secret-password",
                }
            )
        )
        return {"wall_seconds": 1, "peak_rss_bytes": 1024}

    monkeypatch.setattr(pipeline, "supervise", supervise)
    result = orchestrator.run_forecast_backup()
    assert result == {
        "status": "completed",
        "wall_seconds": 1,
        "peak_rss_bytes": 1024,
        "manifest_key": "development/backups/20260909/manifest.json",
        "bytes": 120,
        "seconds": 0.5,
    }
    assert calls[0][0][-3:] == ["backup", "--config", config]
    assert calls[0][1] == {"seconds": 300, "rss_bytes": 4 * 1024**3}
    assert "--no-sync" in calls[0][0]
    assert "secret-password" not in caplog.text


@pytest.mark.parametrize(
    "output",
    [
        "secret-password: invalid JSON",
        '{"manifest_key":"secret-password\\nforged","bytes":1,"seconds":0}',
        '{"manifest_key":"development/manifest.json","bytes":-1,"seconds":0}',
        '{"manifest_key":"development/manifest.json","bytes":1,"seconds":NaN}',
    ],
)
def test_backup_rejects_invalid_report_without_logging_worker_text(
    monkeypatch, tmp_path, caplog, output
):
    from raw_ingest import orchestrator
    from forecast import pipeline

    monkeypatch.setenv("FORECAST_BACKUP_CONFIG", str(tmp_path / "backup.json"))

    def supervise(command, log_path, **limits):
        log_path.write_text(output)
        return {"wall_seconds": 1, "peak_rss_bytes": 1024}

    monkeypatch.setattr(pipeline, "supervise", supervise)
    with pytest.raises((ValueError, TypeError)):
        orchestrator.run_forecast_backup()
    assert "secret-password" not in caplog.text


def test_backup_config_preserves_forecast_dependencies_during_dbt(monkeypatch):
    from raw_ingest import orchestrator

    monkeypatch.delenv("FORECAST_JOB_CONFIG", raising=False)
    monkeypatch.setenv("FORECAST_BACKUP_CONFIG", "/config/backup.json")
    monkeypatch.setenv("DBT_TARGET_SCHEMA", "validation")
    calls = []
    monkeypatch.setattr(
        orchestrator.subprocess, "run", lambda command, **kwargs: calls.append(command)
    )
    orchestrator.run_dbt_build("postgresql://postgres@localhost/test")
    assert "--no-sync" in calls[0]


@pytest.mark.parametrize("level, visible", [(None, True), ("WARNING", False)])
def test_main_configures_backup_status_logging_in_fresh_process(level, visible):
    environment = os.environ.copy()
    environment.pop("LOG_LEVEL", None)
    environment["DATABASE_URL"] = "unused-by-test"
    if level is not None:
        environment["LOG_LEVEL"] = level
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            "from raw_ingest import orchestrator as o; "
            "o.run_pipeline = lambda *a, **k: "
            "o.logger.info('Forecast backup status: completed') or 0; o.main()",
        ],
        env=environment,
        capture_output=True,
        text=True,
        check=True,
    )
    assert ("Forecast backup status: completed" in result.stderr) is visible
