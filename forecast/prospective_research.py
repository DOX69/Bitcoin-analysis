"""Append-only local observations for the frozen hybrid. No production activation."""

import argparse
from datetime import date, datetime, timedelta, timezone
import hashlib
import json
import math
from pathlib import Path

from forecast import benchmark as b
from forecast import hybrid_research as hybrid
from forecast.artifacts import dependencies, validate_prediction, write_json

MINIMUM_ORIGINS = 104
MODEL_MANIFEST = "3c8b3864ce908e1acdbb01c635ddd82eb1f61337b95c2c6a3d04377fb92d24c3"
DISTRIBUTION_HASH = "be7cb63eb804c813123c6918eae43a1201591e0b888e9e4a2ab490edb60e30bc"
LEGACY_SHADOW_HASH = "6e3b828e2b34b416ea4aee780d9db531b34917238e2ec4f018d16a54cfeb2aff"


def validation_status(minimum_counts_met, guardrails_passed):
    """Describe evidence without treating a small sample as model rejection."""
    if not minimum_counts_met:
        return "insufficient_evidence"
    return "guardrails_met" if guardrails_passed else "outside_guardrails"


def horizon_assessment(row):
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
        "validation_status": validation_status(counts, guardrails),
    }


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def frozen_distribution(bundle):
    if sha256(bundle / "manifest.json") != MODEL_MANIFEST:
        raise ValueError("Unrecognized frozen model manifest")
    manifest = json.loads((bundle / "manifest.json").read_text())
    if manifest["dependencies"] != dependencies():
        raise ValueError("Frozen model dependencies changed")
    for source in hybrid.sources():
        content = source.read_bytes().replace(b"\r\n", b"\n")
        # Git exports LF; the original Windows archive can contain CRLF.
        hashes = {
            hashlib.sha256(value).hexdigest()
            for value in (content, content.replace(b"\n", b"\r\n"))
        }
        if manifest["source_sha256"][source.name] not in hashes:
            raise ValueError("Frozen model source changed")
    if sha256(bundle / "standardized-distribution.json") != DISTRIBUTION_HASH:
        raise ValueError("Frozen distribution changed")
    return json.loads((bundle / "standardized-distribution.json").read_text())[
        "quantiles"
    ]


def make_emission(weekly, distribution, now, *, evidence):
    if now.utcoffset() != timedelta(0) or now.weekday() not in (0, 1):
        raise ValueError("Emission requires Monday or Tuesday UTC")
    monday = now.date() - timedelta(days=now.weekday())
    if not weekly or date.fromisoformat(weekly[-1]["date"]) != monday - timedelta(
        weeks=1
    ):
        raise ValueError("Latest completed week is missing")
    if evidence not in ("prospective", "fixture"):
        raise ValueError("Explicit evidence required")
    document = hybrid.shadow(weekly, distribution, now)
    document.update({"evidence": evidence, "model_manifest_sha256": MODEL_MANIFEST})
    return document


def validate_emission(document):
    if document.get("model_manifest_sha256") != MODEL_MANIFEST:
        raise ValueError("Mixed model versions")
    created = datetime.fromisoformat(document["created_at"])
    origin = date.fromisoformat(document["origin_week"])
    if (
        document.get("quantiles") != list(b.QUANTILES)
        or not math.isfinite(document["origin_close"])
        or document["origin_close"] <= 0
    ):
        raise ValueError("Invalid quantiles or origin price")
    if created.utcoffset() != timedelta(0) or origin.weekday() != 0:
        raise ValueError("Invalid UTC origin")
    legacy = (
        document.get("legacy_shadow_sha256") == LEGACY_SHADOW_HASH
        and document["created_at"] == "2026-09-10T18:03:51.868753+00:00"
        and document["origin_week"] == "2026-08-31"
    )
    if not legacy and not origin + timedelta(
        days=7
    ) <= created.date() <= origin + timedelta(days=8):
        raise ValueError("Emission was not created in its weekly slot")
    if document.get("evidence") != "prospective":
        raise ValueError(
            "Synthetic or historical evidence cannot be scored as prospective"
        )
    points = document["points"]
    if [point["horizon_weeks"] for point in points] != list(range(1, 53)):
        raise ValueError("Incomplete horizons")
    validate_prediction([point["USD"] for point in points])
    for point in points:
        expected = origin + timedelta(days=6, weeks=point["horizon_weeks"])
        if point["target_date"] != expected.isoformat() or expected <= created.date():
            raise ValueError("Invalid or nonfuture target at emission")


