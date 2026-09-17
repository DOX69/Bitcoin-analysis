"""Matched daily volume/range ablation. Research only; never publishes."""

import argparse
from datetime import datetime, timezone
import hashlib
from importlib.metadata import version
import json
from pathlib import Path

import numpy as np
from threadpoolctl import threadpool_limits

from forecast import daily_pooled_research as pooled
from forecast import daily_research as daily

RECIPE = {
    **pooled.RECIPE,
    "model": "daily_ohlcv_ablation_v1",
    "candidates": ["price_only", "price_volume", "price_range", "price_volume_range"],
    "volume_features": "log1p(volume): today minus trailing 30d mean; trailing 7d mean minus trailing 30d mean",
    "range_features": "log(high/low): trailing 7d and 30d means",
    "windows": "include completed origin day; no future observations or global normalization",
    "comparison": "identical rows, origins, targets, hyperparameters and calibration for every candidate",
    "selection": "existing shortlist gate versus naive AND same 2% MAE/WIS and landmark guardrails versus price_only in both partitions",
    "vintages": "latest stored revisions at export time, not historical point-in-time evidence",
}


def audit(snapshot, reference):
    rows = snapshot["rows"]
    days, values = daily.observations(rows)
    reference_days, reference_values = daily.observations(reference)
    if days != reference_days or not np.array_equal(values, reference_values):
        raise ValueError(
            "OHLCV and reference dates/closes differ; freeze a matched comparison"
        )
    fields = np.array(
        [[r[k] for k in ("open", "high", "low", "close", "volume")] for r in rows],
        dtype=float,
    )
    if not np.isfinite(fields).all():
        raise ValueError("Nonfinite OHLCV values")
    op, high, low, close, volume = fields.T
    if not np.all(
        (low > 0)
        & (low <= op)
        & (low <= close)
        & (high >= op)
        & (high >= close)
        & (volume >= 0)
    ):
        raise ValueError("Invalid OHLCV bounds or negative volume")
    exported = datetime.fromisoformat(snapshot["exported_at"].replace("Z", "+00:00"))
    observed = [
        datetime.fromisoformat(r["observed_at"].replace("Z", "+00:00")) for r in rows
    ]
    if exported.tzinfo is None or any(
        t.tzinfo is None or t > exported for t in observed
    ):
        raise ValueError("Invalid availability timestamps")
    if days[-1] >= exported.astimezone(timezone.utc).date():
        raise ValueError("Incomplete UTC day")
    return {
        "rows": len(rows),
        "first_date": str(days[0]),
        "last_date": str(days[-1]),
        "zero_volume_days": int(np.sum(volume == 0)),
        "reference_closes_identical": True,
        "oldest_ingestion": min(observed).isoformat(),
        "newest_ingestion": max(observed).isoformat(),
        "point_in_time_history": False,
    }


def feature_sets(rows):
    base = daily.features(np.log([r["close"] for r in rows]))
    volume = np.log1p([r["volume"] for r in rows])
    ranges = np.log([r["high"] / r["low"] for r in rows])
    v = np.full((len(rows), 2), np.nan)
    r = np.full((len(rows), 2), np.nan)
    for j in range(29, len(rows)):
        mean30 = volume[j - 29 : j + 1].mean()
        v[j] = [volume[j] - mean30, volume[j - 6 : j + 1].mean() - mean30]
        r[j] = [ranges[j - 6 : j + 1].mean(), ranges[j - 29 : j + 1].mean()]
    return {
        "price_only": base,
        "price_volume": np.column_stack((base, v)),
        "price_range": np.column_stack((base, r)),
        "price_volume_range": np.column_stack((base, v, r)),
    }


def enriched_shortlist(groups):
    from forecast.daily_recovery import shortlist

    candidates = ("price_volume", "price_range", "price_volume_range")
    vs_naive = shortlist(groups, candidates)
    vs_price = {
        name: {"models": {**g["models"], "naive": g["models"]["price_only"]}}
        for name, g in groups.items()
    }
    return [name for name in shortlist(vs_price, candidates) if name in vs_naive]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--snapshot", type=Path, required=True)
    parser.add_argument("--reference", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    snapshot_bytes, reference_bytes = (
        args.snapshot.read_bytes(),
        args.reference.read_bytes(),
    )
    snapshot, reference = json.loads(snapshot_bytes), json.loads(reference_bytes)
    checks = audit(snapshot, reference)
    args.output.mkdir(parents=True, exist_ok=False)
    sources = {}
    for path in [
        *Path(__file__).parent.glob("*.py"),
        Path(__file__).parents[1] / "uv.lock",
    ]:
        content = path.read_bytes()
        (args.output / path.name).write_bytes(content)
        sources[path.name] = hashlib.sha256(content).hexdigest()
    manifest = {
        "recipe": RECIPE,
        "audit": checks,
        "sources": sources,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "snapshot_sha256": hashlib.sha256(snapshot_bytes).hexdigest(),
        "reference_sha256": hashlib.sha256(reference_bytes).hexdigest(),
        "versions": {p: version(p) for p in ("numpy", "lightgbm", "scipy")},
    }
    (args.output / "snapshot.json").write_bytes(snapshot_bytes)
    (args.output / "reference.json").write_bytes(reference_bytes)
    (args.output / "manifest.json").write_bytes(daily.encode(manifest))
    with threadpool_limits(limits=2):
        report = pooled.run(snapshot["rows"], feature_sets(snapshot["rows"]))
    report["recipe"], report["audit"] = RECIPE, checks
    report["shortlist"] = enriched_shortlist(report["groups"])
    report["decision"] = (
        "further_validation_required"
        if report["shortlist"]
        else "reject_all_challengers"
    )
    (args.output / "report.json").write_bytes(daily.encode(report))
    print(
        json.dumps(
            {
                "decision": report["decision"],
                "shortlist": report["shortlist"],
                "audit": checks,
                "scores": {
                    g: {m: s["aggregate"] for m, s in v["models"].items()}
                    for g, v in report["groups"].items()
                },
            }
        )
    )


if __name__ == "__main__":
    main()
