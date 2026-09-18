"""Exploratory diagnosis after daily-v1 failure; never publishes a model."""

import argparse
from datetime import date, datetime, timezone
import hashlib
import json
from pathlib import Path

import numpy as np
from threadpoolctl import threadpool_limits

from forecast import daily_research as daily

PROTOCOL = {
    "purpose": "Diagnose median calibration and long-horizon extrapolation",
    "evidence": "exploratory_on_previously_examined_history",
    "candidates": ["ridge_v1", "ridge_centered", "ridge_fading_30", "naive"],
    "fading": "raw cumulative log return multiplied by exp(-h/30)",
    "centered_calibration": "mature log error quantiles minus their median; preserve raw Q50",
    "gate": "research shortlist only: MAE and WIS <=0.98x naive in both historical partitions; MAE <=1.05x naive at days 1,7,30,90,180,365 in both partitions",
    "fallback": "naive remains the reference; select no challenger when all fail",
    "production_ready": False,
}


def centered_calibration(logs, origin, raw):
    bands = daily.calibrated(logs, origin, raw)
    return bands * (np.exp(raw[origin]) / bands[:, 2])[:, None]


def shortlist(groups, candidates=("ridge_centered", "ridge_fading_30")):
    accepted = []
    for name in candidates:
        passes = True
        for group in groups.values():
            models = group["models"]
            candidate, baseline = models[name], models["naive"]
            for metric in ("mae", "wis"):
                passes &= (
                    candidate["aggregate"][metric]
                    <= 0.98 * baseline["aggregate"][metric]
                )
            for h in (1, 7, 30, 90, 180, 365):
                passes &= (
                    candidate["per_horizon"][h - 1]["mae"]
                    <= 1.05 * baseline["per_horizon"][h - 1]["mae"]
                )
        if passes:
            accepted.append(name)
    return accepted


def run(rows):
    days, values = daily.observations(rows)
    logs = np.log(values)
    ridge = daily.raw_forecasts(days, values, candidate="ridge")["ridge"]
    naive = {j: np.repeat(logs[j], 365) for j in ridge}
    fading = {
        j: logs[j] + (raw - logs[j]) * np.exp(-daily.HORIZONS / 30)
        for j, raw in ridge.items()
    }
    origins = [
        j
        for j in ridge
        if days[j].weekday() == 6
        and j + 365 < len(values)
        and sum(k + 365 <= j for k in ridge) >= 26
    ]
    split = date(2023, 9, 13)
    partitions = {
        "earlier": [j for j in origins if days[j + 365] <= split],
        "later_already_examined": [j for j in origins if days[j] > split],
    }
    report = {"protocol": PROTOCOL, "groups": {}}
    for name, js in partitions.items():
        predictions = {
            "ridge_v1": [],
            "ridge_centered": [],
            "ridge_fading_30": [],
            "naive": [],
        }
        for j in js:
            predictions["ridge_v1"].append(daily.calibrated(logs, j, ridge))
            predictions["ridge_centered"].append(centered_calibration(logs, j, ridge))
            predictions["ridge_fading_30"].append(centered_calibration(logs, j, fading))
            predictions["naive"].append(daily.calibrated(logs, j, naive, naive=True))
        actuals = [values[j + daily.HORIZONS] for j in js]
        report["groups"][name] = {
            "first_origin": str(days[js[0]]),
            "last_origin": str(days[js[-1]]),
            "models": {
                candidate: daily.scores(p, actuals)
                for candidate, p in predictions.items()
            },
        }
    report["shortlist"] = shortlist(report["groups"])
    report["decision"] = (
        "further_validation_required"
        if report["shortlist"]
        else "reject_all_challengers"
    )
    report["production_ready"] = False
    return report


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--daily", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    snapshot = args.daily.read_bytes()
    manifest = {
        "protocol": PROTOCOL,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "snapshot_sha256": hashlib.sha256(snapshot).hexdigest(),
        "code_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    }
    (args.output / "manifest.json").write_bytes(daily.encode(manifest))
    (args.output / "daily_recovery.py").write_bytes(Path(__file__).read_bytes())
    with threadpool_limits(limits=2):
        report = run(json.loads(snapshot))
    (args.output / "report.json").write_bytes(daily.encode(report))
    print(
        json.dumps(
            {
                "decision": report["decision"],
                "shortlist": report["shortlist"],
                "scores": {
                    name: {
                        candidate: s["aggregate"]
                        for candidate, s in group["models"].items()
                    }
                    for name, group in report["groups"].items()
                },
            }
        )
    )


if __name__ == "__main__":
    main()
