"""Bounded daily pooled-horizon experiment; no publication or promotion."""

import argparse
from datetime import date, datetime, timezone
import hashlib
import json
from pathlib import Path

import numpy as np
from lightgbm import LGBMRegressor
from threadpoolctl import threadpool_limits

from forecast import daily_research as daily
from forecast.daily_recovery import centered_calibration, shortlist, PROTOCOL

TRAIN_HORIZONS = np.array([1, 7, 14, 30, 60, 90, 180, 270, 365])
PARAMETERS = dict(
    objective="regression_l1",
    n_estimators=80,
    learning_rate=0.03,
    num_leaves=7,
    max_depth=3,
    min_child_samples=100,
    reg_lambda=10,
    n_jobs=2,
    random_state=0,
    deterministic=True,
    force_col_wise=True,
    verbosity=-1,
)
RECIPE = {
    "model": "daily_pooled_lightgbm_v1",
    "parameters": PARAMETERS,
    "training": "all daily origins in trailing 1095 days; mature labels only",
    "training_horizons": TRAIN_HORIZONS.tolist(),
    "features": "daily-v1 six past-only features plus log(1+horizon)",
    "target": "cumulative log return divided by sqrt(horizon)",
    "prediction": "one direct model query per day, 1..365; no interpolation",
    "calibration": PROTOCOL["centered_calibration"],
    "gate": PROTOCOL["gate"],
    "production_ready": False,
    "evidence": "exploratory_on_previously_examined_history",
}


def training_data(logs, features, origin):
    starts, horizons = np.meshgrid(
        np.arange(max(365, origin - 1095), origin),
        TRAIN_HORIZONS,
        indexing="ij",
    )
    mature = starts + horizons <= origin
    starts, horizons = starts[mature], horizons[mature]
    x = np.column_stack((features[starts], np.log1p(horizons)))
    y = (logs[starts + horizons] - logs[starts]) / np.sqrt(horizons)
    return x, y


def predict(logs, features, origin):
    x, y = training_data(logs, features, origin)
    model = LGBMRegressor(**PARAMETERS).fit(x, y)
    future = np.column_stack(
        (
            np.repeat(features[origin][None, :], 365, axis=0),
            np.log1p(daily.HORIZONS),
        )
    )
    return logs[origin] + model.predict(future) * np.sqrt(daily.HORIZONS)


def run(rows, feature_sets=None):
    days, values = daily.observations(rows)
    logs = np.log(values)
    if feature_sets is None:
        feature_sets = {"pooled": daily.features(logs)}
    origins = [j for j in range(1095, len(days) - 365) if days[j].weekday() == 6]
    forecasts = {name: {} for name in feature_sets}
    for index, j in enumerate(origins):
        for name, features in feature_sets.items():
            forecasts[name][j] = predict(logs, features, j)
        if index % 50 == 0:
            print(f"Fitted {index + 1}/{len(origins)} origins", flush=True)
    naive = {j: np.repeat(logs[j], 365) for j in origins}
    evaluable = [j for j in origins if sum(k + 365 <= j for k in origins) >= 26]
    split = date(2023, 9, 13)
    groups = {}
    for name, js in {
        "earlier": [j for j in evaluable if days[j + 365] <= split],
        "later_already_examined": [j for j in evaluable if days[j] > split],
    }.items():
        actuals = [values[j + daily.HORIZONS] for j in js]
        groups[name] = {
            "origins": len(js),
            "first_origin": str(days[js[0]]),
            "last_origin": str(days[js[-1]]),
            "models": {
                **{
                    candidate: daily.scores(
                        [centered_calibration(logs, j, raw) for j in js], actuals
                    )
                    for candidate, raw in forecasts.items()
                },
                "naive": daily.scores(
                    [daily.calibrated(logs, j, naive, naive=True) for j in js], actuals
                ),
            },
        }
    accepted = shortlist(groups, candidates=tuple(feature_sets))
    return {
        "recipe": RECIPE,
        "groups": groups,
        "shortlist": accepted,
        "decision": (
            "further_validation_required" if accepted else "reject_all_challengers"
        ),
        "production_ready": False,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--daily", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    snapshot = args.daily.read_bytes()
    sources = {}
    for module in (
        Path(__file__),
        Path(daily.__file__),
        Path(__file__).with_name("daily_recovery.py"),
    ):
        content = module.read_bytes()
        (args.output / module.name).write_bytes(content)
        sources[module.name] = hashlib.sha256(content).hexdigest()
    import importlib.metadata

    manifest = {
        "recipe": RECIPE,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "snapshot_sha256": hashlib.sha256(snapshot).hexdigest(),
        "sources": sources,
        "versions": {
            p: importlib.metadata.version(p) for p in ("numpy", "lightgbm", "scipy")
        },
    }
    (args.output / "manifest.json").write_bytes(daily.encode(manifest))
    with threadpool_limits(limits=2):
        report = run(json.loads(snapshot))
    (args.output / "report.json").write_bytes(daily.encode(report))
    print(
        json.dumps(
            {
                "decision": report["decision"],
                "scores": {
                    g: {m: s["aggregate"] for m, s in v["models"].items()}
                    for g, v in report["groups"].items()
                },
            }
        )
    )


if __name__ == "__main__":
    main()
