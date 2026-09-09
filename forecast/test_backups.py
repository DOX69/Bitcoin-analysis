import io
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path

import psycopg
from psycopg import sql
import pytest
from botocore.exceptions import ClientError

from forecast import backups
from forecast.storage_artifacts import ArtifactRepository


class Objects:
    def __init__(self):
        self.objects = {}

    def put_object(self, *, Bucket, Key, Body, IfNoneMatch):
        if Key in self.objects:
            raise ClientError(
                {"ResponseMetadata": {"HTTPStatusCode": 412}}, "PutObject"
            )
        self.objects[Key] = Body

    def get_object(self, *, Bucket, Key):
        return {"Body": io.BytesIO(self.objects[Key])}

    def get_paginator(self, name):
        return self

    def paginate(self, *, Bucket, Prefix):
        yield {
            "Contents": [{"Key": key} for key in self.objects if key.startswith(Prefix)]
        }


@pytest.fixture
def databases():
    import os
    from psycopg.conninfo import make_conninfo

    url = os.environ.get("FORECAST_BACKUP_TEST_DATABASE_URL")
    if not url:
        pytest.skip("Set FORECAST_BACKUP_TEST_DATABASE_URL to a local test server")
    from psycopg.conninfo import conninfo_to_dict

    assert conninfo_to_dict(url)["host"] in ("127.0.0.1", "localhost")
    names = ["forecast_backup_" + uuid.uuid4().hex[:12] for _ in range(2)]
    with psycopg.connect(url, autocommit=True) as admin:
        connections = []
        try:
            for name in names:
                admin.execute(
                    sql.SQL("CREATE DATABASE {}").format(sql.Identifier(name))
                )
                connections.append(
                    psycopg.connect(make_conninfo(url, dbname=name), autocommit=True)
                )
            yield connections
        finally:
            for connection in connections:
                connection.close()
            for name in names:
                admin.execute(
                    sql.SQL("DROP DATABASE IF EXISTS {}").format(sql.Identifier(name))
                )


def seeded(connection):
    objects = {
        "development/v1/state.json": b"original",
        "development/v1/snapshots/frozen.json": b"{}",
    }
    manifest = {"files": {"state.json": backups.digest(b"original")}}
    body = json.dumps(manifest).encode()
    objects["development/v1/manifest.json"] = body
    manifest["storage_sha256"] = backups.digest(body)
    for name in ("001_storage", "002_jobs"):
        connection.execute(
            (Path(__file__).parent / "migrations" / (name + ".up.sql")).read_text()
        )
    connection.execute(
        "INSERT INTO forecast.versions(id,manifest,artifact_prefix) VALUES ('v1',%s,'development/v1')",
        (json.dumps(manifest),),
    )
    connection.execute("UPDATE forecast.publication SET active_version='v1'")
    connection.execute(
        "INSERT INTO forecast.emissions VALUES ('e1','v1','2026-08-31','2026-09-07',now(),'valid',%s)",
        (
            json.dumps(
                {
                    "snapshot_key": "development/v1/snapshots/frozen.json",
                    "snapshot_sha256": backups.digest(b"{}"),
                }
            ),
        ),
    )
    connection.execute(
        "INSERT INTO forecast.scores(emission_id,horizon,observation_revision,observed,metrics) VALUES ('e1',1,'r1',120,'{}')"
    )
    connection.execute(
        "INSERT INTO forecast.reports(version_id,month,report) VALUES ('v1','2026-09-01','{}')"
    )
    connection.execute(
        "INSERT INTO forecast.attempts VALUES ('2026-08-31','2026-09-07',now(),now(),'valid',NULL)"
    )
    connection.execute(
        "INSERT INTO forecast.maintenance VALUES ('development/rejected','2026-09-01',NULL)"
    )
    connection.execute(
        "INSERT INTO forecast.candidate_cycles VALUES ('2026-07-01',now(),'fixture')"
    )
    return objects


def test_roundtrip_preserves_rows_fk_triggers_and_independent_objects(databases):
    source, target = databases
    live, offline = Objects(), Objects()
    live.objects.update(seeded(source))
    now = datetime(2026, 9, 9, tzinfo=timezone.utc)
    report = backups.backup(
        source,
        ArtifactRepository(live, "live"),
        ArtifactRepository(offline, "backup"),
        "development",
        now,
    )
    again = backups.backup(
        source,
        ArtifactRepository(live, "live"),
        ArtifactRepository(offline, "backup"),
        "development",
        now,
    )
    assert again["manifest_key"] == report["manifest_key"]
    live.objects.clear()
    result = backups.restore(
        target, ArtifactRepository(offline, "backup"), report["manifest_key"]
    )
    assert result["tables"] == 8
    assert offline.objects["development/v1/state.json"] == b"original"
    assert target.execute(
        "SELECT active_version FROM forecast.publication"
    ).fetchone() == ("v1",)
    assert target.execute("SELECT observed FROM forecast.scores").fetchone() == (120,)
    for table in backups.TABLES:
        statement = sql.SQL("SELECT row_to_json(t)::text FROM forecast.{} t").format(
            sql.Identifier(table)
        )
        assert sorted(target.execute(statement).fetchall()) == sorted(
            source.execute(statement).fetchall()
        )
    with pytest.raises(psycopg.Error):
        target.execute("DELETE FROM forecast.emissions")
    with pytest.raises(psycopg.errors.ForeignKeyViolation):
        target.execute("UPDATE forecast.publication SET active_version='missing'")
    with pytest.raises(ValueError, match="existing forecast schema"):
        backups.restore(
            target, ArtifactRepository(offline, "backup"), report["manifest_key"]
        )


def test_corrupt_backup_rejected_before_schema_creation(databases):
    source, target = databases
    live = Objects()
    live.objects.update(seeded(source))
    offline = Objects()
    repository = ArtifactRepository(offline, "backup")
    report = backups.backup(
        source,
        ArtifactRepository(live, "live"),
        repository,
        "development",
        datetime.now(timezone.utc),
    )
    manifest = json.loads(offline.objects[report["manifest_key"]])
    offline.objects[manifest["tables"][0]["key"]] += b"corrupt"
    with pytest.raises(ValueError, match="checksum"):
        backups.restore(target, repository, report["manifest_key"])
    assert target.execute("SELECT to_regnamespace('forecast')").fetchone() == (None,)


def test_immutable_conflict_rejected():
    client = Objects()
    repository = ArtifactRepository(client, "backup")
    backups.put_verified(repository, "development/v1/test", b"first")
    with pytest.raises(ValueError, match="Conflicting"):
        backups.put_verified(repository, "development/v1/test", b"different")


def test_missing_referenced_snapshot_cannot_publish_manifest(databases):
    source, _ = databases
    live, offline = Objects(), Objects()
    live.objects.update(seeded(source))
    del live.objects["development/v1/snapshots/frozen.json"]
    with pytest.raises(ValueError, match="referenced snapshot"):
        backups.backup(
            source,
            ArtifactRepository(live, "live"),
            ArtifactRepository(offline, "backup"),
            "development",
            datetime.now(timezone.utc),
        )
    assert not any(key.endswith("/manifest") for key in offline.objects)