def score_emissions(documents, weekly, now):
    if now.utcoffset() != timedelta(0):
        raise ValueError("Scoring requires UTC")
    observations = {
        date.fromisoformat(row["date"]) + timedelta(days=6): row["close"]
        for row in weekly
    }
    records = {h: [] for h in range(1, 53)}
    seen = set()
    for document in documents:
        validate_emission(document)
        if datetime.fromisoformat(document["created_at"]) > now:
            raise ValueError("Emission creation is in the future")
        origin = document["origin_week"]
        if origin in seen:
            raise ValueError("Duplicate emission origin")
        seen.add(origin)
        for point in document["points"]:
            target = date.fromisoformat(point["target_date"])
            # The Sunday close is not complete until Monday 00:00 UTC.
            if target >= now.date() or target not in observations:
                continue
            row = point["USD"]
            actual = observations[target]
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
                }
            )
    per_horizon = []
    for h, rows in records.items():
        rows.sort(key=lambda row: row["origin_week"])
        metrics = {
            key: sum(row[key] for row in rows) / len(rows) if rows else None
            for key in ("mae", "naive_mae", "wis", "coverage_50", "coverage_80")
        }
        blocks = []
        for start in range(0, len(rows), h):
            block = rows[start : start + h]
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
                    "complete_contiguous": len(block) == h and contiguous,
                    **{
                        key: sum(row[key] for row in block) / len(block)
                        for key in metrics
                    },
                }
            )
        per_horizon.append(
            {
                "horizon_weeks": h,
                "origins": len(rows),
                **metrics,
                "dependence_blocks": blocks,
            }
        )
    for row in per_horizon:
        row.update(horizon_assessment(row))
    sufficient_count = all(row["minimum_counts_met"] for row in per_horizon)
    guardrails = all(row["guardrails_passed"] for row in per_horizon)
    return {
        "created_at": now.isoformat(),
        "evidence": "prospective",
        "model_manifest_sha256": MODEL_MANIFEST,
        "minimum_origins_per_horizon": MINIMUM_ORIGINS,
        "minimum_counts_met": sufficient_count,
        "guardrails_passed": guardrails,
        "validation_status": validation_status(sufficient_count, guardrails),
        "ready_for_confirmation_review": sufficient_count and guardrails,
        "publishable": False,
        "limitations": "Counts and contiguous blocks do not establish independence. Historical stress failed 46 horizons. Requires dependence review, production-compatible artifact and manual promotion.",
        "per_horizon": per_horizon,
        "observations": records,
    }


def read_emissions(directory, distribution):
    documents = []
    for path in sorted(directory.glob("*.json")):
        if path.with_suffix(".sha256").read_text(encoding="ascii") != sha256(path):
            raise ValueError("Archived emission changed")
        document = json.loads(path.read_text())
        validate_emission(document)
        snapshot = Path(document["daily_snapshot_file"])
        if sha256(snapshot) != document["daily_snapshot_sha256"]:
            raise ValueError("Archived source snapshot changed")
        weekly = b.aggregate_daily_rows(json.loads(snapshot.read_text()))
        expected = make_emission(
            weekly,
            distribution,
            datetime.fromisoformat(document["created_at"]),
            evidence="prospective",
        )
        if document["origin_close"] != expected["origin_close"]:
            raise ValueError("Emission origin differs from archived source")
        for point, reference in zip(document["points"], expected["points"]):
            if any(
                not math.isclose(a, b, rel_tol=1e-10, abs_tol=1e-8)
                for a, b in zip(point["USD"], reference["USD"])
            ):
                raise ValueError("Emission differs from frozen recipe replay")
        documents.append(document)
    return documents


