"""Read-only audit/export of ONE archived hybrid report and its independent copy."""

import argparse
import hashlib
import json
import math
from pathlib import Path

from forecast.prospective_research import (
    MINIMUM_ORIGINS,
    MODEL_MANIFEST,
    horizon_assessment,
    validation_status,
)

PREFIX = "development/research/hybrid-v1"
METRICS = ("mae", "naive_mae", "wis", "coverage_50", "coverage_80")


def verified_pair(primary, backup, expected_sha256=None):
    if primary != backup:
        raise ValueError("Independent copy differs")
    digest = hashlib.sha256(primary).hexdigest()
    if expected_sha256 is not None and digest != expected_sha256:
        raise ValueError("Archived checksum mismatch")
    return digest


def summarize(primary, backup, expected_sha256=None):
    digest = verified_pair(primary, backup, expected_sha256)
    report = json.loads(primary)
    if (
        report.get("evidence") != "prospective"
        or report.get("model_manifest_sha256") != MODEL_MANIFEST
        or report.get("minimum_origins_per_horizon") != MINIMUM_ORIGINS
        or report.get("publishable") is not False
    ):
        raise ValueError("Not a supported frozen hybrid research report")
    horizons = report["per_horizon"]
    if [row["horizon_weeks"] for row in horizons] != list(range(1, 53)):
        raise ValueError("Expected all 52 horizons exactly once")
    if set(report["observations"]) != {str(h) for h in range(1, 53)}:
        raise ValueError("Unexpected observation horizons")
    summary, points = [], []
    for row in horizons:
        h = row["horizon_weeks"]
        observations = report["observations"][str(h)]
        if len(observations) != row["origins"] or len(
            {point["origin_week"] for point in observations}
        ) != len(observations):
            raise ValueError("Inconsistent or duplicate observations")
        for metric in METRICS:
            values = [point[metric] for point in observations]
            if any(not math.isfinite(value) or value < 0 for value in values):
                raise ValueError("Invalid observation metric")
            expected = sum(values) / len(values) if values else None
            actual = row[metric]
            if (expected is None and actual is not None) or (
                expected is not None
                and (
                    actual is None
                    or not math.isclose(actual, expected, rel_tol=1e-10, abs_tol=1e-8)
                )
            ):
                raise ValueError("Reported aggregate differs from observations")
        summary.append({**row, **horizon_assessment(row)})
        for point in observations:
            quantiles = point["prediction"]
            if (
                len(quantiles) != 5
                or any(not math.isfinite(v) or v <= 0 for v in quantiles)
                or quantiles != sorted(quantiles)
                or not math.isfinite(point["actual"])
                or point["actual"] <= 0
            ):
                raise ValueError("Invalid observed price or quantiles")
            points.append(
                {
                    "horizon_weeks": h,
                    "origin_week": point["origin_week"],
                    "issued_at": point.get("issued_at"),
                    "origin_close": point.get("origin_close"),
                    "target_date": point["target_date"],
                    "actual": point["actual"],
                    **dict(zip(("q10", "q25", "q50", "q75", "q90"), quantiles)),
                    **{key: point[key] for key in METRICS},
                }
            )
    counts = all(row["minimum_counts_met"] for row in summary)
    guardrails = all(row["guardrails_passed"] for row in summary)
    for key, expected in (
        ("minimum_counts_met", counts),
        ("guardrails_passed", guardrails),
        ("ready_for_confirmation_review", counts and guardrails),
    ):
        if report.get(key) is not expected:
            raise ValueError("Report decision differs from its metrics")
    status = validation_status(counts, guardrails)
    if "validation_status" in report and report["validation_status"] != status:
        raise ValueError("Report validation status differs")
    return {
        "report_created_at": report["created_at"],
        "report_sha256": digest,
        "expected_checksum_verified": expected_sha256 is not None,
        "independent_copy_verified": True,
        "snapshot_copy_verified": False,
        "model_manifest_sha256": MODEL_MANIFEST,
        "snapshot_sha256": report.get("snapshot_sha256"),
        "validation_status": status,
        "minimum_origins_per_horizon": MINIMUM_ORIGINS,
        "minimum_counts_met": counts,
        "guardrails_passed": guardrails,
        "ready_for_confirmation_review": counts and guardrails,
        "publishable": False,
        "mature_points": len(points),
        "per_horizon": summary,
        "observations": points,
        "limitations": "One report only; daily rescoring adds no observations. Copy equality is not independent validation. No emission replay or statistical independence established. Missing legacy metadata stays null. Manual dependence review and promotion remain required.",
    }


