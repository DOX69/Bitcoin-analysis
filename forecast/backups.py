"""Independent immutable forecast backups, restored only into a new schema."""

import hashlib
import json
from pathlib import Path
import time
import re

from psycopg import sql
from psycopg.pq import TransactionStatus

TABLES = (
    "versions",
    "publication",
    "emissions",
    "scores",
    "attempts",
    "maintenance",
    "reports",
    "candidate_cycles",
)
MIGRATIONS = ("001_storage.up.sql", "002_jobs.up.sql")


def digest(content):
    return hashlib.sha256(content).hexdigest()


def read(repository, key):
    validate_key(key)
    return repository.client.get_object(Bucket=repository.bucket, Key=key)[
        "Body"
    ].read()


def put_verified(repository, key, content):
    from botocore.exceptions import ClientError

    validate_key(key)
    try:
        repository.client.put_object(
            Bucket=repository.bucket, Key=key, Body=content, IfNoneMatch="*"
        )
    except ClientError as error:
        if error.response.get("ResponseMetadata", {}).get("HTTPStatusCode") != 412:
            raise
    if digest(read(repository, key)) != digest(content):
        raise ValueError("Conflicting immutable backup object")
    return {"key": key, "sha256": digest(content), "bytes": len(content)}


def validate_key(key):
    if not re.fullmatch(
        r"(development|production)/(?:[A-Za-z0-9_-]+/)*[A-Za-z0-9_.-]+", key
    ) or key.rsplit("/", 1)[-1] in (".", ".."):
        raise ValueError("Unsafe backup object key")


def migration_bytes():
    return {
        name: (Path(__file__).parent / "migrations" / name).read_bytes()
        for name in MIGRATIONS
    }


def require_idle(connection):
    if connection.info.transaction_status != TransactionStatus.IDLE:
        raise ValueError("Backup/restore requires an idle connection")


def columns(connection, table):
    return [
        row[0]
        for row in connection.execute(
            "SELECT column_name FROM information_schema.columns WHERE table_schema=%s AND table_name=%s ORDER BY ordinal_position",
            ("forecast", table),
        )
    ]


def copy_statement(table, names, direction):
    return sql.SQL("COPY forecast.{} ({}) {} STD{}").format(
        sql.Identifier(table),
        sql.SQL(",").join(map(sql.Identifier, names)),
        sql.SQL(direction),
        sql.SQL("OUT" if direction == "TO" else "IN"),
    )


def verify_references(connection, repository, entries):
    from forecast.storage_artifacts import filenames

    mirrored = {item["key"]: item["sha256"] for item in entries}
    versions = connection.execute(
        """SELECT v.manifest,v.artifact_prefix
        FROM forecast.versions v LEFT JOIN forecast.maintenance m
        ON m.artifact_prefix=v.artifact_prefix
        WHERE m.purged_at IS NULL OR v.id IN
        (SELECT active_version FROM forecast.publication UNION SELECT rollback_version FROM forecast.publication)"""
    )
    for manifest, prefix in versions:
        if mirrored.get(prefix + "/manifest.json") != manifest["storage_sha256"]:
            raise ValueError("Missing or corrupt referenced model manifest")
        stored = json.loads(read(repository, prefix + "/manifest.json"))
        if stored != {
            key: value for key, value in manifest.items() if key != "storage_sha256"
        }:
            raise ValueError("Registered model manifest differs")
        for name in filenames(stored):
            if mirrored.get(prefix + "/" + name) != stored["files"][name]:
                raise ValueError("Missing or corrupt referenced model file")
    for (payload,) in connection.execute("SELECT payload FROM forecast.emissions"):
        if mirrored.get(payload["snapshot_key"]) != payload["snapshot_sha256"]:
            raise ValueError("Missing or corrupt referenced snapshot")


