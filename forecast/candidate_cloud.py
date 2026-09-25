"""Development-only prospective collection for a production-compatible candidate."""

import argparse
from datetime import date, datetime, timedelta, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import tempfile

from forecast import benchmark as b
from forecast import evaluation
from forecast.artifacts import emit_forecast, save_model, validate_prediction
from forecast.backups import configured_repositories, digest, put_verified, read
from forecast.jobs import DatabaseSource, check_cost

PREFIX = "development/research/lightgbm-v1"
MODEL_PREFIX = f"{PREFIX}/bundle/model"
BUDGET_PREFIX = "development/research/hybrid-v1"
LOCK = 7_319_941_903_106_202_613
MINIMUM_ORIGINS = 104
MODEL_NAME = "lightgbm_quantile"


def encode(value):
    return (json.dumps(value, sort_keys=True, allow_nan=False) + "\n").encode()


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def keys(repository, prefix):
    return sorted(
        item["Key"]
        for page in repository.client.get_paginator("list_objects_v2").paginate(
            Bucket=repository.bucket, Prefix=prefix + "/"
        )
        for item in page.get("Contents", [])
    )


def save(repository, key, value):
    return put_verified(repository, key, encode(value))


def _copy_prefix(source, backup, prefix):
    for key in keys(source, prefix):
        put_verified(backup, key, read(source, key))


def _weekly_snapshot(daily):
    if not daily:
        raise ValueError("Research source is empty")
    weekly = b.aggregate_daily_rows(daily)
    if not weekly:
        raise ValueError("Research source has no complete week")
    return weekly


def _model_manifest(source):
    content = read(source, f"{MODEL_PREFIX}/manifest.json")
    return json.loads(content), digest(content)


def _load_model(source, manifest_sha):
    parent = Path(tempfile.mkdtemp(prefix="lightgbm-research-model-"))
    directory = parent / "model"
    try:
        model = source.materialize(MODEL_PREFIX, manifest_sha, directory)
        if model.name != MODEL_NAME:
            raise ValueError("Research bundle contains the wrong candidate")
        return model, directory
    except Exception:
        for path in directory.glob("*"):
            path.unlink(missing_ok=True)
        directory.rmdir() if directory.exists() else None
        parent.rmdir()
        raise


def _ensure_model(source, backup, weekly, snapshot_key, snapshot_sha, now):
    bootstrap_key = f"{PREFIX}/bundle/bootstrap.json"
    existing = keys(source, MODEL_PREFIX)
    if existing:
        manifest, manifest_sha = _model_manifest(source)
        if bootstrap_key not in keys(source, f"{PREFIX}/bundle"):
            raise ValueError("Candidate model exists without its bootstrap receipt")
        bootstrap = json.loads(read(source, bootstrap_key))
        if bootstrap.get("model_manifest_sha256") != manifest_sha:
            raise ValueError("Candidate bootstrap does not match its model")
        if manifest.get("candidate") != MODEL_NAME:
            raise ValueError("Candidate model manifest is not LightGBM")
        _copy_prefix(source, backup, MODEL_PREFIX)
        put_verified(backup, bootstrap_key, read(source, bootstrap_key))
        return manifest, manifest_sha

    closes = [row["close"] for row in weekly]
    if len(closes) <= max(b.LOOKBACKS) + b.MAX_HORIZON:
        raise ValueError("Not enough weekly history to bootstrap candidate")
    candidate = b.LightGBMQuantileCandidate()
    candidate.fit(closes, len(closes))
    with tempfile.TemporaryDirectory(prefix="lightgbm-research-bundle-") as directory:
        model_directory = Path(directory) / "model"
        manifest = save_model(
            candidate,
            model_directory,
            {
                "evidence": "development_prospective_bootstrap",
                "last_week": weekly[-1]["date"],
                "snapshot_key": snapshot_key,
                "snapshot_sha256": snapshot_sha,
            },
        )
        manifest_sha = source.upload(model_directory, MODEL_PREFIX)
        backup.upload(model_directory, MODEL_PREFIX)
    save(
        source,
        bootstrap_key,
        {
            "created_at": now.isoformat(),
            "candidate": MODEL_NAME,
            "model_manifest_sha256": manifest_sha,
            "training_snapshot_key": snapshot_key,
            "training_snapshot_sha256": snapshot_sha,
            "training_last_week": weekly[-1]["date"],
        },
    )
    save(
        backup,
        bootstrap_key,
        json.loads(read(source, bootstrap_key)),
    )
    return manifest, manifest_sha