def audit_cloud(source, backup, key, expected_sha256=None):
    # Deliberately do not call collect/load_emissions: they can repair/write copies.
    from forecast.backups import read

    if source.bucket == backup.bucket:
        raise ValueError("Independent destination bucket required")
    if not key.startswith(PREFIX + "/reports/"):
        raise ValueError("Expected a Development hybrid report key")
    primary = read(source, key)
    result = summarize(primary, read(backup, key), expected_sha256)
    report = json.loads(primary)
    snapshot_key = report["snapshot_key"]
    if not snapshot_key.startswith(PREFIX + "/snapshots/"):
        raise ValueError("Snapshot outside hybrid namespace")
    verified_pair(
        read(source, snapshot_key),
        read(backup, snapshot_key),
        report["snapshot_sha256"],
    )
    result.update(report_key=key, snapshot_copy_verified=True)
    return result


def markdown(result):
    lines = [
        "# Audit prospectif de l'hybride",
        "",
        f"Rapport : {result['report_created_at']}",
        f"SHA-256 : `{result['report_sha256']}`",
        f"Statut : `{result['validation_status']}` ; {result['mature_points']} point(s) mature(s).",
        "Copie du rapport identique : oui. Modèle publiable : non.",
        f"Empreinte attendue vérifiée : {result['expected_checksum_verified']}. Copie du snapshot vérifiée : {result['snapshot_copy_verified']}.",
        "",
        "| h (semaines) | n | Statut | MAE USD | Référence USD | WIS USD | Couverture 50 % | Couverture 80 % |",
        "|---|---|---|---|---|---|---|---|",
    ]

    def number(value):
        return "—" if value is None else f"{value:.6g}"

    for row in result["per_horizon"]:
        lines.append(
            "| "
            + " | ".join(
                [
                    str(row["horizon_weeks"]),
                    str(row["origins"]),
                    row["validation_status"],
                    *(number(row[key]) for key in METRICS),
                ]
            )
            + " |"
        )
    lines.extend(
        [
            "",
            "Les couvertures sont des proportions entre 0 et 1. Les valeurs exactes et les observations individuelles sont dans l'export JSON.",
            "",
            result["limitations"],
        ]
    )
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--report", type=Path, help="Local archived report")
    source.add_argument("--report-key", help="Exact S3 hybrid report key")
    parser.add_argument("--copy", type=Path, help="Local independently retrieved copy")
    parser.add_argument("--config", type=Path)
    parser.add_argument("--expected-sha256")
    parser.add_argument("--format", choices=("json", "markdown"), default="json")
    args = parser.parse_args()
    if args.report:
        if args.copy is None or args.config is not None:
            parser.error("Local audit requires --copy and no --config")
        if args.report.resolve() == args.copy.resolve():
            parser.error("Report and copy must be distinct files")
        result = summarize(
            args.report.read_bytes(), args.copy.read_bytes(), args.expected_sha256
        )
    else:
        if args.config is None or args.copy is not None:
            parser.error("Cloud audit requires --config and no --copy")
        config = json.loads(args.config.read_text())
        if config.get("environment") != "development":
            parser.error("Only Development hybrid research is supported")
        from forecast.backups import configured_repositories

        primary, backup = configured_repositories(config)
        result = audit_cloud(primary, backup, args.report_key, args.expected_sha256)
    print(
        markdown(result)
        if args.format == "markdown"
        else json.dumps(result, indent=2, allow_nan=False)
    )


if __name__ == "__main__":
    main()
