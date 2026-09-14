"""Opt-in fixture validation in two NEW dedicated Development databases."""

from datetime import date, datetime, timedelta, timezone
import hashlib
import io
import json
import math
import os
from pathlib import Path
import re
import subprocess
import time


class MeasuredS3:
    """Count application payloads; excludes SDK internal retries and HTTP overhead."""

    def __init__(self, client):
        self.client = client
        self.upload_payload_bytes = 0
        self.download_bytes = 0

    def put_object(self, **kwargs):
        self.upload_payload_bytes += len(kwargs["Body"])
        return self.client.put_object(**kwargs)

    def get_object(self, **kwargs):
        result = self.client.get_object(**kwargs)
        content = result["Body"].read()
        self.download_bytes += len(content)
        return {**result, "Body": io.BytesIO(content)}

    def get_paginator(self, name):
        return self.client.get_paginator(name)


def validate_database_name(name):
    if not re.fullmatch(r"forecast_validation_[a-f0-9]{8,24}", name):
        raise ValueError(
            "A new dedicated forecast_validation_<hex> database is required"
        )


class LocalCopy:
    """Read artifacts from an independent offline backup, without contacting S3."""

    def __init__(self, directory):
        self.directory = Path(directory).resolve()

    def path(self, key):
        path = (self.directory / key).resolve()
        if not path.is_relative_to(self.directory):
            raise ValueError("Unsafe backup key")
        return path

    def get_object(self, *, Bucket, Key):
        return {"Body": io.BytesIO(self.path(Key).read_bytes())}


def backup_object(client, bucket, key, directory):
    content = client.get_object(Bucket=bucket, Key=key)["Body"].read()
    path = LocalCopy(directory).path(key)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as handle:
        handle.write(content)
    if path.read_bytes() != content:
        raise ValueError("Independent backup differs")
    return {
        "key": key,
        "bytes": len(content),
        "sha256": hashlib.sha256(content).hexdigest(),
    }


def probe_object(client, bucket, key, directory):
    from botocore.exceptions import ClientError

    content = b"Forecast Development fixture, never promotion evidence."
    client.put_object(Bucket=bucket, Key=key, Body=content, IfNoneMatch="*")
    try:
        client.put_object(Bucket=bucket, Key=key, Body=b"overwrite", IfNoneMatch="*")
    except ClientError as error:
        status = error.response.get("ResponseMetadata", {}).get("HTTPStatusCode")
        if status != 412:
            raise
    else:
        raise ValueError("Conditional overwrite was accepted")
    if client.get_object(Bucket=bucket, Key=key)["Body"].read() != content:
        raise ValueError("Original object changed")
    return {
        **backup_object(client, bucket, key, directory),
        "overwrite_http_status": status,
    }


