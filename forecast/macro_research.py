"""Point-in-time ALFRED macro ablation; research only, never publishes."""

import argparse
import csv
from datetime import date, datetime, timezone
import hashlib
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
from urllib.parse import quote
from urllib.request import Request, urlopen

import numpy as np
from threadpoolctl import threadpool_limits

from forecast import daily_pooled_research as pooled
from forecast import daily_research as daily
from forecast.daily_recovery import shortlist

ALFRED_GRAPH_URL = "https://alfred.stlouisfed.org/graph/alfredgraph.csv"
SERIES = ("DFF", "CPIAUCSL", "UNRATE")
VINTAGE_BATCH_SIZE = 12
MACRO_LAGS = (7,)

RECIPE = {
    "model": "daily_pooled_alfred_macro_v1",
    "series": list(SERIES),
    "source": "ALFRED vintage snapshots from the public graph CSV endpoint",
    "availability": "for origin day d, use the latest requested vintage_date <= d; use only observations <= d",
    "features": "each series level and seven-day change, carried forward within its point-in-time vintage",
    "comparison": "same daily rows, Sunday origins, 365 targets, model parameters and calibration as price_only",
    "selection": "macro must beat both unchanged-price and price-only baselines in both partitions and all guardrails",
    "production_ready": False,
    "evidence": "exploratory_on_point_in_time_macro_snapshot",
}


def _date_strings(values):
    return [
        value.isoformat() if isinstance(value, date) else str(value) for value in values
    ]


def parse_alfred_csv(content, series_id, vintage_dates):
    """Parse one ALFRED request and reject a silently substituted vintage."""
    if isinstance(content, bytes):
        content = content.decode("utf-8-sig")
    vintages = [date.fromisoformat(value) for value in _date_strings(vintage_dates)]
    expected = [
        "observation_date",
        *(f"{series_id}_{value:%Y%m%d}" for value in vintages),
    ]
    rows = list(csv.reader(io.StringIO(content)))
    if not rows or rows[0] != expected:
        raise ValueError("ALFRED vintage header does not match the request")

    observations = []
    previous = None
    for row in rows[1:]:
        if len(row) != len(expected):
            raise ValueError("ALFRED observation width does not match the request")
        observed = date.fromisoformat(row[0])
        if previous is not None and observed <= previous:
            raise ValueError("ALFRED observations must be ordered and unique")
        previous = observed
        values = []
        for raw in row[1:]:
            if raw in ("", ".", "#N/A"):
                values.append(None)
                continue
            value = float(raw)
            if not np.isfinite(value):
                raise ValueError("ALFRED observation is not finite")
            values.append(value)
        observations.append({"date": observed.isoformat(), "values": values})
    if not observations:
        raise ValueError("ALFRED returned no observations")
    return {
        "series_id": series_id,
        "vintage_dates": [value.isoformat() for value in vintages],
        "observations": observations,
    }


def _fetch(url, opener=None):
    if opener is None:
        curl = shutil.which("curl.exe") or shutil.which("curl")
        if curl is None:
            opener = urlopen
        else:
            handle, filename = tempfile.mkstemp(suffix=".csv")
            os.close(handle)
            Path(filename).unlink(missing_ok=True)
            try:
                command = (
                    f"{curl} -L --fail --silent --show-error --retry 4 "
                    f"--retry-delay 2 --retry-all-errors --max-time 90 "
                    f"-A 'bitcoin-analysis-forecast-research/1' "
                    f"-o '{filename}' '{url}'"
                )
                powershell = shutil.which("powershell.exe")
                if powershell:
                    subprocess.run(
                        [
                            powershell,
                            "-NoProfile",
                            "-NonInteractive",
                            "-Command",
                            command,
                        ],
                        check=True,
                        capture_output=True,
                        timeout=180,
                    )
                else:
                    subprocess.run(
                        [
                            curl,
                            "-L",
                            "--fail",
                            "--silent",
                            "--show-error",
                            "--retry",
                            "4",
                            "--retry-delay",
                            "2",
                            "--retry-all-errors",
                            "--max-time",
                            "90",
                            "-A",
                            "bitcoin-analysis-forecast-research/1",
                            "-o",
                            filename,
                            url,
                        ],
                        check=True,
                        capture_output=True,
                        timeout=180,
                    )
                return Path(filename).read_bytes()
            finally:
                Path(filename).unlink(missing_ok=True)
    request = Request(
        url, headers={"User-Agent": "bitcoin-analysis-forecast-research/1"}
    )
    with opener(request, timeout=30) as response:
        return response.read()


