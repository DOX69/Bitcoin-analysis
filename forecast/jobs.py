"""Bounded forecast jobs following the existing ingestion cron."""

from datetime import date, datetime, timedelta, timezone
import math
import statistics
import hashlib
import json
from pathlib import Path
import tempfile

from forecast.benchmark import aggregate_daily_rows, _wis

JOB_LOCK = 7_319_941_903_106_202_609


class DatabaseSource:
    def __init__(self, connection, daily_schema, bronze_schema, now):
        self.connection = connection
        self.daily_schema = daily_schema
        self.bronze_schema = bronze_schema
        self.now = now

    def daily(self, cutoff):
        from psycopg import sql

        rows = self.connection.execute(
            sql.SQL(
                """
            SELECT d.date_prices,d.close_usd,b.close,b.ingest_date_time
            FROM {}.obt_fact_day_btc d LEFT JOIN LATERAL (
                SELECT close,ingest_date_time FROM {}.btc_usd_ohlcv
                WHERE date=d.date_prices AND ingest_date_time <= %s
                ORDER BY ingest_date_time DESC LIMIT 1
            ) b ON true WHERE d.date_prices <= %s ORDER BY d.date_prices
        """
            ).format(
                sql.Identifier(self.daily_schema), sql.Identifier(self.bronze_schema)
            ),
            (self.now.replace(tzinfo=None), cutoff),
        ).fetchall()
        observations = []
        for day, close, source_close, ingested in rows:
            if source_close is None or float(source_close) != float(close):
                raise ValueError("Daily close does not match its known source revision")
            observed_at = ingested.replace(tzinfo=timezone.utc).isoformat()
            observations.append(
                {
                    "date": day.isoformat(),
                    "close": float(close),
                    "revision": hashlib.sha256(
                        f"{day}:{close!r}:{observed_at}".encode()
                    ).hexdigest(),
                    "source": f"{self.bronze_schema}.btc_usd_ohlcv",
                    "observed_at": observed_at,
                }
            )
        return observations

    def fx(self, cutoff):
        from psycopg import sql

        rates = {}
        for currency in ("EUR", "CHF"):
            row = self.connection.execute(
                sql.SQL(
                    "SELECT date,rate FROM {}.{} WHERE date <= %s AND ingest_date_time <= %s ORDER BY date DESC,ingest_date_time DESC LIMIT 1"
                ).format(
                    sql.Identifier(self.bronze_schema),
                    sql.Identifier(f"usd_{currency.lower()}_rates"),
                ),
                (cutoff, self.now.replace(tzinfo=None)),
            ).fetchone()
            if row is None:
                raise ValueError("Missing known FX observation")
            rates[currency] = {"date": row[0].isoformat(), "rate": float(row[1])}
        return rates


def artifact_loader(repository, environment):
    def load(manifest, prefix, origin):
        if environment not in ("development", "production") or not prefix.startswith(
            environment + "/"
        ):
            raise ValueError("Artifact environment mismatch")
        trained = date.fromisoformat(manifest["context"]["last_week"])
        if trained > origin:
            raise ValueError("Model trained with future observations")
        with tempfile.TemporaryDirectory(prefix="forecast-artifact-") as directory:
            path = Path(directory) / "model"
            candidate = repository.materialize(prefix, manifest["storage_sha256"], path)
            downloaded = json.loads((path / "manifest.json").read_text())
            if downloaded != {
                key: value for key, value in manifest.items() if key != "storage_sha256"
            }:
                raise ValueError(
                    "Registered manifest differs from verified artifact manifest"
                )
            return candidate

    return load


def persist_snapshot(repository, prefix, document):
    repository.validate_prefix(prefix)
    content = json.dumps(document, sort_keys=True, allow_nan=False).encode()
    digest = hashlib.sha256(content).hexdigest()
    key = f"{prefix}/snapshots/{digest}.json"
    try:
        repository.client.put_object(
            Bucket=repository.bucket, Key=key, Body=content, IfNoneMatch="*"
        )
    except Exception:
        # A replay or uncertain upload may already have stored the exact bytes.
        existing = repository.client.get_object(Bucket=repository.bucket, Key=key)[
            "Body"
        ].read()
        if existing != content:
            raise ValueError("Conflicting immutable snapshot")
    saved = repository.client.get_object(Bucket=repository.bucket, Key=key)[
        "Body"
    ].read()
    if hashlib.sha256(saved).hexdigest() != digest:
        raise ValueError("Stored snapshot checksum mismatch")
    return {"key": key, "sha256": digest}


