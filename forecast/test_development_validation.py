import io
import os
from pathlib import Path
import uuid

from botocore.exceptions import ClientError
import pytest

from forecast import development_validation as validation


class Bucket:
    def __init__(self):
        self.objects = {}

    def put_object(self, Bucket, Key, Body, IfNoneMatch):
        if Key in self.objects:
            raise ClientError(
                {
                    "Error": {"Code": "PreconditionFailed"},
                    "ResponseMetadata": {"HTTPStatusCode": 412},
                },
                "PutObject",
            )
        self.objects[Key] = Body

    def get_object(self, Bucket, Key):
        return {"Body": io.BytesIO(self.objects[Key])}


def test_probe_proves_conditional_rejection_and_reloads_independent_copy(tmp_path):
    bucket = Bucket()
    result = validation.probe_object(
        bucket, "private", "development/check/probe", tmp_path
    )
    assert result["overwrite_http_status"] == 412
    assert result["bytes"] > 0
    bucket.objects.clear()
    copy = validation.LocalCopy(tmp_path)
    assert copy.get_object(Bucket="ignored", Key="development/check/probe")[
        "Body"
    ].read()


def test_probe_does_not_accept_connection_error_as_overwrite_protection(tmp_path):
    class Broken(Bucket):
        def put_object(self, **kwargs):
            if kwargs["Key"] in self.objects:
                raise ConnectionError("secret endpoint")
            return super().put_object(**kwargs)

    with pytest.raises(ConnectionError):
        validation.probe_object(
            Broken(), "private", "development/check/probe", tmp_path
        )


@pytest.mark.parametrize(
    "name",
    [
        "railway",
        "forecast_validation_",
        "forecast_validation_x;drop database railway",
        "production",
    ],
)
def test_refuses_existing_service_database_names(name):
    with pytest.raises(ValueError):
        validation.validate_database_name(name)


def test_local_copy_rejects_path_traversal(tmp_path):
    with pytest.raises(ValueError):
        validation.LocalCopy(tmp_path).get_object(Bucket="ignored", Key="../../secret")


def test_s3_transfer_counts_include_duplicate_reads_and_rejected_write():
    client = validation.MeasuredS3(Bucket())
    client.put_object(Bucket="private", Key="key", Body=b"abc", IfNoneMatch="*")
    with pytest.raises(ClientError):
        client.put_object(Bucket="private", Key="key", Body=b"attempt", IfNoneMatch="*")
    for _ in range(2):
        assert client.get_object(Bucket="private", Key="key")["Body"].read() == b"abc"
    assert client.upload_payload_bytes == 10
    assert client.download_bytes == 6


def test_fixture_workflow_uses_real_postgres_and_offline_artifacts(tmp_path):
    import psycopg
    from psycopg import sql
    from psycopg.conninfo import conninfo_to_dict, make_conninfo
    from forecast.storage_artifacts import ArtifactRepository

    url = os.environ.get("FORECAST_VALIDATION_TEST_DATABASE_URL")
    if not url:
        pytest.skip("Set FORECAST_VALIDATION_TEST_DATABASE_URL for local PostgreSQL")
    assert conninfo_to_dict(url)["host"] in ("localhost", "127.0.0.1")
    name = "forecast_validation_" + uuid.uuid4().hex[:12]
    with psycopg.connect(url, autocommit=True) as admin:
        admin.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(name)))
        try:
            with psycopg.connect(
                make_conninfo(url, dbname=name), autocommit=True
            ) as connection:
                for migration in ("001_storage", "002_jobs"):
                    connection.execute(
                        (
                            Path(__file__).parent / "migrations" / f"{migration}.up.sql"
                        ).read_text()
                    )
                bucket = Bucket()
                result = validation.exercise(
                    connection, ArtifactRepository(bucket, "private"), tmp_path, name
                )
                assert result["rollback"]
                assert result["scoring"]["scores"] == 1
                assert (
                    connection.execute(
                        "SELECT count(*) FROM forecast.emissions"
                    ).fetchone()[0]
                    == 1
                )
                for key in bucket.objects:
                    validation.backup_object(
                        bucket, "private", key, tmp_path / "backup"
                    )
                bucket.objects.clear()
                local = validation.LocalCopy(tmp_path / "backup")
                manifest, prefix = connection.execute(
                    "SELECT manifest,artifact_prefix FROM forecast.versions LIMIT 1"
                ).fetchone()
                restored_model = ArtifactRepository(local, "offline").materialize(
                    prefix, manifest["storage_sha256"], tmp_path / "reloaded"
                )
                assert len(restored_model.predict([100, 101], 1)) == 52
        finally:
            admin.execute(sql.SQL("DROP DATABASE {}").format(sql.Identifier(name)))