def fetch_series(
    series_id,
    vintage_dates,
    start_date,
    end_date,
    *,
    base_url=ALFRED_GRAPH_URL,
    batch_size=VINTAGE_BATCH_SIZE,
    opener=None,
):
    vintages = [date.fromisoformat(value) for value in _date_strings(vintage_dates)]
    if vintages != sorted(set(vintages)):
        raise ValueError("Vintage dates must be sorted and unique")
    parts = []
    for offset in range(0, len(vintages), batch_size):
        batch = vintages[offset : offset + batch_size]
        ids = ",".join([series_id] * len(batch))
        query = (
            f"id={quote(ids, safe=',')}&cosd={start_date:%Y-%m-%d}"
            f"&coed={end_date:%Y-%m-%d}"
            f"&vintage_date={quote(','.join(value.isoformat() for value in batch), safe=',')}"
        )
        parts.append(_fetch(f"{base_url}?{query}", opener))
    return merge_alfred_parts(parts, series_id, vintages)


def merge_alfred_parts(contents, series_id, vintage_dates):
    vintages = [date.fromisoformat(value) for value in _date_strings(vintage_dates)]
    positions = {value: index for index, value in enumerate(vintages)}
    merged = {}
    seen = []
    for content in contents:
        if isinstance(content, bytes):
            content = content.decode("utf-8-sig")
        header = next(csv.reader(io.StringIO(content)), [])
        prefix = f"{series_id}_"
        if len(header) < 2 or any(not value.startswith(prefix) for value in header[1:]):
            raise ValueError("ALFRED vintage header does not match the series")
        batch = [
            datetime.strptime(value[len(prefix) :], "%Y%m%d").date()
            for value in header[1:]
        ]
        if any(value not in positions for value in batch) or len(batch) != len(
            set(batch)
        ):
            raise ValueError("ALFRED part contains an unexpected vintage")
        seen.extend(batch)
        parsed = parse_alfred_csv(content, series_id, batch)
        for row in parsed["observations"]:
            values = merged.setdefault(row["date"], [None] * len(vintages))
            for local_index, vintage in enumerate(batch):
                position = positions[vintage]
                existing = values[position]
                current = row["values"][local_index]
                if existing is not None and existing != current:
                    raise ValueError("ALFRED parts contain conflicting observations")
                values[position] = current
    if sorted(seen) != vintages:
        raise ValueError("ALFRED parts do not cover the requested vintages")
    return {
        "series_id": series_id,
        "vintage_dates": [value.isoformat() for value in vintages],
        "observations": [
            {"date": observed, "values": merged[observed]}
            for observed in sorted(merged)
        ],
    }


def snapshot_from_raw(directory, vintage_dates, *, series=SERIES):
    directory = Path(directory)
    return {
        "schema_version": 1,
        "source": "ALFRED",
        "series": [
            merge_alfred_parts(
                [
                    path.read_bytes()
                    for path in sorted(directory.glob(f"{series_id}-*.csv"))
                ],
                series_id,
                vintage_dates,
            )
            for series_id in series
        ],
        "vintage_dates": [value.isoformat() for value in vintage_dates],
    }


def fetch_snapshot(days, *, series=SERIES, opener=None):
    if not days:
        raise ValueError("At least one daily date is required")
    vintages = sorted({day for day in days if day.weekday() == 6})
    if not vintages:
        raise ValueError("The daily snapshot must include a Sunday origin")
    start_date, end_date = min(days), max(days)
    return {
        "schema_version": 1,
        "source": "ALFRED",
        "series": [
            fetch_series(
                series_id,
                vintages,
                start_date,
                end_date,
                opener=opener,
            )
            for series_id in series
        ],
        "vintage_dates": [value.isoformat() for value in vintages],
    }


def _series_values(days, snapshot, payload):
    vintages = np.array(
        [date.fromisoformat(value) for value in snapshot["vintage_dates"]], dtype=object
    )
    observations = payload["observations"]
    observation_dates = np.array(
        [date.fromisoformat(row["date"]) for row in observations], dtype=object
    )
    values = np.asarray(
        [
            [np.nan if value is None else float(value) for value in row["values"]]
            for row in observations
        ],
        dtype=float,
    )
    if values.shape[1] != len(vintages):
        raise ValueError("Macro observation width does not match vintage dates")
    carried = np.full_like(values, np.nan)
    for vintage_index in range(values.shape[1]):
        last = np.nan
        for observation_index, value in enumerate(values[:, vintage_index]):
            if np.isfinite(value):
                last = value
            carried[observation_index, vintage_index] = last

    result = np.full(len(days), np.nan)
    for index, day in enumerate(days):
        vintage_index = int(np.searchsorted(vintages, day, side="right") - 1)
        observation_index = int(
            np.searchsorted(observation_dates, day, side="right") - 1
        )
        if vintage_index >= 0 and observation_index >= 0:
            result[index] = carried[observation_index, vintage_index]
    return result


