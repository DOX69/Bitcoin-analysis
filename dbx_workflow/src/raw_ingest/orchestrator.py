import logging
import os
from pathlib import Path
import subprocess
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
    subprocess.run(
        DBT_COMMAND,
        check=True,
        cwd=REPOSITORY_ROOT,
        env=_dbt_environment(database_url),
    )


def run_pipeline(
    database_url,
    *,
    run_id,
    market_ingestor=ingest_market_data,
    indicator_ingestor=ingest_technical_indicators,
    dbt_runner=run_dbt_build,
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
            return 0
        except Exception:
            logger.exception("Ingestion pipeline failed")
            return 1
        finally:
            with connection.cursor() as cursor:
                cursor.execute("SELECT pg_advisory_unlock(%s)", (LOCK_KEY,))


def main():
    exit_code = run_pipeline(
        os.environ["DATABASE_URL"],
        run_id=str(uuid4()),
    )
    raise SystemExit(exit_code)


if __name__ == "__main__":
    main()
