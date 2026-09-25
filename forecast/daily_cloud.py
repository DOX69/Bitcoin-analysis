"""Immutable daily-horizon preview, recalculated on Mondays in Development."""

import argparse
from datetime import datetime, timedelta, timezone
import json
import os
from pathlib import Path
from zoneinfo import ZoneInfo

from threadpoolctl import threadpool_limits

from forecast import daily_research as model
from forecast import evaluation
from forecast.backups import configured_repositories, digest, put_verified, read
from forecast.cloud_research import keys
from forecast.benchmark import _wis
from forecast.jobs import DatabaseSource, check_cost

LOCK = 7_319_941_903_106_202_613


def selection():
    selected = json.loads(Path(__file__).with_name("daily-selection.json").read_text())
    if (
        selected["model_manifest_sha256"] != model.MODEL_MANIFEST
        or selected["candidate"] not in ("holt", "ridge")
        or selected["production_ready"] is not False
    ):
        raise ValueError("Daily research selection mismatch")
    return selected


def collect(source, backup, rows, now, *, bootstrap=False):
    local = now.astimezone(ZoneInfo("Europe/Paris"))
    if not bootstrap and local.weekday() != 0:
        return {"status": "outside_monday"}
    origin = str(now.date() - timedelta(days=1))
    key = f"{model.PREFIX}/emissions/{origin}.json"
    # Reuse the original issuance, even after an uncertain upload or a restart.
    if key in keys(source, f"{model.PREFIX}/emissions"):
        content = read(source, key)
        envelope = json.loads(content)
        snapshot = read(source, envelope["snapshot_key"])
        if digest(snapshot) != envelope["snapshot_sha256"]:
            raise ValueError("Daily snapshot corrupted")
        put_verified(backup, envelope["snapshot_key"], snapshot)
        put_verified(backup, key, content)
        return {
            "status": "already_emitted",
            "report_key": key,
            "independent_copy_verified": True,
        }
    selected = selection()
    with threadpool_limits(limits=2):
        document = model.emission(rows, now, selected["candidate"])
    snapshot = model.encode(rows)
    snapshot_key = f"{model.PREFIX}/snapshots/{digest(snapshot)}.json"
    envelope = {
        "emission": document,
        "snapshot_key": snapshot_key,
        "snapshot_sha256": digest(snapshot),
        "selection": selected,
        "bootstrap": bootstrap,
    }
    for repository in (source, backup):
        put_verified(repository, snapshot_key, snapshot)
        put_verified(
            repository,
            f"{model.PREFIX}/recipes/{model.MODEL_MANIFEST}.json",
            model.encode(model.RECIPE),
        )
        put_verified(repository, key, model.encode(envelope))
    return {
        "status": "completed",
        "emissions": 1,
        "points": 365,
        "report_key": key,
        "independent_copy_verified": True,
    }


