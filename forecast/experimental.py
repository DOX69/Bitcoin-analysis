"""Publish verified research emissions as a six-month experiment, never a champion."""

import calendar
from datetime import date, datetime, timedelta, timezone
import json
import math
import os

from forecast.backups import digest, put_verified, read
from forecast.candidate_cloud import MODEL_PREFIX, PREFIX, validate_emission
from forecast.jobs import DatabaseSource, check_cost
from forecast.storage_artifacts import ArtifactRepository, filenames

DESTINATION = "production/experimental/lightgbm-v1"
LOCK = 7_319_941_903_106_202_614


def six_month_end(day):
    month = day.month + 6
    year = day.year + (month - 1) // 12
    month = (month - 1) % 12 + 1
    return date(year, month, min(day.day, calendar.monthrange(year, month)[1]))


def public_emission(document, fx):
    validate_emission(document)
    issued = date.fromisoformat(document["emission_date"])
    if issued != datetime.fromisoformat(document["created_at"]).date():
        raise ValueError("Emission date differs from its actual creation")
    for currency in ("EUR", "CHF"):
        value = fx[currency]
        if (
            date.fromisoformat(value["date"]) > issued
            or not math.isfinite(value["rate"])
            or value["rate"] <= 0
        ):
            raise ValueError("Invalid emission-time FX")
    end = six_month_end(issued)
    return {
        "id": document["origin_week"],
        "emissionDate": issued.isoformat(),
        "issuedAt": document["created_at"],
        "originWeek": document["origin_week"],
        "originDate": (
            date.fromisoformat(document["points"][0]["target_date"]) - timedelta(days=7)
        ).isoformat(),
        "horizonEnd": end.isoformat(),
        "status": "delayed" if issued.weekday() == 1 else "valid",
        "fx": fx,
        "points": [
            {
                "horizonWeeks": point["horizon_weeks"],
                "targetDate": point["target_date"],
                "USD": point["USD"],
                **{
                    currency: [value * fx[currency]["rate"] for value in point["USD"]]
                    for currency in ("EUR", "CHF")
                },
            }
            for point in document["points"]
            if date.fromisoformat(point["target_date"]) <= end
        ],
    }


def mirror_model(source, destination, backup, manifest_sha):
    from botocore.exceptions import ClientError

    manifest_bytes = read(source, MODEL_PREFIX + "/manifest.json")
    if digest(manifest_bytes) != manifest_sha:
        raise ValueError("Experimental model differs from the explicitly pinned model")
    manifest = json.loads(manifest_bytes)
    target = DESTINATION + "/bundle/model"
    try:
        saved = read(destination, target + "/manifest.json")
    except ClientError as error:
        if error.response.get("Error", {}).get("Code") not in ("NoSuchKey", "404"):
            raise
    else:
        if saved != manifest_bytes or read(backup, target + "/manifest.json") != saved:
            raise ValueError("Experimental model archive changed")
        return
    for name in filenames(manifest):
        content = read(source, MODEL_PREFIX + "/" + name)
        if digest(content) != manifest["files"][name]:
            raise ValueError("Experimental model file changed")
        put_verified(destination, target + "/" + name, content)
        put_verified(backup, target + "/" + name, content)
    training = read(source, manifest["context"]["snapshot_key"])
    if digest(training) != manifest["context"]["snapshot_sha256"]:
        raise ValueError("Model training snapshot changed")
    for repository in (destination, backup):
        put_verified(repository, target + "/training-snapshot.json", training)
    for repository in (destination, backup):
        put_verified(repository, target + "/manifest.json", manifest_bytes)