def exercise(connection, repository, output, version_id):
    from forecast.artifacts import emit_forecast, save_model
    from forecast.benchmark import GaussianRandomWalkCandidate
    from forecast.jobs import (
        artifact_loader,
        fresh_weekly,
        persist_snapshot,
        register_bundle,
        run_batch,
    )
    from forecast.storage import ForecastStore

    now = datetime(2026, 9, 7, tzinfo=timezone.utc)
    first = date(2024, 1, 1)
    daily = [
        {
            "date": (first + timedelta(days=i)).isoformat(),
            "close": 100 * math.exp(i * 0.0002 + 0.08 * math.sin(i / 35)),
            "revision": "synthetic-v1",
            "source": "development-validation-fixture",
            "observed_at": now.isoformat(),
        }
        for i in range((now.date() - first).days)
    ]
    weekly = fresh_weekly(daily, now)
    candidate = GaussianRandomWalkCandidate()
    candidate.fit([row["close"] for row in weekly], len(weekly))
    model = output / "fixture-model"
    save_model(
        candidate, model, {"last_week": weekly[-1]["date"], "evidence": "fixture"}
    )
    store = ForecastStore(connection)
    register_bundle(store, repository, model, version_id, "development")
    loader = artifact_loader(repository, "development")
    fx = {
        "EUR": {"date": "2026-09-04", "rate": 0.92},
        "CHF": {"date": "2026-09-04", "rate": 0.85},
    }

    def verify(manifest, prefix):
        emit_forecast(
            loader(manifest, prefix, date(2026, 8, 31)),
            weekly,
            now.date().isoformat(),
            fx,
        )

    store.activate_version(version_id, verify)
    args = dict(
        evidence="fixture",
        daily_loader=lambda cutoff: [
            r for r in daily if r["date"] <= cutoff.isoformat()
        ],
        fx_loader=lambda _: fx,
        candidate_loader=loader,
        snapshot_writer=lambda prefix, doc: persist_snapshot(repository, prefix, doc),
        cost={"month": "2026-09", "measured_usd": 0, "projected_usd": 0},
    )
    first_run = run_batch(connection, now=now, **args)
    replay = run_batch(connection, now=now, **args)
    if first_run != {"emission": "valid", "scores": 0} or replay != {
        "emission": "already_published",
        "scores": 0,
    }:
        raise ValueError("Fixture emission or replay failed")
    daily.append(
        {
            "date": "2026-09-13",
            "close": 130,
            "revision": "known-target",
            "source": "fixture",
        }
    )
    scored = run_batch(
        connection, now=datetime(2026, 9, 16, tzinfo=timezone.utc), **args
    )
    rescored = run_batch(
        connection, now=datetime(2026, 9, 16, tzinfo=timezone.utc), **args
    )
    if scored.get("scores") != 1 or rescored.get("scores") != 0:
        raise ValueError("Known-target scoring or replay failed")
    # A distinct fixture version proves rollback while preserving emitted payloads.
    second = version_id + "-rollback"
    register_bundle(store, repository, model, second, "development")
    store.activate_version(second, verify)
    store.rollback(verify)
    if (
        connection.execute(
            "SELECT active_version FROM forecast.publication"
        ).fetchone()[0]
        != version_id
    ):
        raise ValueError("Rollback failed")
    return {
        "first_run": first_run,
        "replay": replay,
        "scoring": scored,
        "scoring_replay": rescored,
        "rollback": True,
    }


def database_snapshot(connection):
    # Full rows catch changed FX, metadata, version pointers, attempts and scores.
    tables = (
        "versions",
        "publication",
        "emissions",
        "scores",
        "attempts",
        "reports",
        "maintenance",
        "candidate_cycles",
    )
    return {
        name: sorted(
            connection.execute(
                f"SELECT row_to_json(t)::text FROM forecast.{name} t"
            ).fetchall()
        )
        for name in tables
    }


def pg_command(executable, url, arguments):
    from psycopg.conninfo import conninfo_to_dict

    info = conninfo_to_dict(url)
    env = os.environ.copy()
    for source, target in (
        ("host", "PGHOST"),
        ("port", "PGPORT"),
        ("user", "PGUSER"),
        ("password", "PGPASSWORD"),
        ("dbname", "PGDATABASE"),
        ("sslmode", "PGSSLMODE"),
    ):
        if source in info:
            env[target] = info[source]
    completed = subprocess.run(
        [executable, *arguments], env=env, capture_output=True, timeout=180
    )
    if completed.returncode:
        raise RuntimeError(
            "PostgreSQL backup/restore command failed; diagnostics withheld to protect credentials"
        )