def run_batch(
    connection,
    *,
    now,
    evidence,
    daily_loader,
    fx_loader,
    candidate_loader,
    snapshot_writer,
    cost,
):
    """One durable attempt per Monday/Tuesday; scoring also catches up on other days.

    The caller must supervise this entire worker with the combined 300-second limit.
    Loaders are called only after the ingestion/dbt run succeeded.
    """
    if not connection.autocommit:
        raise ValueError(
            "Job connection must use autocommit for durable attempt claims"
        )
    if evidence not in ("prospective", "fixture", "historical_replay"):
        raise ValueError("Explicit forecast evidence is required")
    slot = emission_slot(now)
    check_cost(cost, now)
    if not connection.execute(
        "SELECT pg_try_advisory_lock(%s)", (JOB_LOCK,)
    ).fetchone()[0]:
        return {"emission": "locked", "scores": 0}
    result = {"emission": "outside_window", "scores": 0}
    try:
        if slot:
            result["emission"] = _emit(
                connection,
                now,
                slot,
                daily_loader,
                fx_loader,
                candidate_loader,
                snapshot_writer,
                evidence,
            )
        try:
            result["scores"] = _score_mature(connection, now, daily_loader)
            month = (now.date().replace(day=1) - timedelta(days=1)).strftime("%Y-%m")
            for (identifier,) in connection.execute(
                "SELECT id FROM forecast.versions"
            ).fetchall():
                report = monthly_report(connection, identifier, month)
                connection.execute(
                    "INSERT INTO forecast.reports(version_id,month,report) VALUES (%s,%s,%s::jsonb) ON CONFLICT DO NOTHING",
                    (identifier, month + "-01", json.dumps(report, allow_nan=False)),
                )
        except Exception as error:
            result["scoring_error"] = type(error).__name__
        return result
    finally:
        connection.execute("SELECT pg_advisory_unlock(%s)", (JOB_LOCK,))


def _emit(
    connection,
    now,
    slot,
    daily_loader,
    fx_loader,
    candidate_loader,
    snapshot_writer,
    evidence,
):
    from forecast.artifacts import emit_forecast
    from forecast.storage import ForecastStore

    origin, status = slot
    if connection.execute(
        "SELECT id FROM forecast.emissions WHERE origin_week=%s", (origin,)
    ).fetchone():
        return "already_published"
    active = connection.execute(
        "SELECT v.id,v.manifest,v.artifact_prefix FROM forecast.publication p JOIN forecast.versions v ON v.id=p.active_version WHERE NOT v.withdrawn"
    ).fetchone()
    if active is None:
        return "no_active_version"
    claimed = connection.execute(
        "INSERT INTO forecast.attempts(origin_week,attempt_day,started_at,status) VALUES (%s,%s,%s,'started') ON CONFLICT DO NOTHING RETURNING origin_week",
        (origin, now.date(), now),
    ).fetchone()
    if not claimed:
        return "attempt_consumed"
    try:
        daily = daily_loader(origin + timedelta(days=6))
        weekly = fresh_weekly(daily, now)
        candidate = candidate_loader(active[1], active[2], origin)
        fx = fx_loader(now.date())
        payload = emit_forecast(candidate, weekly, now.date().isoformat(), fx)
        snapshot = snapshot_writer(
            active[2],
            {
                "daily": daily,
                "fx": fx,
                "read_at": now.isoformat(),
                "evidence": evidence,
            },
        )
        payload.update(
            {
                "model_version_id": active[0],
                "model_manifest_sha256": hashlib.sha256(
                    json.dumps(
                        active[1], sort_keys=True, separators=(",", ":")
                    ).encode()
                ).hexdigest(),
                "model_manifest": active[1],
                "origin_close": weekly[-1]["close"],
                "data_cutoff": (origin + timedelta(days=6)).isoformat(),
                "data_read_at": now.isoformat(),
                "snapshot_sha256": snapshot["sha256"],
                "snapshot_key": snapshot["key"],
                "evidence": evidence,
            }
        )
        ForecastStore(connection).publish_emission(active[0], payload, now, status)
        connection.execute(
            "UPDATE forecast.attempts SET status=%s,finished_at=%s WHERE origin_week=%s AND attempt_day=%s",
            (status, datetime.now(timezone.utc), origin, now.date()),
        )
        return status
    except Exception as error:
        connection.execute(
            "UPDATE forecast.attempts SET status='failed',finished_at=%s,error_type=%s WHERE origin_week=%s AND attempt_day=%s",
            (datetime.now(timezone.utc), type(error).__name__, origin, now.date()),
        )
        return "failed"