def publish(connection, source, destination, backup, documents, manifest_sha, now):
    """Input emissions have passed the collector's exact snapshot/model replay."""
    if destination.bucket == backup.bucket or now.utcoffset().total_seconds() != 0:
        raise ValueError("Independent backup and UTC publication required")
    if not connection.execute("SELECT pg_try_advisory_lock(%s)", (LOCK,)).fetchone()[0]:
        return {"status": "already_running"}
    try:
        mirror_model(source, destination, backup, manifest_sha)
        published = 0
        for document in documents:
            validate_emission(document, manifest_sha)
            if datetime.fromisoformat(document["created_at"]) > now:
                raise ValueError("Cannot publish a future emission")
            key = f"{PREFIX}/emissions/{document['origin_week']}.json"
            original = read(source, key)
            envelope = json.loads(original)
            if envelope["emission"] != document:
                raise ValueError("Research emission changed after verification")
            source_sha = digest(original)
            existing = connection.execute(
                "SELECT source_sha256 FROM forecast_experimental.emissions WHERE origin_week=%s",
                (document["origin_week"],),
            ).fetchone()
            if existing:
                if existing[0] != source_sha:
                    raise ValueError("Existing experimental emission is immutable")
                continue
            snapshot = read(source, envelope["snapshot_key"])
            if digest(snapshot) != envelope["snapshot_sha256"]:
                raise ValueError("Research snapshot changed")
            fx = DatabaseSource(
                connection,
                "unused",
                "bronze",
                datetime.fromisoformat(document["created_at"]),
            ).fx(date.fromisoformat(document["emission_date"]))
            payload = public_emission(document, fx)
            content = (
                json.dumps(payload, sort_keys=True, allow_nan=False) + "\n"
            ).encode()
            prefix = f"{DESTINATION}/emissions/{document['origin_week']}"
            for repository in (destination, backup):
                put_verified(repository, prefix + "/source.json", original)
                put_verified(repository, prefix + "/snapshot.json", snapshot)
                put_verified(repository, prefix + "/public.json", content)
            connection.execute(
                """INSERT INTO forecast_experimental.emissions
                (origin_week,emission_date,model_sha256,source_sha256,payload_sha256,payload)
                VALUES (%s,%s,%s,%s,%s,%s::jsonb)""",
                (
                    document["origin_week"],
                    document["emission_date"],
                    manifest_sha,
                    source_sha,
                    digest(content),
                    content.decode(),
                ),
            )
            published += 1
        return {"status": "completed", "new_emissions": published, "experimental": True}
    finally:
        connection.execute("SELECT pg_advisory_unlock(%s)", (LOCK,))


def main():
    import argparse
    from pathlib import Path
    import boto3
    from botocore.config import Config
    import psycopg

    from forecast import candidate_cloud as cloud

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", required=True, type=Path)
    args = parser.parse_args()
    config = json.loads(args.config.read_text())
    manifest_sha = os.environ["FORECAST_EXPERIMENTAL_MODEL_SHA256"]
    now = datetime.now(timezone.utc)
    if (
        os.environ.get("RAILWAY_ENVIRONMENT_NAME", "").lower() != "production"
        or config.get("destination_environment") != "production"
        or len(manifest_sha) != 64
    ):
        raise ValueError("Explicit experimental destination and frozen model required")
    network = Config(connect_timeout=5, read_timeout=15, retries={"max_attempts": 2})
    repositories = []
    for kind in ("SOURCE", "SOURCE_BACKUP", "ARTIFACT", "BACKUP"):
        prefix = f"FORECAST_EXPERIMENTAL_{kind}_"
        client = boto3.client(
            "s3",
            endpoint_url=os.environ[prefix + "ENDPOINT"],
            aws_access_key_id=os.environ[prefix + "ACCESS_KEY_ID"],
            aws_secret_access_key=os.environ[prefix + "SECRET_ACCESS_KEY"],
            region_name="auto",
            config=network,
        )
        repositories.append(ArtifactRepository(client, os.environ[prefix + "BUCKET"]))
    source, source_backup, destination, backup = repositories
    check_cost(
        json.loads(read(source, config["cost_prefix"] + f"/{now:%Y-%m}.json")), now
    )
    with psycopg.connect(os.environ["DATABASE_URL"], autocommit=True) as connection:
        saved = dict(
            connection.execute(
                "SELECT origin_week::text,source_sha256 FROM forecast_experimental.emissions WHERE model_sha256=%s",
                (manifest_sha,),
            ).fetchall()
        )
        source_keys = cloud.keys(source, PREFIX + "/emissions")
        if source_keys and all(
            saved.get(key.rsplit("/", 1)[-1][:-5]) == digest(read(source, key))
            for key in source_keys
        ):
            print(json.dumps({"status": "up_to_date", "experimental": True}))
            return
        model, directory = cloud._load_model(source, manifest_sha)
        try:
            documents = cloud._load_emissions(
                source, source_backup, model, manifest_sha, now
            )
            print(
                json.dumps(
                    publish(
                        connection,
                        source,
                        destination,
                        backup,
                        documents,
                        manifest_sha,
                        now,
                    )
                )
            )
        finally:
            for path in directory.iterdir():
                path.unlink()
            directory.rmdir()
            directory.parent.rmdir()


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print(json.dumps({"status": "failed", "error_type": type(error).__name__}))
        raise SystemExit(1) from None