def make_emission(weekly, candidate, manifest_sha, now):
    if now.utcoffset() != timedelta(0) or now.weekday() not in (0, 1):
        raise ValueError("Emission requires Monday or Tuesday UTC")
    origin = date.fromisoformat(weekly[-1]["date"])
    if origin + timedelta(days=7) > now.date():
        raise ValueError("Latest completed week is missing")
    document = emit_forecast(candidate, weekly, now.date().isoformat())
    document.update(
        {
            "created_at": now.isoformat(),
            "candidate": MODEL_NAME,
            "model_manifest_sha256": manifest_sha,
            "evidence": "prospective",
            "emission_schema_version": 1,
        }
    )
    return document


def validate_emission(document, manifest_sha=None):
    manifest_sha = manifest_sha or document.get("model_manifest_sha256")
    if (
        document.get("candidate") != MODEL_NAME
        or document.get("model_manifest_sha256") != manifest_sha
        or document.get("evidence") != "prospective"
    ):
        raise ValueError("Mixed or non-prospective candidate evidence")
    created = datetime.fromisoformat(document["created_at"])
    origin = date.fromisoformat(document["origin_week"])
    if (
        created.utcoffset() != timedelta(0)
        or origin.weekday() != 0
        or not origin + timedelta(days=7)
        <= created.date()
        <= origin + timedelta(days=8)
        or document.get("quantiles") != list(b.QUANTILES)
        or not math.isfinite(document["origin_close"])
        or document["origin_close"] <= 0
    ):
        raise ValueError("Invalid candidate emission metadata")
    points = document.get("points", [])
    if [point.get("horizon_weeks") for point in points] != list(range(1, 53)):
        raise ValueError("Incomplete candidate horizons")
    validate_prediction([point["USD"] for point in points])
    for point in points:
        target = origin + timedelta(days=6, weeks=point["horizon_weeks"])
        baseline = point.get("baseline", {}).get("USD")
        if (
            point.get("target_date") != target.isoformat()
            or target <= created.date()
            or not isinstance(baseline, list)
            or len(baseline) != 5
            or any(not math.isfinite(value) or value <= 0 for value in baseline)
            or baseline != sorted(baseline)
        ):
            raise ValueError("Invalid candidate emission point")


def _observation_index(weekly):
    observations = {}
    for row in weekly:
        target = date.fromisoformat(row["date"]) + timedelta(days=6)
        if target in observations:
            raise ValueError("Duplicate scoring observation")
        close = float(row["close"])
        if not math.isfinite(close) or close <= 0:
            raise ValueError("Invalid scoring observation")
        observations[target] = {
            "close": close,
            "revision": row.get(
                "revision", hashlib.sha256(f"{target}:{close!r}".encode()).hexdigest()
            ),
            "source": row.get("source", "weekly_snapshot"),
            "observed_at": row.get("observed_at"),
        }
    return observations


def _summary(rows):
    keys_to_average = (
        "mae",
        "naive_mae",
        "wis",
        "coverage_50",
        "coverage_80",
        "width_50",
        "width_80",
        "baseline_probabilistic_mae",
        "baseline_probabilistic_wis",
        "baseline_probabilistic_coverage_50",
        "baseline_probabilistic_coverage_80",
        "baseline_probabilistic_width_50",
        "baseline_probabilistic_width_80",
        "mae_delta",
        "wis_delta",
    )
    return {
        "origins": len(rows),
        **{
            key: sum(row[key] for row in rows) / len(rows) if rows else None
            for key in keys_to_average
        },
    }


def _assessment(row):
    counts = (
        row["origins"] >= MINIMUM_ORIGINS
        and sum(block["complete_contiguous"] for block in row["dependence_blocks"]) >= 2
    )
    guardrails = (
        row["origins"] > 0
        and row["mae"] <= 1.05 * row["naive_mae"]
        and 0.4 <= row["coverage_50"] <= 0.6
        and 0.7 <= row["coverage_80"] <= 0.9
    )
    return {
        "minimum_counts_met": counts,
        "guardrails_passed": guardrails,
        "validation_status": (
            "insufficient_evidence"
            if not counts
            else "guardrails_met" if guardrails else "outside_guardrails"
        ),
    }