def _score_mature(connection, now, daily_loader):
    from forecast.storage import ForecastStore

    observations = {}
    for row in daily_loader(now.date() - timedelta(days=1)):
        key = str(row["date"])[:10]
        if key in observations:
            raise ValueError("Duplicate scoring observation")
        observations[key] = row
    count = 0
    store = ForecastStore(connection)
    for identifier, payload in connection.execute(
        "SELECT id,payload FROM forecast.emissions WHERE status != 'invalidated' ORDER BY created_at"
    ).fetchall():
        for point in payload["points"]:
            observation = observations.get(point["target_date"])
            metrics = score_point(
                point,
                observation,
                payload["origin_close"],
                now,
                evidence=payload.get("evidence", "unverified"),
            )
            if metrics is not None:
                count += store.record_score(
                    identifier,
                    point["horizon_weeks"],
                    observation["revision"],
                    observation["close"],
                    metrics,
                )
    return count


def emission_slot(now):
    if now.tzinfo is None or now.utcoffset() != timedelta(0):
        raise ValueError("Forecast clock must be UTC")
    if now.weekday() > 1:
        return None
    return now.date() - timedelta(days=now.weekday() + 7), (
        "valid" if now.weekday() == 0 else "delayed"
    )


def fresh_weekly(daily, now):
    monday = now.date() - timedelta(days=now.weekday())
    if any(date.fromisoformat(str(row["date"])[:10]) >= monday for row in daily):
        raise ValueError("Snapshot includes future or incomplete-week observations")
    weekly = aggregate_daily_rows(daily)
    if date.fromisoformat(weekly[-1]["date"]) != monday - timedelta(days=7):
        raise ValueError("Snapshot is not fresh")
    return weekly


def check_cost(record, now):
    if record.get("month") != now.strftime("%Y-%m"):
        raise ValueError("Forecast cost month is absent or stale")
    for key in ("measured_usd", "projected_usd"):
        value = record.get(key)
        if (
            not isinstance(value, (int, float))
            or not math.isfinite(value)
            or value < 0
            or value >= 5
        ):
            raise ValueError(
                "Forecast cost suspension: measured or projected total must be below 5 USD"
            )