def read_legacy_emission(bundle, distribution):
    """Admit only the exact shadow whose hash was recorded before its targets."""
    path = bundle / "research-shadow.json"
    if sha256(path) != LEGACY_SHADOW_HASH:
        raise ValueError("Original shadow changed")
    manifest = json.loads((bundle / "manifest.json").read_text())
    snapshot = bundle / "snapshot.csv"
    if sha256(snapshot) != manifest["snapshot_sha256"]:
        raise ValueError("Original shadow snapshot changed")
    document = json.loads(path.read_text())
    expected = hybrid.shadow(
        b._read_weekly_csv(snapshot),
        distribution,
        datetime.fromisoformat(document["created_at"]),
    )
    if {k: v for k, v in document.items() if k != "points"} != {
        k: v for k, v in expected.items() if k != "points"
    } or any(
        not math.isclose(a, b, rel_tol=1e-10, abs_tol=1e-8)
        for point, reference in zip(document["points"], expected["points"])
        for a, b in zip(point["USD"], reference["USD"])
    ):
        raise ValueError("Original shadow does not match frozen recipe replay")
    document.update(
        {
            "legacy_shadow_sha256": LEGACY_SHADOW_HASH,
            "model_manifest_sha256": MODEL_MANIFEST,
            "evidence": "prospective",
        }
    )
    validate_emission(document)
    return document


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bundle", type=Path, required=True)
    parser.add_argument("--directory", type=Path, required=True)
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--score-only", action="store_true")
    parser.add_argument("--include-legacy-shadow", action="store_true")
    args = parser.parse_args()
    now = datetime.now(timezone.utc)
    if not args.score_only and now.weekday() not in (0, 1):
        print(json.dumps({"status": "not_due", "publishable": False}))
        return
    distribution = frozen_distribution(args.bundle)
    monday = now.date() - timedelta(days=now.weekday())
    end = monday - timedelta(days=1)
    daily = b.fetch_daily_snapshot(args.base_url, date(2015, 7, 20), end)
    if not daily or max(date.fromisoformat(row["date"][:10]) for row in daily) > end:
        raise ValueError("Source returned no data or data beyond cutoff")
    weekly = b.aggregate_daily_rows(daily)
    now = datetime.now(timezone.utc)
    args.directory.mkdir(parents=True, exist_ok=True)
    run = args.directory / now.strftime("%Y%m%dT%H%M%S%fZ")
    run.mkdir(exist_ok=False)
    write_json(run / "daily-snapshot.json", daily)
    emissions = args.directory / "emissions"
    emissions.mkdir(exist_ok=True)
    if not args.score_only:
        emission = make_emission(weekly, distribution, now, evidence="prospective")
        emission["daily_snapshot_sha256"] = sha256(run / "daily-snapshot.json")
        emission["daily_snapshot_file"] = str((run / "daily-snapshot.json").resolve())
        destination = emissions / f"{emission['origin_week']}.json"
        if not destination.exists():
            write_json(destination, emission)
            with destination.with_suffix(".sha256").open(
                "x", encoding="ascii"
            ) as receipt:
                receipt.write(sha256(destination))
    documents = read_emissions(emissions, distribution)
    if args.include_legacy_shadow:
        documents.append(read_legacy_emission(args.bundle, distribution))
    report = score_emissions(documents, weekly, now)
    write_json(run / "report.json", report)
    write_json(
        run / "inventory.json",
        {
            "emissions": {path.name: sha256(path) for path in emissions.glob("*.json")},
            "daily-snapshot.json": sha256(run / "daily-snapshot.json"),
            "report.json": sha256(run / "report.json"),
            "collector_sha256": sha256(Path(__file__)),
            "legacy_shadow_sha256": (
                LEGACY_SHADOW_HASH if args.include_legacy_shadow else None
            ),
        },
    )
    print(
        json.dumps(
            {
                "status": "recorded",
                "emissions": len(documents),
                "ready_for_confirmation_review": report[
                    "ready_for_confirmation_review"
                ],
                "publishable": False,
                "report": str(run / "report.json"),
            }
        )
    )


if __name__ == "__main__":
    main()
