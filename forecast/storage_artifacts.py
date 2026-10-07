"""Private S3 artifact transport using an injected boto3 S3 client."""

import hashlib
import json
import re
from pathlib import Path


def digest(content):
    return hashlib.sha256(content).hexdigest()


def filenames(manifest):
    names = list(manifest["files"])
    if not names or any(
        Path(name).name != name
        or "/" in name
        or "\\" in name
        or name in (".", "..", "manifest.json")
        for name in names
    ):
        raise ValueError("Unsafe artifact filename")
    return names


class ArtifactRepository:
    def __init__(self, client, bucket):
        self.client = client
        self.bucket = bucket

    def upload(self, directory, prefix):
        self.validate_prefix(prefix)
        directory = Path(directory)
        content = (directory / "manifest.json").read_bytes()
        manifest = json.loads(content)
        objects = {}
        for name in filenames(manifest):
            body = (directory / name).read_bytes()
            if digest(body) != manifest["files"][name]:
                raise ValueError("Artifact checksum mismatch")
            objects[name] = body
        objects["manifest.json"] = content
        for name, body in objects.items():
            self.client.put_object(
                Bucket=self.bucket, Key=f"{prefix}/{name}", Body=body, IfNoneMatch="*"
            )
            saved = self.client.get_object(Bucket=self.bucket, Key=f"{prefix}/{name}")[
                "Body"
            ].read()
            if digest(saved) != digest(body):
                raise ValueError("Stored artifact checksum mismatch")
        return digest(content)

    def materialize(self, prefix, manifest_sha256, directory):
        self.validate_prefix(prefix)
        from forecast.artifacts import load_model

        directory = Path(directory)
        directory.mkdir(parents=True, exist_ok=False)
        content = self.client.get_object(
            Bucket=self.bucket, Key=f"{prefix}/manifest.json"
        )["Body"].read()
        if digest(content) != manifest_sha256:
            raise ValueError("Manifest checksum mismatch")
        manifest = json.loads(content)
        for name in filenames(manifest):
            body = self.client.get_object(Bucket=self.bucket, Key=f"{prefix}/{name}")[
                "Body"
            ].read()
            if digest(body) != manifest["files"][name]:
                raise ValueError("Artifact checksum mismatch")
            (directory / name).write_bytes(body)
        (directory / "manifest.json").write_bytes(content)
        return load_model(directory)

    @staticmethod
    def validate_prefix(prefix):
        if not re.fullmatch(
            r"(development|production)/[A-Za-z0-9_-]+(?:/[A-Za-z0-9_-]+)*", prefix
        ):
            raise ValueError("Artifact prefix must identify an environment and version")