def score_point(point, observation, origin_close, now, *, evidence="unverified"):
    target = date.fromisoformat(point["target_date"])
    if target >= now.date() or observation is None:
        return None
    actual = float(observation["close"])
    values = point["USD"]
    baseline_payload = point.get("baseline")
    baseline = (
        baseline_payload.get("USD")
        if isinstance(baseline_payload, dict)
        else [origin_close] * 5
    )
    if (
        str(observation["date"])[:10] != target.isoformat()
        or not observation.get("revision")
        or len(values) != 5
        or any(
            not math.isfinite(value) or value <= 0
            for value in [actual, origin_close, *values]
        )
        or values != sorted(values)
        or len(baseline) != 5
        or any(not math.isfinite(value) or value <= 0 for value in baseline)
        or baseline != sorted(baseline)
    ):
        raise ValueError("Invalid scoring observation, origin or quantiles")
    return {
        "mae": abs(actual - values[2]),
        "wis": _wis(actual, values),
        "coverage_50": int(values[1] <= actual <= values[3]),
        "coverage_80": int(values[0] <= actual <= values[4]),
        "width_50": values[3] - values[1],
        "width_80": values[4] - values[0],
        "naive_mae": abs(actual - origin_close),
        "naive_wis": _wis(actual, [origin_close] * 5),
        "baseline_probabilistic_mae": abs(actual - baseline[2]),
        "baseline_probabilistic_wis": _wis(actual, baseline),
        "baseline_probabilistic_coverage_50": int(baseline[1] <= actual <= baseline[3]),
        "baseline_probabilistic_coverage_80": int(baseline[0] <= actual <= baseline[4]),
        "baseline_probabilistic_width_50": baseline[3] - baseline[1],
        "baseline_probabilistic_width_80": baseline[4] - baseline[0],
        "mae_delta": abs(actual - values[2]) - abs(actual - baseline[2]),
        "wis_delta": _wis(actual, values) - _wis(actual, baseline),
        "regime": (
            "up"
            if actual > origin_close
            else "down" if actual < origin_close else "flat"
        ),
        "observation_revision": observation["revision"],
        "observation_source": observation.get("source"),
        "observation_known_at": observation.get("observed_at"),
        "evidence": evidence,
    }