def backup(connection, source_repository, backup_repository, environment, now):
    if environment not in ("development", "production"):
        raise ValueError("Invalid backup environment")
    if source_repository.bucket == backup_repository.bucket:
        raise ValueError("Independent destination bucket required")
    if now.utcoffset() is None:
        raise ValueError("Timezone-aware backup time required")
    require_idle(connection)
    from datetime import timezone

    started = time.perf_counter()
    prefix = (
        environment
        + "/backups/"
        + now.astimezone(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    )
    manifest = {
        "schema_version": 1,
        "environment": environment,
        "created_at": now.isoformat(),
        "migrations": {name: digest(body) for name, body in migration_bytes().items()},
        "tables": [],
        "objects": [],
    }
    with connection.transaction():
        connection.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ")
        connection.execute("SET LOCAL TimeZone TO 'UTC'")
        connection.execute("SET LOCAL DateStyle TO 'ISO, YMD'")
        connection.execute("SELECT singleton FROM forecast.publication FOR UPDATE")
        actual = {
            r[0]
            for r in connection.execute(
                "SELECT tablename FROM pg_tables WHERE schemaname='forecast'"
            )
        }
        if actual != set(TABLES):
            raise ValueError("Unexpected forecast tables")
        for table in TABLES:
            names = columns(connection, table)
            with connection.cursor().copy(copy_statement(table, names, "TO")) as stream:
                content = b"".join(bytes(chunk) for chunk in stream)
            entry = put_verified(backup_repository, prefix + "/" + table, content)
            entry.update(
                name=table,
                columns=names,
                rows=connection.execute(
                    sql.SQL("SELECT count(*) FROM forecast.{}").format(
                        sql.Identifier(table)
                    )
                ).fetchone()[0],
            )
            manifest["tables"].append(entry)
        paginator = source_repository.client.get_paginator("list_objects_v2")
        for page in paginator.paginate(
            Bucket=source_repository.bucket, Prefix=environment + "/"
        ):
            for item in page.get("Contents", []):
                key = item["Key"]
                if not key.startswith(environment + "/"):
                    raise ValueError("Artifact environment mismatch")
                manifest["objects"].append(
                    put_verified(backup_repository, key, read(source_repository, key))
                )
        verify_references(connection, backup_repository, manifest["objects"])
    manifest["objects"].sort(key=lambda item: item["key"])
    body = json.dumps(manifest, sort_keys=True, separators=(",", ":")).encode()
    key = prefix + "/manifest"
    put_verified(backup_repository, key, body)
    return {
        "manifest_key": key,
        "bytes": len(body)
        + sum(item["bytes"] for item in manifest["tables"] + manifest["objects"]),
        "seconds": time.perf_counter() - started,
    }


def restore(connection, backup_repository, manifest_key):
    require_idle(connection)
    started = time.perf_counter()
    manifest = json.loads(read(backup_repository, manifest_key))
    environment = manifest["environment"]
    if environment not in ("development", "production") or not manifest_key.startswith(
        environment + "/backups/"
    ):
        raise ValueError("Invalid backup environment")
    migrations = migration_bytes()
    if manifest["schema_version"] != 1 or manifest["migrations"] != {
        name: digest(body) for name, body in migrations.items()
    }:
        raise ValueError("Backup migration mismatch")
    if [item["name"] for item in manifest["tables"]] != list(TABLES):
        raise ValueError("Unexpected backup tables")
    content = {}
    prefix = manifest_key.rsplit("/", 1)[0] + "/"
    for item in manifest["tables"] + manifest["objects"]:
        if not item["key"].startswith(environment + "/"):
            raise ValueError("Artifact environment mismatch")
        body = read(backup_repository, item["key"])
        if digest(body) != item["sha256"] or len(body) != item["bytes"]:
            raise ValueError("Backup checksum mismatch")
        content[item["key"]] = body
    with connection.transaction():
        connection.execute("SET LOCAL TimeZone TO 'UTC'")
        connection.execute("SET LOCAL DateStyle TO 'ISO, YMD'")
        if (
            connection.execute("SELECT to_regnamespace('forecast')").fetchone()[0]
            is not None
        ):
            raise ValueError("Refusing existing forecast schema")
        for body in migrations.values():
            connection.execute(body.decode())
        connection.execute("DELETE FROM forecast.publication")
        for item in manifest["tables"]:
            table = item["name"]
            if (
                item["key"] != prefix + table
                or columns(connection, table) != item["columns"]
            ):
                raise ValueError("Backup table metadata mismatch")
            with connection.cursor().copy(
                copy_statement(table, item["columns"], "FROM")
            ) as stream:
                stream.write(content[item["key"]])
            count = connection.execute(
                sql.SQL("SELECT count(*) FROM forecast.{}").format(
                    sql.Identifier(table)
                )
            ).fetchone()[0]
            if count != item["rows"]:
                raise ValueError("Restored row count mismatch")
        verify_references(connection, backup_repository, manifest["objects"])
    return {
        "tables": len(TABLES),
        "objects": len(manifest["objects"]),
        "seconds": time.perf_counter() - started,
    }


def configured_repositories(config):
    import os
    import boto3
    from botocore.config import Config
    from forecast.storage_artifacts import ArtifactRepository

    network = Config(connect_timeout=5, read_timeout=15, retries={"max_attempts": 2})
    source = boto3.client(
        "s3", endpoint_url=os.environ["FORECAST_S3_ENDPOINT_URL"], config=network
    )
    destination = boto3.client(
        "s3",
        endpoint_url=os.environ["FORECAST_BACKUP_S3_ENDPOINT_URL"],
        aws_access_key_id=os.environ["FORECAST_BACKUP_ACCESS_KEY_ID"],
        aws_secret_access_key=os.environ["FORECAST_BACKUP_SECRET_ACCESS_KEY"],
        region_name=os.environ.get("FORECAST_BACKUP_REGION", "auto"),
        config=network,
    )
    return ArtifactRepository(source, config["artifact_bucket"]), ArtifactRepository(
        destination, config["backup_bucket"]
    )


def main():
    import argparse
    from datetime import datetime, timezone
    import os
    import psycopg

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["backup"])
    parser.add_argument("--config", required=True, type=Path)
    args = parser.parse_args()
    config = json.loads(args.config.read_text())
    source, destination = configured_repositories(config)
    with psycopg.connect(os.environ["DATABASE_URL"], autocommit=True) as connection:
        print(
            json.dumps(
                backup(
                    connection,
                    source,
                    destination,
                    config["environment"],
                    datetime.now(timezone.utc),
                )
            )
        )


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print(json.dumps({"status": "failed", "error_type": type(error).__name__}))
        raise SystemExit(1) from None