def feature_matrix(days, snapshot):
    """Build causal macro features using the latest vintage known on each day."""
    if list(snapshot.get("vintage_dates", [])) != sorted(
        set(snapshot.get("vintage_dates", []))
    ):
        raise ValueError("Macro vintage dates must be sorted and unique")
    payloads = snapshot.get("series", [])
    if not payloads:
        raise ValueError("Macro snapshot contains no series")
    snapshot_vintages = list(snapshot["vintage_dates"])
    if any(payload.get("vintage_dates") != snapshot_vintages for payload in payloads):
        raise ValueError("Macro series do not share the snapshot vintage dates")

    raw = np.column_stack(
        [_series_values(days, snapshot, payload) for payload in payloads]
    )
    result = np.full((len(days), raw.shape[1] * (1 + len(MACRO_LAGS))), np.nan)
    for series_index in range(raw.shape[1]):
        start = series_index * (1 + len(MACRO_LAGS))
        result[:, start] = raw[:, series_index]
        for lag_index, lag in enumerate(MACRO_LAGS, start + 1):
            result[lag:, lag_index] = raw[lag:, series_index] - raw[:-lag, series_index]
    if len(days) > 365 and not np.isfinite(result[365:]).all():
        raise ValueError("Macro snapshot has missing values after the warmup period")
    return result


def enriched_shortlist(groups):
    candidates = ("price_macro",)
    vs_naive = set(shortlist(groups, candidates))
    vs_price = {
        name: {"models": {**group["models"], "naive": group["models"]["price_only"]}}
        for name, group in groups.items()
    }
    return [
        name
        for name in candidates
        if name in vs_naive and name in shortlist(vs_price, candidates)
    ]


def run(rows, snapshot):
    days, _ = daily.observations(rows)
    macro_features = feature_matrix(days, snapshot)
    features = {
        "price_only": daily.features(np.log([row["close"] for row in rows])),
        "price_macro": np.column_stack(
            (daily.features(np.log([row["close"] for row in rows])), macro_features)
        ),
    }
    report = pooled.run(rows, feature_sets=features)
    report["recipe"] = RECIPE
    report["shortlist"] = enriched_shortlist(report["groups"])
    report["decision"] = (
        "further_validation_required"
        if report["shortlist"]
        else "reject_all_challengers"
    )
    report["production_ready"] = False
    return report


def _encode(value):
    return json.dumps(value, sort_keys=True, allow_nan=False).encode()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--daily", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--raw-dir", type=Path)
    args = parser.parse_args()
    args.output.mkdir(parents=False, exist_ok=False)
    source = args.daily.read_bytes()
    rows = json.loads(source)
    days, _ = daily.observations(rows)
    vintages = sorted({day for day in days if day.weekday() == 6})
    snapshot = (
        snapshot_from_raw(args.raw_dir, vintages)
        if args.raw_dir is not None
        else fetch_snapshot(days)
    )
    (args.output / "macro-snapshot.json").write_bytes(_encode(snapshot))
    manifest = {
        "recipe": RECIPE,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "daily_snapshot_sha256": hashlib.sha256(source).hexdigest(),
        "macro_snapshot_sha256": hashlib.sha256(_encode(snapshot)).hexdigest(),
        "code_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    }
    if args.raw_dir is not None:
        manifest["raw_files_sha256"] = {
            path.name: hashlib.sha256(path.read_bytes()).hexdigest()
            for path in sorted(args.raw_dir.glob("*.csv"))
        }
    (args.output / "manifest.json").write_bytes(_encode(manifest))
    with threadpool_limits(limits=2):
        report = run(rows, snapshot)
    (args.output / "report.json").write_bytes(_encode(report))
    print(
        json.dumps(
            {
                "decision": report["decision"],
                "shortlist": report["shortlist"],
                "scores": {
                    group: {
                        model: score["aggregate"]
                        for model, score in payload["models"].items()
                    }
                    for group, payload in report["groups"].items()
                },
            }
        )
    )


if __name__ == "__main__":
    main()