def calibration_report(scores, month):
    rows = []
    for horizon in range(1, 53):
        metrics = [row["metrics"] for row in scores if row["horizon"] == horizon]
        rows.append(
            {
                "horizon_weeks": horizon,
                "origins": len(metrics),
                **{
                    key: (
                        statistics.mean(
                            value for m in metrics if (value := m.get(key)) is not None
                        )
                        if any(key in m for m in metrics)
                        else None
                    )
                    for key in (
                        "mae",
                        "wis",
                        "coverage_50",
                        "coverage_80",
                        "naive_mae",
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
                },
            }
        )
    return {
        "month": month,
        "per_horizon": rows,
        "action": "manual_review_only",
        "evidence_sources": {
            "selection": {"status": "not_included_in_prospective_report"},
            "final_holdout": {
                "status": "must_be_provided_separately",
                "publishable_from_this_report": False,
            },
            "prospective": {"status": "revisioned_scores"},
        },
    }


def check_promotion(report):
    rows = report.get("per_horizon", [])
    evidence_source = report.get("evidence_source") or report.get("evidence")
    final_holdout = report.get("final_holdout")
    if (
        report.get("candidate") not in ("gaussian_random_walk", "lightgbm_quantile")
        or evidence_source not in ("prospective", "final_holdout")
        or not report.get("confirmation_review")
        or report.get("manual_dependence_review") is not True
        or report.get("manual_regime_review") is not True
        or report.get("baseline_verified") is not True
        or report.get("data_verified") is not True
        or report.get("resources_verified") is not True
        or [row.get("horizon_weeks") for row in rows] != list(range(1, 53))
    ):
        raise ValueError("Refused promotion: incomplete evidence or ineligible recipe")
    if evidence_source == "final_holdout" and (
        not isinstance(final_holdout, dict)
        or final_holdout.get("status") != "available"
        or final_holdout.get("read_only_after_scores") is not True
        or final_holdout.get("selection_locked") is not True
    ):
        raise ValueError("Refused promotion: final holdout was not frozen and locked")
    active = report.get("active_per_horizon")
    if active is not None and [row.get("horizon_weeks") for row in active] != list(
        range(1, 53)
    ):
        raise ValueError("Refused promotion: incomplete active comparison")
    for index, row in enumerate(rows):
        if (
            type(row.get("origins")) is not int
            or row["origins"] < 104
            or sum(
                block.get("complete_contiguous", False)
                for block in row.get("dependence_blocks", [])
            )
            < 2
            or any(
                not isinstance(row.get(k), (float, int))
                or not math.isfinite(row[k])
                or row[k] < 0
                for k in ("mae", "wis", "naive_mae", "coverage_50", "coverage_80")
            )
            or row["mae"] > 1.05 * row["naive_mae"]
            or not 0.4 <= row["coverage_50"] <= 0.6
            or not 0.7 <= row["coverage_80"] <= 0.9
        ):
            raise ValueError("Refused promotion: horizon guardrail failed")
        if active is not None and any(
            not math.isfinite(active[index].get(k, math.nan))
            or active[index][k] < 0
            or row[k] > 1.05 * active[index][k]
            for k in ("wis", "mae")
        ):
            raise ValueError("Refused promotion: active horizon guardrail failed")
    if active is not None and sum(row["wis"] for row in rows) > 0.95 * sum(
        row["wis"] for row in active
    ):
        raise ValueError("Refused promotion: WIS gain below five percent")


def artifact_expired(now, *, protected, last_target, rejected_at):
    if protected:
        return False
    if last_target is not None:
        try:
            expires = last_target.replace(year=last_target.year + 2)
        except ValueError:
            expires = last_target.replace(year=last_target.year + 2, day=28)
        return now >= expires
    return rejected_at is not None and now >= rejected_at + timedelta(days=90)


def monthly_report(connection, version_id, month, *, evidence="prospective"):
    start = date.fromisoformat(month + "-01")
    end = (start.replace(day=28) + timedelta(days=4)).replace(day=1)
    rows = connection.execute(
        """
        SELECT DISTINCT ON (s.emission_id,s.horizon) s.horizon,s.metrics
        FROM forecast.scores s JOIN forecast.emissions e ON e.id=s.emission_id
        WHERE e.version_id=%s AND e.status != 'invalidated'
          AND s.metrics->>'evidence'=%s
          AND (e.payload->'points'->(s.horizon-1)->>'target_date')::date >= %s
          AND (e.payload->'points'->(s.horizon-1)->>'target_date')::date < %s
        ORDER BY s.emission_id,s.horizon,s.created_at DESC,s.observation_revision DESC
    """,
        (version_id, evidence, start, end),
    ).fetchall()
    return {
        **calibration_report([{"horizon": h, "metrics": m} for h, m in rows], month),
        "version_id": version_id,
        "evidence": evidence,
    }


def purge_artifacts(connection, now, delete_artifacts):
    """Delete only expired files, under the same lock as activation/publication.

    A shared prefix considers every referring version and emission. The callback
    must delete only the listed bundle objects and tolerate an already absent file.
    """
    purged = []
    with connection.transaction():
        active, rollback = connection.execute(
            "SELECT active_version,rollback_version FROM forecast.publication FOR UPDATE"
        ).fetchone()
        versions = connection.execute(
            "SELECT id,artifact_prefix,manifest FROM forecast.versions"
        ).fetchall()
        for identifier, prefix, manifest in versions:
            lifecycle = connection.execute(
                "SELECT rejected_at,purged_at FROM forecast.maintenance WHERE artifact_prefix=%s",
                (prefix,),
            ).fetchone()
            if lifecycle and lifecycle[1] is not None:
                continue
            target = connection.execute(
                """
                SELECT max((point->>'target_date')::date)
                FROM forecast.emissions e JOIN forecast.versions v ON v.id=e.version_id,
                jsonb_array_elements(e.payload->'points') point
                WHERE v.artifact_prefix=%s
            """,
                (prefix,),
            ).fetchone()[0]
            protected = any(
                v in (active, rollback) and p == prefix for v, p, _ in versions
            )
            if artifact_expired(
                now,
                protected=protected,
                last_target=target,
                rejected_at=lifecycle[0] if lifecycle else None,
            ):
                delete_artifacts(prefix, manifest)
                connection.execute(
                    "INSERT INTO forecast.maintenance(artifact_prefix,purged_at) VALUES (%s,now()) ON CONFLICT(artifact_prefix) DO UPDATE SET purged_at=excluded.purged_at",
                    (prefix,),
                )
                purged.append(prefix)
    return purged


def claim_quarter(connection, now, snapshot_sha256):
    quarter = now.date().replace(month=((now.month - 1) // 3) * 3 + 1, day=1)
    row = connection.execute(
        "INSERT INTO forecast.candidate_cycles(quarter,started_at,snapshot_sha256) VALUES (%s,%s,%s) ON CONFLICT DO NOTHING RETURNING quarter",
        (quarter, now, snapshot_sha256),
    ).fetchone()
    if row is None:
        raise ValueError(
            "A candidate cycle already started this quarter; no automatic retry"
        )


def register_bundle(store, repository, directory, version_id, environment):
    from forecast.artifacts import load_model

    if environment not in ("development", "production"):
        raise ValueError("Invalid artifact environment")
    load_model(directory)
    prefix = f"{environment}/{version_id}"
    storage_sha256 = repository.upload(directory, prefix)
    manifest = json.loads((Path(directory) / "manifest.json").read_text())
    manifest["storage_sha256"] = storage_sha256
    store.register_version(version_id, manifest, prefix)


def main(argv=None):
    import argparse
    import os

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "command",
        choices=(
            "worker",
            "quarterly",
            "report",
            "register",
            "check-promotion",
            "purge",
        ),
    )
    parser.add_argument("--config", type=Path)
    parser.add_argument("--directory", type=Path)
    parser.add_argument("--snapshot", type=Path)
    parser.add_argument("--report", type=Path)
    parser.add_argument("--version-id")
    parser.add_argument("--month")
    args = parser.parse_args(argv)
    try:
        if args.command == "check-promotion":
            check_promotion(json.loads(args.report.read_text()))
            print(
                json.dumps(
                    {"status": "numeric_checks_passed_manual_activation_required"}
                )
            )
            return 0
        config = json.loads(args.config.read_text())
        now = datetime.now(timezone.utc)
        cost = json.loads(Path(config["cost_record"]).read_text())
        check_cost(cost, now)
        import psycopg

        with psycopg.connect(os.environ["DATABASE_URL"], autocommit=True) as connection:
            if args.command == "quarterly":
                from forecast.pipeline import prepare_run, execute_run

                if config["environment"] != "development":
                    raise ValueError("Candidate cycles require Development")
                digest = hashlib.sha256(args.snapshot.read_bytes()).hexdigest()
                claim_quarter(connection, now, digest)
                prepare_run(args.snapshot, args.directory)
                execute_run(args.directory)
                result = {"status": "candidate_cycle_complete_no_promotion"}
            elif args.command == "report":
                result = monthly_report(connection, args.version_id, args.month)
            else:
                import boto3
                from forecast.storage_artifacts import ArtifactRepository, filenames

                client = boto3.client(
                    "s3", endpoint_url=os.environ["FORECAST_S3_ENDPOINT_URL"]
                )
                repository = ArtifactRepository(client, config["artifact_bucket"])
                if args.command == "register":
                    from forecast.storage import ForecastStore

                    register_bundle(
                        ForecastStore(connection),
                        repository,
                        args.directory,
                        args.version_id,
                        config["environment"],
                    )
                    result = {"status": "registered_inactive"}
                elif args.command == "purge":

                    def delete(prefix, manifest):
                        repository.validate_prefix(prefix)
                        if not prefix.startswith(config["environment"] + "/"):
                            raise ValueError("Artifact environment mismatch")
                        for name in [*filenames(manifest), "manifest.json"]:
                            client.delete_object(
                                Bucket=config["artifact_bucket"], Key=f"{prefix}/{name}"
                            )

                    result = {"purged": purge_artifacts(connection, now.date(), delete)}
                else:
                    import psutil

                    process = psutil.Process()
                    process.cpu_affinity(process.cpu_affinity()[:2])
                    source = DatabaseSource(
                        connection,
                        config["daily_schema"],
                        config.get("bronze_schema", "bronze"),
                        now,
                    )
                    result = run_batch(
                        connection,
                        now=now,
                        evidence="prospective",
                        daily_loader=source.daily,
                        fx_loader=source.fx,
                        candidate_loader=artifact_loader(
                            repository, config["environment"]
                        ),
                        snapshot_writer=lambda prefix, document: persist_snapshot(
                            repository, prefix, document
                        ),
                        cost=cost,
                    )
            print(json.dumps(result, allow_nan=False))
            return int(result.get("emission") == "failed" or "scoring_error" in result)
    except Exception as error:
        # Database and S3 exception text can contain connection details.
        print(json.dumps({"status": "failed", "error_type": type(error).__name__}))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