def score_emissions(documents, weekly, now, *, source_version=None, manifest_sha=None):
    if now.utcoffset() != timedelta(0):
        raise ValueError("Scoring requires UTC")
    observations = _observation_index(weekly)
    records = {h: [] for h in range(1, 53)}
    seen = set()
    for document in documents:
        validate_emission(document, manifest_sha or document["model_manifest_sha256"])
        if datetime.fromisoformat(document["created_at"]) > now:
            raise ValueError("Emission creation is in the future")
        origin = document["origin_week"]
        if origin in seen:
            raise ValueError("Duplicate emission origin")
        seen.add(origin)
        for point in document["points"]:
            target = date.fromisoformat(point["target_date"])
            if target >= now.date() or target not in observations:
                continue
            observation = observations[target]
            actual = observation["close"]
            row = point["USD"]
            baseline = point["baseline"]["USD"]
            records[point["horizon_weeks"]].append(
                {
                    "origin_week": origin,
                    "issued_at": document["created_at"],
                    "origin_close": document["origin_close"],
                    "target_date": target.isoformat(),
                    "actual": actual,
                    "prediction": row,
                    "mae": abs(actual - row[2]),
                    "naive_mae": abs(actual - document["origin_close"]),
                    "wis": b._wis(actual, row),
                    "coverage_50": float(row[1] <= actual <= row[3]),
                    "coverage_80": float(row[0] <= actual <= row[4]),
                    "width_50": row[3] - row[1],
                    "width_80": row[4] - row[0],
                    "baseline_prediction": baseline,
                    "baseline_probabilistic_mae": abs(actual - baseline[2]),
                    "baseline_probabilistic_wis": b._wis(actual, baseline),
                    "baseline_probabilistic_coverage_50": float(
                        baseline[1] <= actual <= baseline[3]
                    ),
                    "baseline_probabilistic_coverage_80": float(
                        baseline[0] <= actual <= baseline[4]
                    ),
                    "baseline_probabilistic_width_50": baseline[3] - baseline[1],
                    "baseline_probabilistic_width_80": baseline[4] - baseline[0],
                    "mae_delta": abs(actual - row[2]) - abs(actual - baseline[2]),
                    "wis_delta": b._wis(actual, row) - b._wis(actual, baseline),
                    "regime": evaluation.realized_regime(
                        actual, document["origin_close"]
                    ),
                    "observation_revision": observation["revision"],
                    "observation_source": observation["source"],
                    "observation_known_at": observation["observed_at"],
                    "source_version": source_version,
                }
            )
    per_horizon = []
    for horizon, rows in records.items():
        rows.sort(key=lambda row: row["origin_week"])
        blocks = []
        for start in range(0, len(rows), horizon):
            block = rows[start : start + horizon]
            contiguous = all(
                date.fromisoformat(right["origin_week"])
                - date.fromisoformat(left["origin_week"])
                == timedelta(weeks=1)
                for left, right in zip(block, block[1:])
            )
            blocks.append(
                {
                    "first_origin_week": block[0]["origin_week"],
                    "last_origin_week": block[-1]["origin_week"],
                    "origins": len(block),
                    "complete_contiguous": len(block) == horizon and contiguous,
                    **_summary(block),
                }
            )
        row = {
            "horizon_weeks": horizon,
            **_summary(rows),
            "dependence_blocks": blocks,
            "observations": rows,
        }
        row.update(_assessment(row))
        per_horizon.append(row)
    minimum_counts_met = all(row["minimum_counts_met"] for row in per_horizon)
    guardrails_passed = all(row["guardrails_passed"] for row in per_horizon)
    return {
        "created_at": now.isoformat(),
        "candidate": MODEL_NAME,
        "evidence": "prospective",
        "evidence_source": "prospective",
        "minimum_origins_per_horizon": MINIMUM_ORIGINS,
        "minimum_counts_met": minimum_counts_met,
        "guardrails_passed": guardrails_passed,
        "validation_status": (
            "insufficient_evidence"
            if not minimum_counts_met
            else "guardrails_met" if guardrails_passed else "outside_guardrails"
        ),
        "ready_for_confirmation_review": minimum_counts_met and guardrails_passed,
        "publishable": False,
        "limitations": "Prospective evidence only; confirmation review and manual promotion remain required.",
        "per_horizon": per_horizon,
        "observations": {str(horizon): rows for horizon, rows in records.items()},
        "evidence_sources": {
            "selection": {"status": "historical_research_only"},
            "final_holdout": {
                "status": "not_available",
                "reason": "No untouched historical period is claimed by this prospective collector",
            },
            "prospective": {
                "status": "immutable_emissions_and_revisioned_observations",
                "source_version": source_version,
            },
        },
    }


