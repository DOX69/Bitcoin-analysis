import hashlib
import io
import json
import pytest
from forecast.storage_artifacts import ArtifactRepository


class Bucket:
    def __init__(self):
        self.objects = {}

    def put_object(self, Bucket, Key, Body, IfNoneMatch):
        assert IfNoneMatch == "*"
        if Key in self.objects:
            raise ValueError("exists")
        self.objects[Key] = Body

    def get_object(self, Bucket, Key):
        return {"Body": io.BytesIO(self.objects[Key])}


def test_upload_checks_integrity_and_never_overwrites(tmp_path):
    (tmp_path / "state.json").write_bytes(b"{}")
    manifest = {"files": {"state.json": hashlib.sha256(b"{}").hexdigest()}}
    (tmp_path / "manifest.json").write_text(json.dumps(manifest))
    bucket = Bucket()
    repository = ArtifactRepository(bucket, "private")
    digest = repository.upload(tmp_path, "development/v1")
    assert len(digest) == 64
    with pytest.raises(ValueError):
        repository.upload(tmp_path, "development/v1")
    (tmp_path / "state.json").write_bytes(b"bad")
    with pytest.raises(ValueError):
        repository.upload(tmp_path, "development/v2")


def test_rejects_manifest_path_escape(tmp_path):
    (tmp_path / "manifest.json").write_text(json.dumps({"files": {"../secret": "abc"}}))
    with pytest.raises(ValueError):
        ArtifactRepository(Bucket(), "private").upload(tmp_path, "development/v1")


@pytest.mark.parametrize(
    "prefix", ["", "/production/v1", "development/../v1", "development//v1", "v1"]
)
def test_rejects_unsafe_prefix(prefix):
    with pytest.raises(ValueError):
        ArtifactRepository.validate_prefix(prefix)