def main(argv=None):
    import argparse
    import boto3
    import psycopg
    from psycopg import sql
    from psycopg.conninfo import make_conninfo
    import psutil
    from forecast.jobs import artifact_loader
    from forecast.storage_artifacts import ArtifactRepository

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database-name", required=True)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args(argv)
    validate_database_name(args.database_name)
    args.output.mkdir(parents=True, exist_ok=False)
    started = time.perf_counter()
    cpu_started = time.process_time()
    admin_url = os.environ["DATABASE_URL"]
    bucket = os.environ["FORECAST_S3_BUCKET"]
    client = MeasuredS3(
        boto3.client("s3", endpoint_url=os.environ["FORECAST_S3_ENDPOINT_URL"])
    )
    repository = ArtifactRepository(client, bucket)
    prefix = "development/" + args.database_name
    backup = args.output / "independent-objects"
    probe = probe_object(client, bucket, prefix + "/probe", backup)
    urls = [
        make_conninfo(admin_url, dbname=name)
        for name in (args.database_name, args.database_name + "_restore")
    ]
    with psycopg.connect(admin_url, autocommit=True) as admin:
        for name in (args.database_name, args.database_name + "_restore"):
            admin.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(name)))
    report = {
        "evidence": "fixture",
        "promotion": False,
        "database": args.database_name,
        "probe": probe,
        "objects": [],
        "executed_at": datetime.now(timezone.utc).isoformat(),
    }
    with psycopg.connect(urls[0], autocommit=True) as connection:
        for migration in ("001_storage", "002_jobs"):
            connection.execute(
                (
                    Path(__file__).parent / "migrations" / f"{migration}.up.sql"
                ).read_text()
            )
        report["workflow"] = exercise(
            connection, repository, args.output, args.database_name
        )
        before = database_snapshot(connection)
        report["database_bytes"] = connection.execute(
            "SELECT pg_database_size(current_database())"
        ).fetchone()[0]
        report["forecast_relation_bytes"] = connection.execute(
            "SELECT sum(pg_total_relation_size(c.oid))::bigint FROM pg_class c JOIN pg_namespace n ON c.relnamespace=n.oid WHERE n.nspname='forecast' AND c.relkind='r'"
        ).fetchone()[0]
        paginator = client.get_paginator("list_objects_v2")
        for page in paginator.paginate(Bucket=bucket, Prefix=prefix):
            for item in page.get("Contents", []):
                if item["Key"] != prefix + "/probe":
                    report["objects"].append(
                        backup_object(client, bucket, item["Key"], backup)
                    )
    dump = args.output / "forecast.dump"
    pg_command(
        os.environ.get("FORECAST_PG_DUMP", "pg_dump"),
        urls[0],
        ["--format=custom", "--no-owner", "--no-acl", "--file", str(dump)],
    )
    restore_started = time.perf_counter()
    pg_command(
        os.environ.get("FORECAST_PG_RESTORE", "pg_restore"),
        urls[1],
        [
            "--no-owner",
            "--no-acl",
            "--exit-on-error",
            "--dbname",
            args.database_name + "_restore",
            str(dump),
        ],
    )
    with psycopg.connect(urls[1], autocommit=True) as restored:
        if database_snapshot(restored) != before:
            raise ValueError("Restored database differs from source")
        local_repository = ArtifactRepository(LocalCopy(backup), "offline")
        loader = artifact_loader(local_repository, "development")
        for manifest, artifact_prefix in restored.execute(
            "SELECT manifest,artifact_prefix FROM forecast.versions"
        ):
            loader(manifest, artifact_prefix, date(2026, 8, 31))
        for (payload,) in restored.execute("SELECT payload FROM forecast.emissions"):
            body = local_repository.client.get_object(
                Bucket="offline", Key=payload["snapshot_key"]
            )["Body"].read()
            if hashlib.sha256(body).hexdigest() != payload["snapshot_sha256"]:
                raise ValueError("Restored snapshot differs")
    report.update(
        restore_seconds=time.perf_counter() - restore_started,
        elapsed_seconds=time.perf_counter() - started,
        cpu_seconds=time.process_time() - cpu_started,
        final_rss_bytes=psutil.Process().memory_info().rss,
        database_backup_bytes=dump.stat().st_size,
        object_bytes=sum(o["bytes"] for o in report["objects"]) + probe["bytes"],
        restore_verified=True,
        s3_upload_payload_bytes=client.upload_payload_bytes,
        s3_download_bytes=client.download_bytes,
        limits=[
            "S3 upload and download payload counts exclude SDK internal retries and HTTP overhead",
            "Synthetic software validation only",
            "One backup does not prove a daily schedule or 24-hour RPO",
            "Local process metrics exclude Railway service compute and billing",
        ],
    )
    (args.output / "report.json").write_text(
        json.dumps(report, indent=2), encoding="utf-8"
    )
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print(json.dumps({"status": "failed", "error_type": type(error).__name__}))
        raise SystemExit(1) from None
