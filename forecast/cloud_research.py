"""Development-only prospective collection with immutable S3 and independent copies."""

import argparse
from datetime import datetime, timedelta, timezone
import json
import os
from pathlib import Path
import tempfile

from forecast import benchmark as b
from forecast import prospective_research as local
from forecast.backups import configured_repositories, digest, put_verified, read
from forecast.jobs import DatabaseSource, check_cost

PREFIX = "development/research/hybrid-v1"
LOCK = 7_319_941_903_106_202_612
BUNDLE_FILES = (
    "manifest.json",
    "snapshot.csv",
    "standardized-distribution.json",
    "research-shadow.json",
)


def encode(value):
    return (json.dumps(value, sort_keys=True, allow_nan=False) + "\n").encode()


def keys(repository, prefix):
    return sorted(
        item["Key"]
        for page in repository.client.get_paginator("list_objects_v2").paginate(
            Bucket=repository.bucket, Prefix=prefix + "/"
        )
        for item in page.get("Contents", [])
    )


def save(source, backup, key, value):
    content = encode(value)
    first = put_verified(source, key, content)
    put_verified(backup, key, content)
    return first


def load_emissions(source, backup, distribution):
    documents = []
    for key in keys(source, PREFIX + "/emissions"):
        content = read(source, key)
        envelope = json.loads(content)
        document = envelope["emission"]
        local.validate_emission(document)
        snapshot_key = envelope["snapshot_key"]
        if not snapshot_key.startswith(PREFIX + "/snapshots/"):
            raise ValueError("Research snapshot outside its namespace")
        snapshot = read(source, snapshot_key)
        if digest(snapshot) != envelope["snapshot_sha256"]:
            raise ValueError("Research source snapshot changed")
        weekly = b.aggregate_daily_rows(json.loads(snapshot))
        expected = local.make_emission(
            weekly,
            distribution,
            datetime.fromisoformat(document["created_at"]),
            evidence="prospective",
        )
        if document != expected:
            raise ValueError("Research emission differs from its source replay")
        # Also repairs an interrupted independent copy without rewriting the source.
        put_verified(backup, snapshot_key, snapshot)
        put_verified(backup, key, content)
        documents.append(document)
    return documents


def collect(source, backup, bundle, daily, now, *, emit=True):
    distribution = local.frozen_distribution(bundle)
    legacy = local.read_legacy_emission(bundle, distribution)
    monday = now.date() - timedelta(days=now.weekday())
    if any(datetime.fromisoformat(row["date"]).date() >= monday for row in daily):
        raise ValueError("Research source includes an incomplete week")
    weekly = b.aggregate_daily_rows(daily)
    documents = load_emissions(source, backup, distribution)
    snapshot = encode(daily)
    snapshot_key = f"{PREFIX}/snapshots/{digest(snapshot)}.json"
    put_verified(source, snapshot_key, snapshot)
    put_verified(backup, snapshot_key, snapshot)
    if emit and now.weekday() in (0, 1):
        origin = (monday - timedelta(weeks=1)).isoformat()
        if not any(document["origin_week"] == origin for document in documents):
            document = local.make_emission(
                weekly, distribution, now, evidence="prospective"
            )
            save(
                source,
                backup,
                f"{PREFIX}/emissions/{origin}.json",
                {
                    "emission": document,
                    "snapshot_key": snapshot_key,
                    "snapshot_sha256": digest(snapshot),
                },
            )
            documents.append(document)
    report = local.score_emissions([legacy, *documents], weekly, now)
    report["snapshot_key"] = snapshot_key
    report["snapshot_sha256"] = digest(snapshot)
    report["runtime"] = local.dependencies()
    report["collector_sha256"] = local.sha256(Path(__file__))
    report_key = f"{PREFIX}/reports/{now.strftime('%Y%m%dT%H%M%S%fZ')}.json"
    saved = save(source, backup, report_key, report)
    return {
        "status": "completed",
        "emissions": len(documents) + 1,
        "mature_points": sum(row["origins"] for row in report["per_horizon"]),
        "ready_for_confirmation_review": report["ready_for_confirmation_review"],
        "publishable": False,
        "report_key": report_key,
        "report_sha256": saved["sha256"],
        "independent_copy_verified": True,
    }


def main():
    import psutil
    import psycopg

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--score-only", action="store_true")
    args = parser.parse_args()
    config = json.loads(args.config.read_text())
    if (
        config.get("environment") != "development"
        or os.environ.get("RAILWAY_ENVIRONMENT_NAME", "").lower() != "development"
    ):
        raise ValueError("Research worker is restricted to Railway Development")
    process = psutil.Process()
    process.cpu_affinity(process.cpu_affinity()[:2])
    source, backup = configured_repositories(config)
    now = datetime.now(timezone.utc)
    check_cost(
        json.loads(read(source, f"{PREFIX}/budget/{now.strftime('%Y-%m')}.json")), now
    )
    with psycopg.connect(os.environ["DATABASE_URL"], autocommit=True) as connection:
        if not connection.execute(
            "SELECT pg_try_advisory_lock(%s)", (LOCK,)
        ).fetchone()[0]:
            print(json.dumps({"status": "already_running"}))
            return
        try:
            monday = now.date() - timedelta(days=now.weekday())
            daily = DatabaseSource(
                connection, config["daily_schema"], config["bronze_schema"], now
            ).daily(monday - timedelta(days=1))
            with tempfile.TemporaryDirectory(prefix="research-bundle-") as directory:
                bundle = Path(directory)
                for name in BUNDLE_FILES:
                    (bundle / name).write_bytes(read(source, f"{PREFIX}/bundle/{name}"))
                print(
                    json.dumps(
                        collect(
                            source,
                            backup,
                            bundle,
                            daily,
                            datetime.now(timezone.utc),
                            emit=not args.score_only,
                        )
                    )
                )
        finally:
            connection.execute("SELECT pg_advisory_unlock(%s)", (LOCK,))


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print(json.dumps({"status": "failed", "error_type": type(error).__name__}))
        raise SystemExit(1) from None