def _load_emissions(source, backup, candidate, manifest_sha, now):
    documents = []
    for key in keys(source, f"{PREFIX}/emissions"):
        envelope_bytes = read(source, key)
        envelope = json.loads(envelope_bytes)
        document = envelope["emission"]
        validate_emission(document, manifest_sha)
        snapshot_key = envelope["snapshot_key"]
        if not snapshot_key.startswith(f"{PREFIX}/snapshots/"):
            raise ValueError("Candidate snapshot outside its namespace")
        snapshot = read(source, snapshot_key)
        if digest(snapshot) != envelope["snapshot_sha256"]:
            raise ValueError("Candidate source snapshot changed")
        daily = json.loads(snapshot)
        expected = make_emission(
            _weekly_snapshot(daily),
            candidate,
            manifest_sha,
            datetime.fromisoformat(document["created_at"]),
        )
        if document != expected:
            raise ValueError("Candidate emission differs from its source replay")
        put_verified(backup, snapshot_key, snapshot)
        put_verified(backup, key, envelope_bytes)
        documents.append(document)
    return documents


def collect(source, backup, daily, now, *, emit=True):
    monday = now.date() - timedelta(days=now.weekday())
    if any(date.fromisoformat(str(row["date"])[:10]) >= monday for row in daily):
        raise ValueError("Research source includes an incomplete week")
    weekly = _weekly_snapshot(daily)
    snapshot = encode(daily)
    snapshot_key = f"{PREFIX}/snapshots/{digest(snapshot)}.json"
    put_verified(source, snapshot_key, snapshot)
    put_verified(backup, snapshot_key, snapshot)
    manifest, manifest_sha = _ensure_model(
        source, backup, weekly, snapshot_key, digest(snapshot), now
    )
    if manifest["context"]["last_week"] > weekly[-1]["date"]:
        raise ValueError("Candidate model was trained with future observations")
    model, model_directory = _load_model(source, manifest_sha)
    try:
        documents = _load_emissions(source, backup, model, manifest_sha, now)
        origin = weekly[-1]["date"]
        if (
            emit
            and now.weekday() in (0, 1)
            and not any(document["origin_week"] == origin for document in documents)
        ):
            document = make_emission(weekly, model, manifest_sha, now)
            save(
                source,
                f"{PREFIX}/emissions/{origin}.json",
                {
                    "emission": document,
                    "snapshot_key": snapshot_key,
                    "snapshot_sha256": digest(snapshot),
                },
            )
            save(
                backup,
                f"{PREFIX}/emissions/{origin}.json",
                json.loads(read(source, f"{PREFIX}/emissions/{origin}.json")),
            )
            documents.append(document)
        report = score_emissions(
            documents,
            weekly,
            now,
            source_version=digest(snapshot),
            manifest_sha=manifest_sha,
        )
        report["model_manifest_sha256"] = manifest_sha
        report["model_training_last_week"] = manifest["context"]["last_week"]
        report_key = f"{PREFIX}/reports/{now.strftime('%Y%m%dT%H%M%S%fZ')}.json"
        report_saved = save(source, report_key, report)
        save(backup, report_key, json.loads(read(source, report_key)))
        return {
            "status": "completed",
            "candidate": MODEL_NAME,
            "emissions": len(documents),
            "mature_points": sum(row["origins"] for row in report["per_horizon"]),
            "validation_status": report["validation_status"],
            "ready_for_confirmation_review": report["ready_for_confirmation_review"],
            "publishable": False,
            "report_key": report_key,
            "report_sha256": report_saved["sha256"],
            "independent_copy_verified": True,
        }
    finally:
        for path in model_directory.iterdir():
            path.unlink(missing_ok=True)
        model_directory.rmdir()
        model_directory.parent.rmdir()


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
        raise ValueError(
            "Candidate research worker is restricted to Railway Development"
        )
    process = psutil.Process()
    process.cpu_affinity(process.cpu_affinity()[:2])
    source, backup = configured_repositories(config)
    now = datetime.now(timezone.utc)
    check_cost(
        json.loads(
            read(source, f"{BUDGET_PREFIX}/budget/{now.strftime('%Y-%m')}.json")
        ),
        now,
    )
    with psycopg.connect(os.environ["DATABASE_URL"], autocommit=True) as connection:
        if not connection.execute(
            "SELECT pg_try_advisory_lock(%s)", (LOCK,)
        ).fetchone()[0]:
            print(json.dumps({"status": "already_running", "candidate": MODEL_NAME}))
            return
        try:
            monday = now.date() - timedelta(days=now.weekday())
            daily = DatabaseSource(
                connection, config["daily_schema"], config["bronze_schema"], now
            ).daily(monday - timedelta(days=1))
            print(
                json.dumps(
                    collect(
                        source,
                        backup,
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