def score_existing(source, backup, rows, now):
    """Score completed target days without changing any issued distribution."""
    dates, _ = model.observations(rows)
    if dates[-1] >= now.date():
        raise ValueError("Cannot score an incomplete UTC day")
    actuals = {}
    for row in rows:
        if row["date"] in actuals:
            raise ValueError("Duplicate daily scoring observation")
        actuals[row["date"]] = row
    metrics = [[] for _ in range(365)]
    for key in keys(source, f"{model.PREFIX}/emissions"):
        content = read(source, key)
        document = json.loads(content)["emission"]
        if document["model_manifest_sha256"] != model.MODEL_MANIFEST:
            raise ValueError("Unknown daily model")
        if datetime.fromisoformat(document["created_at"]) > now:
            continue
        put_verified(backup, key, content)
        for point in document["points"]:
            if (
                point["target_date"] not in actuals
                or point["target_date"] >= now.date().isoformat()
            ):
                continue
            observation = actuals[point["target_date"]]
            value = float(observation["close"])
            q = point["USD"]
            baseline = point.get("baseline", {"USD": [document["origin_close"]] * 5})[
                "USD"
            ]
            metrics[point["horizon_days"] - 1].append(
                {
                    "mae": abs(q[2] - value),
                    "naive_mae": abs(document["origin_close"] - value),
                    "wis": _wis(value, q),
                    "coverage_50": int(q[1] <= value <= q[3]),
                    "coverage_80": int(q[0] <= value <= q[4]),
                    "width_50": q[3] - q[1],
                    "width_80": q[4] - q[0],
                    "baseline_probabilistic_mae": abs(baseline[2] - value),
                    "baseline_probabilistic_wis": _wis(value, baseline),
                    "baseline_probabilistic_coverage_50": int(
                        baseline[1] <= value <= baseline[3]
                    ),
                    "baseline_probabilistic_coverage_80": int(
                        baseline[0] <= value <= baseline[4]
                    ),
                    "baseline_probabilistic_width_50": baseline[3] - baseline[1],
                    "baseline_probabilistic_width_80": baseline[4] - baseline[0],
                    "mae_delta": abs(q[2] - value) - abs(baseline[2] - value),
                    "wis_delta": _wis(value, q) - _wis(value, baseline),
                    "regime": evaluation.realized_regime(
                        value, document["origin_close"]
                    ),
                    "observation_revision": observation.get("revision"),
                    "observation_source": observation.get("source"),
                    "observation_known_at": observation.get("observed_at"),
                }
            )
    snapshot = model.encode(rows)
    snapshot_key = f"{model.PREFIX}/snapshots/{digest(snapshot)}.json"

    def summary(values):
        return {
            "origins": len(values),
            **{
                key: (
                    sum(value[key] for value in values) / len(values)
                    if values
                    else None
                )
                for key in (
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
            },
        }

    per_horizon = []
    for i, values in enumerate(metrics):
        rolling = (
            [
                {"window_origins": width, **summary(values[-width:])}
                for width in sorted(
                    {min(26, len(values)), min(52, len(values)), min(104, len(values))}
                )
            ]
            if values
            else []
        )
        by_regime = {
            regime: summary([value for value in values if value["regime"] == regime])
            for regime in ("up", "down", "flat")
            if any(value["regime"] == regime for value in values)
        }
        per_horizon.append(
            {
                "horizon_days": i + 1,
                **summary(values),
                "rolling": rolling,
                "by_regime": by_regime,
            }
        )
    report = {
        "as_of": now.isoformat(),
        "evidence": "prospective",
        "production_ready": False,
        "snapshot_key": snapshot_key,
        "snapshot_sha256": digest(snapshot),
        "evidence_sources": {
            "selection": {"status": "historical_research_only"},
            "final_holdout": {
                "status": "not_available",
                "reason": "Daily preview history was already examined; prospective collection is separate",
                "maturity_horizon_days": 365,
            },
            "prospective": {
                "status": "immutable_emissions_and_revisioned_observations",
                "maturity": "completed UTC day only",
            },
        },
        "per_horizon": per_horizon,
    }
    report_key = f"{model.PREFIX}/reports/{now:%Y%m%dT%H%M%S%fZ}.json"
    for repository in (source, backup):
        put_verified(repository, snapshot_key, snapshot)
        put_verified(repository, report_key, model.encode(report))
    return {"mature_points": sum(map(len, metrics)), "score_report_key": report_key}


def main():
    import psutil
    import psycopg

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument(
        "--bootstrap",
        action="store_true",
        help="One initial issuance using the actual clock, outside Monday",
    )
    args = parser.parse_args()
    config = json.loads(args.config.read_text())
    if (
        config.get("environment") != "development"
        or os.environ.get("RAILWAY_ENVIRONMENT_NAME", "").lower() != "development"
    ):
        raise ValueError("Daily research requires Development")
    process = psutil.Process()
    process.cpu_affinity(process.cpu_affinity()[:2])
    now = datetime.now(timezone.utc)
    source, backup = configured_repositories(config)
    check_cost(
        json.loads(
            read(source, f"development/research/hybrid-v1/budget/{now:%Y-%m}.json")
        ),
        now,
    )
    with psycopg.connect(os.environ["DATABASE_URL"], autocommit=True) as connection:
        if not connection.execute(
            "SELECT pg_try_advisory_lock(%s)", (LOCK,)
        ).fetchone()[0]:
            print(json.dumps({"status": "already_running"}))
            return
        try:
            rows = DatabaseSource(
                connection, config["daily_schema"], config["bronze_schema"], now
            ).daily(now.date() - timedelta(days=1))
            result = collect(source, backup, rows, now, bootstrap=args.bootstrap)
            result.update(score_existing(source, backup, rows, now))
            print(json.dumps(result))
        finally:
            connection.execute("SELECT pg_advisory_unlock(%s)", (LOCK,))


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print(json.dumps({"status": "failed", "error_type": type(error).__name__}))
        raise SystemExit(1) from None
