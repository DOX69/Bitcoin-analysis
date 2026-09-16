import logging
import json
import math
import os
from pathlib import Path
import subprocess
import tempfile
from urllib.parse import parse_qs, unquote, urlsplit
from uuid import uuid4

import psycopg

from raw_ingest.ingest_market_price_data import ingest_market_data
from raw_ingest.ingest_technical_indicators import ingest_technical_indicators


logger = logging.getLogger(__name__)
LOCK_KEY = 7_319_941_903_106_202_608
REPOSITORY_ROOT = Path(__file__).parents[3]
DBT_COMMAND = [
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


def _dbt_environment(database_url):
    parsed = urlsplit(database_url)
    query = parse_qs(parsed.query)
    environment = os.environ.copy()
    environment.update(
        {
            "PGHOST": parsed.hostname or "",
            "PGPORT": str(parsed.port or 5432),
            "PGUSER": unquote(parsed.username or ""),
            "PGPASSWORD": unquote(parsed.password or ""),
            "PGDATABASE": unquote(parsed.path.lstrip("/")),
            "DBT_TARGET_SCHEMA": os.environ["DBT_TARGET_SCHEMA"],
        }
    )
    if "sslmode" in query:
        environment["PGSSLMODE"] = query["sslmode"][0]
    return environment


def run_dbt_build(database_url):
    command = DBT_COMMAND
    if any(
        os.environ.get(name)
        for name in (
            "FORECAST_JOB_CONFIG",
            "FORECAST_BACKUP_CONFIG",
            "FORECAST_RESEARCH_CONFIG",
        )
    ):
        command = DBT_COMMAND[:2] + ["--no-sync"] + DBT_COMMAND[2:]
    subprocess.run(
        command,
        check=True,
        cwd=REPOSITORY_ROOT,
        env=_dbt_environment(database_url),
    )


def run_forecast():
    config = os.environ.get("FORECAST_JOB_CONFIG")
    if not config:
        return {"status": "disabled"}
    from forecast.pipeline import supervise

    # Deployment installs the forecast extra once. A cron never installs packages.
    command = [
        "uv",
        "--directory",
        str(REPOSITORY_ROOT),
        "run",
        "--locked",
        "--extra",
        "forecast",
        "--no-sync",
        "python",
        "-m",
        "forecast.jobs",
        "worker",
        "--config",
        config,
    ]
    with tempfile.TemporaryDirectory(prefix="forecast-job-") as directory:
        log_path = Path(directory) / "worker.log"
        try:
            result = supervise(command, log_path, seconds=300, rss_bytes=4 * 1024**3)
        finally:
            if log_path.exists():
                logger.info("Forecast worker: %s", log_path.read_text(encoding="utf-8"))
    return {"status": "completed", **result}


def run_forecast_research(*, daily=False):
    config = os.environ.get("FORECAST_RESEARCH_CONFIG")
    if not config:
        return {"status": "disabled"}
    from forecast.pipeline import supervise

    command = [
        "uv",
        "--directory",
        str(REPOSITORY_ROOT),
        "run",
        "--locked",
        "--extra",
        "forecast",
        "--no-sync",
        "python",
        "-m",
        "forecast.daily_cloud" if daily else "forecast.cloud_research",
        "--config",
        config,
    ]
    with tempfile.TemporaryDirectory(prefix="forecast-research-") as directory:
        log_path = Path(directory) / "worker.log"
        resources = supervise(command, log_path, seconds=300, rss_bytes=4 * 1024**3)
        report = json.loads(log_path.read_text(encoding="utf-8"))
        from forecast.backups import validate_key

        if report.get("report_key"):
            validate_key(report["report_key"])
    return {
        **resources,
        **{
            key: report[key]
            for key in (
                "status",
                "emissions",
                "mature_points",
                "report_key",
                "independent_copy_verified",
            )
            if key in report
        },
    }


def run_daily_forecast_research():
    return run_forecast_research(daily=True)


def run_forecast_backup():
    config = os.environ.get("FORECAST_BACKUP_CONFIG")
    if not config:
        return {"status": "disabled"}
    from forecast.pipeline import supervise
    from forecast.backups import validate_key

    command = [
        "uv",
        "--directory",
        str(REPOSITORY_ROOT),
        "run",
        "--locked",
        "--extra",
        "forecast",
        "--no-sync",
        "python",
        "-m",
        "forecast.backups",
        "backup",
        "--config",
        config,
    ]
    with tempfile.TemporaryDirectory(prefix="forecast-backup-") as directory:
        log_path = Path(directory) / "worker.log"
        result = supervise(command, log_path, seconds=300, rss_bytes=4 * 1024**3)
        report = json.loads(log_path.read_text(encoding="utf-8"))
        key, size, seconds = report["manifest_key"], report["bytes"], report["seconds"]
        validate_key(key)
        if (
            type(size) is not int
            or size < 0
            or type(seconds) not in (int, float)
            or not math.isfinite(seconds)
            or seconds < 0
        ):
            raise ValueError("Invalid backup report metrics")
    # Never forward arbitrary worker fields or diagnostic text to the ingestion log.
    return {
        "status": "completed",
        **result,
        "manifest_key": key,
        "bytes": size,
        "seconds": seconds,
    }


def run_pipeline(
    database_url,
    *,
    run_id,
    market_ingestor=ingest_market_data,
    indicator_ingestor=ingest_technical_indicators,
    dbt_runner=run_dbt_build,
    forecast_runner=run_forecast,
    backup_runner=run_forecast_backup,
    research_runner=run_forecast_research,
    daily_research_runner=run_daily_forecast_research,
):
    with psycopg.connect(database_url, autocommit=True) as connection:
        with connection.cursor() as cursor:
            cursor.execute("SELECT pg_try_advisory_lock(%s)", (LOCK_KEY,))
            if cursor.fetchone()[0] is False:
                logger.error("Another ingestion run holds the PostgreSQL lock")
                return 1

        try:
            market_ingestor(connection, run_id)
            indicator_ingestor(connection, run_id)
            dbt_runner(database_url)
            try:
                logger.info("Forecast status: %s", forecast_runner())
            except Exception:
                # Forecast failure never changes ingestion/dbt success or replays it.
                logger.error("Forecast failed; ingestion and dbt remain successful")
            try:
                logger.info("Forecast research status: %s", research_runner())
            except Exception:
                logger.error(
                    "Forecast research failed; ingestion and dbt remain successful"
                )
            try:
                logger.info(
                    "Daily forecast research status: %s", daily_research_runner()
                )
            except Exception:
                logger.error(
                    "Daily forecast research failed; ingestion and dbt remain successful"
                )
            return 0
        except Exception:
            logger.exception("Ingestion pipeline failed")
            return 1
        finally:
            try:
                logger.info("Forecast backup status: %s", backup_runner())
            except Exception:
                logger.error("Forecast backup failed; ingestion status unchanged")
            with connection.cursor() as cursor:
                cursor.execute("SELECT pg_advisory_unlock(%s)", (LOCK_KEY,))


def main():
    logging.basicConfig(
        level=os.environ.get("LOG_LEVEL", "INFO").upper(),
        format="%(levelname)s %(message)s",
    )
    exit_code = run_pipeline(
        os.environ["DATABASE_URL"],
        run_id=str(uuid4()),
    )
    raise SystemExit(exit_code)


if __name__ == "__main__":
    main()
