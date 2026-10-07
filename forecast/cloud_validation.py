"""Opt-in bounded fixture run on Development; never uses the normal forecast DB."""

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import sys
import tempfile
import time

import psycopg
from psycopg import sql
from psycopg.conninfo import make_conninfo
import psutil

from forecast.development_validation import (
    database_snapshot,
    exercise,
    validate_database_name,
)
from forecast.pipeline import supervise


def worker(config, name, output):
    from forecast.backups import backup, configured_repositories, restore
    from forecast.jobs import check_cost

    if config["environment"] != "development":
        raise ValueError("Cloud fixtures require Development")
    validate_database_name(name)
    process = psutil.Process()
    if hasattr(process, "cpu_affinity"):
        process.cpu_affinity(process.cpu_affinity()[:2])
    started = time.perf_counter()
    cpu_started = time.process_time()
    current = datetime.now(timezone.utc)
    for measured, projected in ((5, 0), (0, 5)):
        try:
            check_cost(
                {
                    "month": current.strftime("%Y-%m"),
                    "measured_usd": measured,
                    "projected_usd": projected,
                },
                current,
            )
        except ValueError:
            pass
        else:
            raise ValueError("Cost suspension failed")
    source, independent = configured_repositories(config)
    admin_url = os.environ["DATABASE_URL"]
    with psycopg.connect(admin_url, autocommit=True) as admin:
        for database in (name, name + "_restore"):
            admin.execute(
                sql.SQL("CREATE DATABASE {}").format(sql.Identifier(database))
            )
    with psycopg.connect(
        make_conninfo(admin_url, dbname=name), autocommit=True
    ) as connection:
        for migration in ("001_storage", "002_jobs"):
            connection.execute(
                (
                    Path(__file__).parent / "migrations" / f"{migration}.up.sql"
                ).read_text()
            )
        workflow = exercise(connection, source, output, name)
        original = database_snapshot(connection)
        saved = backup(
            connection, source, independent, "development", datetime.now(timezone.utc)
        )
        database_bytes = connection.execute(
            "SELECT pg_database_size(current_database())"
        ).fetchone()[0]
    with psycopg.connect(
        make_conninfo(admin_url, dbname=name + "_restore"), autocommit=True
    ) as restored:
        recovery = restore(restored, independent, saved["manifest_key"])
        if database_snapshot(restored) != original:
            raise ValueError("Restored rows differ")
    report = {
        "evidence": "fixture",
        "promotion": False,
        "cost_suspension_at_five_verified": True,
        "database": name,
        "workflow": workflow,
        "backup": saved,
        "restore": recovery,
        "database_bytes": database_bytes,
        "wall_seconds": time.perf_counter() - started,
        "cpu_seconds": time.process_time() - cpu_started,
        "executed_at": datetime.now(timezone.utc).isoformat(),
        "limits": "Synthetic fixture; no prospective performance or guaranteed future availability",
    }
    (output / "report.json").write_text(json.dumps(report), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", required=True, type=Path)
    parser.add_argument("--database-name", required=True)
    parser.add_argument("--worker", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--output", type=Path, help=argparse.SUPPRESS)
    args = parser.parse_args()
    validate_database_name(args.database_name)
    config = json.loads(args.config.read_text(encoding="utf-8"))
    if config["environment"] != "development":
        raise ValueError("Cloud fixtures require Development")
    if args.worker:
        worker(config, args.database_name, args.output)
        return
    with tempfile.TemporaryDirectory(prefix="forecast-cloud-") as directory:
        output = Path(directory)
        metrics = supervise(
            [
                sys.executable,
                "-m",
                "forecast.cloud_validation",
                "--config",
                str(args.config),
                "--database-name",
                args.database_name,
                "--worker",
                "--output",
                str(output),
            ],
            output / "worker.log",
            seconds=300,
            rss_bytes=4 * 1024**3,
        )
        report = json.loads((output / "report.json").read_text(encoding="utf-8"))
        report["supervisor"] = metrics
        from forecast.backups import configured_repositories

        _, independent = configured_repositories(config)
        content = json.dumps(report, indent=2).encode()
        key = f"development/validation-reports/{args.database_name}.json"
        independent.client.put_object(
            Bucket=independent.bucket, Key=key, Body=content, IfNoneMatch="*"
        )
        if (
            independent.client.get_object(Bucket=independent.bucket, Key=key)[
                "Body"
            ].read()
            != content
        ):
            raise ValueError("Validation report verification failed")
        print(content.decode())


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print(json.dumps({"status": "failed", "error_type": type(error).__name__}))
        raise SystemExit(1) from None
