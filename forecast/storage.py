"""Durable PostgreSQL forecast data, separate from dbt output."""

from datetime import date, timedelta, timezone
import hashlib
import json
import math
import uuid


def validate_emission(payload, created_at):
    if created_at.tzinfo is None:
        raise ValueError("Creation timestamp must have a timezone")
    if "model_manifest" in payload:
        if not payload.get("model_version_id") or not payload.get(
            "model_manifest_sha256"
        ):
            raise ValueError("Model version and manifest are required together")
        expected_manifest_hash = hashlib.sha256(
            json.dumps(
                payload["model_manifest"], sort_keys=True, separators=(",", ":")
            ).encode()
        ).hexdigest()
        if payload["model_manifest_sha256"] != expected_manifest_hash:
            raise ValueError("Model manifest checksum mismatch")
    emitted = date.fromisoformat(payload["emission_date"])
    origin = date.fromisoformat(payload["origin_week"])
    if (
        emitted != created_at.astimezone(timezone.utc).date()
        or origin.weekday() != 0
        or emitted < origin + timedelta(days=7)
    ):
        raise ValueError("Invalid emission origin or creation date")
    if (
        payload["quantiles"] != [0.1, 0.25, 0.5, 0.75, 0.9]
        or len(payload["points"]) != 52
    ):
        raise ValueError("Expected five quantiles and 52 horizons")
    rates = {"USD": 1.0}
    for currency, fx in payload["fx"].items():
        if (
            currency not in ("EUR", "CHF")
            or date.fromisoformat(fx["date"]) > emitted
            or not math.isfinite(fx["rate"])
            or fx["rate"] <= 0
        ):
            raise ValueError("Invalid frozen FX")
        rates[currency] = fx["rate"]
    for h, point in enumerate(payload["points"], 1):
        if (
            point["horizon_weeks"] != h
            or point["target_date"] != (origin + timedelta(days=6, weeks=h)).isoformat()
        ):
            raise ValueError("Invalid target")
        for currency, rate in rates.items():
            values = point.get(currency, [])
            if (
                len(values) != 5
                or any(not math.isfinite(v) or v <= 0 for v in values)
                or values != sorted(values)
            ):
                raise ValueError("Invalid quantiles")
            if any(
                not math.isclose(v, usd * rate, rel_tol=1e-10)
                for v, usd in zip(values, point["USD"])
            ):
                raise ValueError("Quantiles differ from frozen FX")
        baseline = point.get("baseline")
        if baseline is not None:
            values = baseline.get("USD") if isinstance(baseline, dict) else None
            if (
                not isinstance(baseline, dict)
                or baseline.get("name") != "probabilistic_last_close_reference"
                or not isinstance(values, list)
                or len(values) != 5
                or any(not math.isfinite(v) or v <= 0 for v in values)
                or values != sorted(values)
                or not math.isclose(values[2], payload["origin_close"], rel_tol=1e-10)
            ):
                raise ValueError("Invalid probabilistic baseline")


class ForecastStore:
    def __init__(self, connection):
        self.connection = connection

    def register_version(self, version_id, manifest, artifact_prefix):
        from forecast.artifacts import FEATURES
        from forecast.evaluation import version_signature

        if (
            manifest.get("schema_version") != 1
            or manifest.get("features") != FEATURES
            or manifest.get("recalibration") is not None
            or manifest.get("quantiles") != [0.1, 0.25, 0.5, 0.75, 0.9]
            or manifest.get("horizons") != list(range(1, 53))
            or not manifest.get("files")
            or (
                "version" in manifest
                and manifest["version"] != version_signature(manifest)
            )
        ):
            raise ValueError("Unsupported artifact manifest")
        with self.connection.transaction():
            self.connection.execute(
                "INSERT INTO forecast.versions(id,manifest,artifact_prefix) VALUES (%s,%s::jsonb,%s)",
                (version_id, json.dumps(manifest, allow_nan=False), artifact_prefix),
            )

    def activate_version(self, version_id, verify_artifacts):
        with self.connection.transaction():
            self.connection.execute("SELECT * FROM forecast.publication FOR UPDATE")
            row = self.connection.execute(
                "SELECT manifest,artifact_prefix FROM forecast.versions WHERE id=%s AND NOT withdrawn",
                (version_id,),
            ).fetchone()
            if not row:
                raise ValueError("Unknown or withdrawn version")
            verify_artifacts(row[0], row[1])
            self.connection.execute(
                "UPDATE forecast.publication SET rollback_version=active_version,active_version=%s WHERE active_version IS DISTINCT FROM %s",
                (version_id, version_id),
            )

    def rollback(self, verify_artifacts):
        with self.connection.transaction():
            row = self.connection.execute(
                "SELECT rollback_version FROM forecast.publication FOR UPDATE"
            ).fetchone()
            if not row[0]:
                raise ValueError("No rollback version")
            version = self.connection.execute(
                "SELECT manifest,artifact_prefix FROM forecast.versions WHERE id=%s AND NOT withdrawn",
                (row[0],),
            ).fetchone()
            if not version:
                raise ValueError("Rollback version withdrawn")
            verify_artifacts(version[0], version[1])
            self.connection.execute(
                "UPDATE forecast.publication SET active_version=rollback_version,rollback_version=active_version"
            )

    def publish_emission(self, version_id, payload, created_at, status="valid"):
        validate_emission(payload, created_at)
        if status not in ("valid", "delayed"):
            raise ValueError("Invalid initial status")
        with self.connection.transaction():
            active = self.connection.execute(
                "SELECT active_version FROM forecast.publication FOR UPDATE"
            ).fetchone()[0]
            if active != version_id:
                raise ValueError("Version is not active")
            if self.connection.execute(
                "SELECT withdrawn FROM forecast.versions WHERE id=%s", (version_id,)
            ).fetchone()[0]:
                raise ValueError("Version is withdrawn")
            existing = self.connection.execute(
                "SELECT id,payload FROM forecast.emissions WHERE origin_week=%s",
                (payload["origin_week"],),
            ).fetchone()
            if existing:
                if existing[1] != payload:
                    raise ValueError("Conflicting emission replay")
                return existing[0]
            identifier = str(uuid.uuid4())
            row = self.connection.execute(
                "INSERT INTO forecast.emissions(id,version_id,origin_week,emission_date,created_at,status,payload) VALUES (%s,%s,%s,%s,%s,%s,%s::jsonb) ON CONFLICT(origin_week) DO NOTHING RETURNING id",
                (
                    identifier,
                    version_id,
                    payload["origin_week"],
                    payload["emission_date"],
                    created_at,
                    status,
                    json.dumps(payload, allow_nan=False),
                ),
            ).fetchone()
            return (
                row[0]
                if row
                else self.connection.execute(
                    "SELECT id FROM forecast.emissions WHERE origin_week=%s",
                    (payload["origin_week"],),
                ).fetchone()[0]
            )

    def record_score(
        self, emission_id, horizon, observation_revision, observed, metrics
    ):
        if not observation_revision or not math.isfinite(observed) or observed <= 0:
            raise ValueError("Invalid observation")
        with self.connection.transaction():
            return (
                self.connection.execute(
                    "INSERT INTO forecast.scores(emission_id,horizon,observation_revision,observed,metrics) VALUES (%s,%s,%s,%s,%s::jsonb) ON CONFLICT DO NOTHING RETURNING emission_id",
                    (
                        emission_id,
                        horizon,
                        observation_revision,
                        observed,
                        json.dumps(metrics, allow_nan=False),
                    ),
                ).fetchone()
                is not None
            )
