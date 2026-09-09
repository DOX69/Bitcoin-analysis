from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import statistics
import sys
import threading
import time
import urllib.parse
import urllib.request
from collections import defaultdict
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path
from typing import Any, Iterable, Sequence

MAX_HORIZON = 52
LOOKBACKS = (1, 2, 4, 8, 13, 26, 52)
QUANTILES = (0.1, 0.25, 0.5, 0.75, 0.9)
BENCHMARK_THREADS = 2
RAILWAY_VCPU_MINUTE_USD = 0.000463
RAILWAY_GB_MINUTE_USD = 0.000231
RAILWAY_MEMORY_GB = 4
API_CHUNK_DAYS = 1799


@dataclass(frozen=True)
class Split:
    train_end: int
    calibration_start: int
    calibration_end: int
    test_start: int
    test_end: int


@dataclass(frozen=True)
class CandidateMeasurement:
    name: str
    threads_configured: int
    fit_seconds: float
    backtest_seconds: float
    peak_rss_bytes: int
    artifact_bytes: int
    metrics: dict[str, float]
    per_horizon: list[dict[str, float | int]]


def aggregate_daily_rows(
    rows: Iterable[dict[str, Any]],
) -> list[dict[str, float | str]]:
    by_date: dict[date, float] = {}
    for row in rows:
        observed = date.fromisoformat(str(row["date"])[:10])
        close = float(row["close"])
        if not math.isfinite(close) or close <= 0:
            raise ValueError(f"Invalid close for {observed}: {close}")
        if observed in by_date:
            raise ValueError(f"Duplicate daily observation: {observed}")
        by_date[observed] = close

    weeks: dict[tuple[int, int], list[tuple[date, float]]] = defaultdict(list)
    for observed, close in sorted(by_date.items()):
        iso_year, iso_week, _ = observed.isocalendar()
        weeks[(iso_year, iso_week)].append((observed, close))

    weekly = []
    for (iso_year, iso_week), observations in sorted(weeks.items()):
        monday = date.fromisocalendar(iso_year, iso_week, 1)
        expected_dates = [monday + timedelta(days=index) for index in range(7)]
        if [observed for observed, _ in observations] != expected_dates:
            raise ValueError("Snapshot must contain complete ISO weeks")
        weekly.append({"date": monday.isoformat(), "close": observations[-1][1]})
    if not weekly:
        raise ValueError("Snapshot contains no daily observations")
    for previous, current in zip(weekly, weekly[1:]):
        previous_date = date.fromisoformat(str(previous["date"]))
        current_date = date.fromisoformat(str(current["date"]))
        if current_date != previous_date + timedelta(days=7):
            raise ValueError("Snapshot has a missing ISO week")
    return weekly


def split_series(weekly: Sequence[dict[str, Any]]) -> Split:
    count = len(weekly)
    train_end = math.floor(count * 0.6)
    calibration_end = math.floor(count * 0.8)
    test_end = count - MAX_HORIZON
    if train_end <= max(LOOKBACKS) + MAX_HORIZON:
        raise ValueError("Snapshot is too short for the training split")
    if test_end <= calibration_end:
        raise ValueError(
            "Snapshot is too short for disjoint calibration and test targets"
        )
    return Split(train_end, train_end, calibration_end, calibration_end, test_end)


def _empirical_quantile(values: Sequence[float], quantile: float) -> float:
    ordered = sorted(values)
    position = (len(ordered) - 1) * quantile
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return ordered[lower]
    weight = position - lower
    return ordered[lower] + weight * (ordered[upper] - ordered[lower])


@dataclass(frozen=True)
class ResidualQuantileCalibrator:
    corrections: tuple[tuple[float, ...], ...]
    quantiles: tuple[float, ...]
    preserve_median: bool = False

    @classmethod
    def fit(
        cls,
        predictions: Sequence[Sequence[Sequence[float]]],
        actuals: Sequence[Sequence[float]],
        quantiles: Sequence[float],
        preserve_median: bool = False,
    ) -> "ResidualQuantileCalibrator":
        horizon_count = len(predictions[0])
        corrections = []
        for horizon_index in range(horizon_count):
            by_quantile = []
            for quantile_index, quantile in enumerate(quantiles):
                residuals = [
                    actual[horizon_index] - prediction[horizon_index][quantile_index]
                    for prediction, actual in zip(predictions, actuals)
                ]
                correction = (
                    0.0
                    if preserve_median and quantile == 0.5
                    else _empirical_quantile(residuals, quantile)
                )
                by_quantile.append(correction)
            corrections.append(tuple(by_quantile))
        return cls(tuple(corrections), tuple(quantiles), preserve_median)

    def apply(
        self, predictions: Sequence[Sequence[Sequence[float]]]
    ) -> list[list[list[float]]]:
        calibrated = []
        for origin in predictions:
            calibrated.append(
                [
                    sorted(
                        prediction + correction
                        for prediction, correction in zip(
                            row, self.corrections[horizon_index]
                        )
                    )
                    for horizon_index, row in enumerate(origin)
                ]
            )
        return calibrated

    def to_json_bytes(self) -> bytes:
        return json.dumps(
            {
                "quantiles": self.quantiles,
                "corrections": self.corrections,
                "preserve_median": self.preserve_median,
            },
            sort_keys=True,
        ).encode()


def estimate_railway_cost_usd(runtime_seconds: float) -> float:
    minutes = max(0.0, runtime_seconds) / 60
    return minutes * (
        BENCHMARK_THREADS * RAILWAY_VCPU_MINUTE_USD
        + RAILWAY_MEMORY_GB * RAILWAY_GB_MINUTE_USD
    )


def _process_rss_bytes() -> int:
    if sys.platform == "win32":
        import ctypes
        from ctypes import wintypes

        class ProcessMemoryCounters(ctypes.Structure):
            _fields_ = [
                ("cb", wintypes.DWORD),
                ("PageFaultCount", wintypes.DWORD),
                ("PeakWorkingSetSize", ctypes.c_size_t),
                ("WorkingSetSize", ctypes.c_size_t),
                ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
                ("QuotaPagedPoolUsage", ctypes.c_size_t),
                ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
                ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
                ("PagefileUsage", ctypes.c_size_t),
                ("PeakPagefileUsage", ctypes.c_size_t),
            ]

        counters = ProcessMemoryCounters()
        counters.cb = ctypes.sizeof(ProcessMemoryCounters)
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        psapi = ctypes.WinDLL("psapi", use_last_error=True)
        get_current_process = kernel32.GetCurrentProcess
        get_current_process.restype = wintypes.HANDLE
        get_memory_info = psapi.GetProcessMemoryInfo
        get_memory_info.argtypes = [
            wintypes.HANDLE,
            ctypes.POINTER(ProcessMemoryCounters),
            wintypes.DWORD,
        ]
        get_memory_info.restype = wintypes.BOOL
        if not get_memory_info(
            get_current_process(), ctypes.byref(counters), counters.cb
        ):
            raise ctypes.WinError(ctypes.get_last_error())
        return int(counters.WorkingSetSize)

    import resource

    value = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return int(value * (1024 if sys.platform != "darwin" else 1))


class PeakRssSampler:
    def __init__(self) -> None:
        self.peak_bytes = 0
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    def __enter__(self) -> "PeakRssSampler":
        self.peak_bytes = _process_rss_bytes()
        self._thread = threading.Thread(target=self._sample, daemon=True)
        self._thread.start()
        return self

    def __exit__(self, *_: object) -> None:
        self._stop.set()
        if self._thread:
            self._thread.join()

    def _sample(self) -> None:
        while not self._stop.is_set():
            self.peak_bytes = max(self.peak_bytes, _process_rss_bytes())
            self._stop.wait(0.025)


def _feature_row(closes: Sequence[float], origin: int) -> list[float]:
    if origin < max(LOOKBACKS):
        raise ValueError("Feature row requires 52 observed weeks")
    current_log = math.log(closes[origin])
    features = [current_log]
    features.extend(current_log - math.log(closes[origin - lag]) for lag in LOOKBACKS)
    for window in (4, 13, 26):
        returns = [
            math.log(closes[index] / closes[index - 1])
            for index in range(origin - window + 1, origin + 1)
        ]
        features.append(statistics.pstdev(returns))
    return features


def _actuals(closes: Sequence[float], origins: Sequence[int]) -> list[list[float]]:
    return [
        [closes[origin + horizon] for horizon in range(1, MAX_HORIZON + 1)]
        for origin in origins
    ]


class PersistenceCandidate:
    name = "price_unchanged"
    threads_configured = 1
    preserve_median = True

    def fit(self, closes: Sequence[float], train_end: int) -> None:
        self.train_end = train_end

    def predict(self, closes: Sequence[float], origin: int) -> list[list[float]]:
        return [[closes[origin]] * len(QUANTILES) for _ in range(MAX_HORIZON)]

    def artifact_bytes(self) -> int:
        return len(
            json.dumps({"candidate": self.name, "horizons": MAX_HORIZON}).encode()
        )


class GaussianRandomWalkCandidate:
    name = "gaussian_random_walk"
    threads_configured = 1
    preserve_median = False

    def fit(self, closes: Sequence[float], train_end: int) -> None:
        returns = [
            math.log(closes[index] / closes[index - 1]) for index in range(1, train_end)
        ]
        self.mu = statistics.mean(returns)
        self.sigma = max(statistics.pstdev(returns), 1e-9)

    def predict(self, closes: Sequence[float], origin: int) -> list[list[float]]:
        normal = statistics.NormalDist()
        current_log = math.log(closes[origin])
        return [
            [
                math.exp(
                    current_log
                    + self.mu * horizon
                    + self.sigma * math.sqrt(horizon) * normal.inv_cdf(quantile)
                )
                for quantile in QUANTILES
            ]
            for horizon in range(1, MAX_HORIZON + 1)
        ]

    def artifact_bytes(self) -> int:
        return len(
            json.dumps(
                {"candidate": self.name, "mu": self.mu, "sigma": self.sigma}
            ).encode()
        )


class LightGBMQuantileCandidate:
    name = "lightgbm_quantile"
    threads_configured = BENCHMARK_THREADS
    preserve_median = False

    def fit(self, closes: Sequence[float], train_end: int) -> None:
        try:
            from lightgbm import LGBMRegressor
        except ImportError as error:
            raise RuntimeError(
                "LightGBM is required. Run with `uv run --with lightgbm`."
            ) from error

        import numpy as np

        self.models = []
        for horizon in range(1, MAX_HORIZON + 1):
            origins = range(max(LOOKBACKS), train_end - horizon)
            features = np.asarray(
                [_feature_row(closes, origin) for origin in origins], dtype=float
            )
            targets = np.asarray(
                [math.log(closes[origin + horizon]) for origin in origins], dtype=float
            )
            models_for_horizon = []
            for quantile in QUANTILES:
                model = LGBMRegressor(
                    objective="quantile",
                    alpha=quantile,
                    n_estimators=80,
                    learning_rate=0.05,
                    num_leaves=15,
                    max_depth=5,
                    min_child_samples=10,
                    random_state=42,
                    n_jobs=BENCHMARK_THREADS,
                    verbosity=-1,
                    force_col_wise=True,
                )
                model.fit(features, targets)
                models_for_horizon.append(model)
            self.models.append(models_for_horizon)

    def predict(self, closes: Sequence[float], origin: int) -> list[list[float]]:
        import numpy as np

        features = np.asarray([_feature_row(closes, origin)], dtype=float)
        return [
            [
                float(math.exp(model.predict(features)[0]))
                for model in models_for_horizon
            ]
            for models_for_horizon in self.models
        ]

    def artifact_bytes(self) -> int:
        return sum(
            len(model.booster_.model_to_string().encode())
            for models in self.models
            for model in models
        )


def _pinball_loss(actual: float, prediction: float, quantile: float) -> float:
    error = actual - prediction
    return max(quantile * error, (quantile - 1) * error)


def _score(
    predictions: Sequence[Sequence[Sequence[float]]],
    actuals: Sequence[Sequence[float]],
) -> tuple[dict[str, float], list[dict[str, float | int]]]:
    per_horizon = []
    for horizon_index in range(MAX_HORIZON):
        values = [row[horizon_index] for row in predictions]
        targets = [row[horizon_index] for row in actuals]
        medians = [row[2] for row in values]
        pinball = [
            _pinball_loss(target, row[quantile_index], quantile)
            for target, row in zip(targets, values)
            for quantile_index, quantile in enumerate(QUANTILES)
        ]
        coverage_50 = sum(
            row[1] <= target <= row[3] for target, row in zip(targets, values)
        ) / len(targets)
        coverage_80 = sum(
            row[0] <= target <= row[4] for target, row in zip(targets, values)
        ) / len(targets)
        per_horizon.append(
            {
                "horizon_weeks": horizon_index + 1,
                "mae": statistics.mean(
                    abs(target - prediction)
                    for target, prediction in zip(targets, medians)
                ),
                "rmse": math.sqrt(
                    statistics.mean(
                        (target - prediction) ** 2
                        for target, prediction in zip(targets, medians)
                    )
                ),
                "mean_pinball": statistics.mean(pinball),
                "coverage_50": coverage_50,
                "coverage_80": coverage_80,
                "interval_width_50": statistics.mean(row[3] - row[1] for row in values),
                "interval_width_80": statistics.mean(row[4] - row[0] for row in values),
            }
        )
    metrics = {
        "mae": statistics.mean(row["mae"] for row in per_horizon),
        "rmse": statistics.mean(row["rmse"] for row in per_horizon),
        "mean_pinball": statistics.mean(row["mean_pinball"] for row in per_horizon),
        "coverage_50": statistics.mean(row["coverage_50"] for row in per_horizon),
        "coverage_80": statistics.mean(row["coverage_80"] for row in per_horizon),
        "interval_width_50": statistics.mean(
            row["interval_width_50"] for row in per_horizon
        ),
        "interval_width_80": statistics.mean(
            row["interval_width_80"] for row in per_horizon
        ),
    }
    return metrics, per_horizon


def _candidate_measurement(
    candidate: Any, closes: Sequence[float], split: Split
) -> CandidateMeasurement:
    calibration_origins = list(
        range(split.calibration_start, split.calibration_end - MAX_HORIZON)
    )
    test_origins = list(range(split.test_start, split.test_end))
    with PeakRssSampler() as sampler:
        fit_started = time.perf_counter()
        candidate.fit(closes, split.train_end)
        fit_seconds = time.perf_counter() - fit_started

        calibration_predictions = [
            candidate.predict(closes, origin) for origin in calibration_origins
        ]
        calibration_actuals = _actuals(closes, calibration_origins)
        calibrator = ResidualQuantileCalibrator.fit(
            calibration_predictions,
            calibration_actuals,
            QUANTILES,
            preserve_median=candidate.preserve_median,
        )
        test_predictions = [
            candidate.predict(closes, origin) for origin in test_origins
        ]
        calibrated_predictions = calibrator.apply(test_predictions)
        test_actuals = _actuals(closes, test_origins)
        metrics, per_horizon = _score(calibrated_predictions, test_actuals)
        artifact_bytes = candidate.artifact_bytes() + len(calibrator.to_json_bytes())
        backtest_seconds = time.perf_counter() - fit_started
    return CandidateMeasurement(
        candidate.name,
        candidate.threads_configured,
        fit_seconds,
        backtest_seconds,
        sampler.peak_bytes,
        artifact_bytes,
        metrics,
        per_horizon,
    )


def run_benchmark(weekly: Sequence[dict[str, Any]]) -> dict[str, Any]:
    split = split_series(weekly)
    closes = [float(row["close"]) for row in weekly]
    candidates = [
        PersistenceCandidate(),
        GaussianRandomWalkCandidate(),
        LightGBMQuantileCandidate(),
    ]
    measurements = [
        _candidate_measurement(candidate, closes, split) for candidate in candidates
    ]
    return {
        "protocol": {
            "weekly_rows": len(weekly),
            "train_observations": split.train_end,
            "calibration_origins": [
                split.calibration_start,
                split.calibration_end - MAX_HORIZON - 1,
            ],
            "test_origins": [split.test_start, split.test_end - 1],
            "split_dates": {
                "train_last_observation": weekly[split.train_end - 1]["date"],
                "calibration_first_origin": weekly[split.calibration_start]["date"],
                "calibration_last_origin": weekly[
                    split.calibration_end - MAX_HORIZON - 1
                ]["date"],
                "test_first_origin": weekly[split.test_start]["date"],
                "test_last_origin": weekly[split.test_end - 1]["date"],
                "test_last_target": weekly[-1]["date"],
            },
            "horizons": [1, MAX_HORIZON],
            "quantiles": QUANTILES,
            "candidate_count": len(candidates),
            "actual_railway_cost_usd": 0.0,
            "limits": {
                "max_candidates": 3,
                "max_runtime_minutes": 30,
                "max_threads": BENCHMARK_THREADS,
                "max_memory_gb": RAILWAY_MEMORY_GB,
            },
            "calibrator": "split residual quantiles fitted on calibration origins",
            "target": "weekly ISO Sunday BTC/USD close",
            "leakage_control": "models train only on targets before train_end; calibration and test origins are disjoint",
            "overlap_policy": "adjacent feature windows may overlap because they use only values known at each origin; future targets never enter another split's features",
        },
        "candidates": [
            {
                "name": measurement.name,
                "threads_configured": measurement.threads_configured,
                "fit_seconds": measurement.fit_seconds,
                "backtest_seconds": measurement.backtest_seconds,
                "peak_rss_mb": measurement.peak_rss_bytes / (1024 * 1024),
                "artifact_bytes_model_plus_calibrator": measurement.artifact_bytes,
                "estimated_railway_equivalent_cost_usd": estimate_railway_cost_usd(
                    measurement.backtest_seconds
                ),
                "metrics": measurement.metrics,
                "per_horizon": measurement.per_horizon,
            }
            for measurement in measurements
        ],
    }


def _fetch_json(url: str) -> list[dict[str, Any]]:
    request = urllib.request.Request(
        url, headers={"User-Agent": "bitcoin-forecast-benchmark/1.0"}
    )
    with urllib.request.urlopen(request, timeout=60) as response:
        payload = json.loads(response.read())
    if not isinstance(payload, list):
        raise ValueError(f"Expected a list from {url}")
    return payload


def fetch_daily_snapshot(base_url: str, start: date, end: date) -> list[dict[str, Any]]:
    rows = []
    chunk_start = start
    while chunk_start <= end:
        chunk_end = min(end, chunk_start + timedelta(days=API_CHUNK_DAYS - 1))
        query = urllib.parse.urlencode(
            {
                "type": "history",
                "startDate": chunk_start.isoformat(),
                "endDate": chunk_end.isoformat(),
            }
        )
        rows.extend(_fetch_json(f"{base_url.rstrip('/')}/api/bitcoin?{query}"))
        chunk_start = chunk_end + timedelta(days=1)
    return rows


def _write_weekly_csv(path: Path, weekly: Sequence[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=("date", "close"))
        writer.writeheader()
        writer.writerows(weekly)


def _read_weekly_csv(path: Path) -> list[dict[str, Any]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return [
            {"date": row["date"], "close": float(row["close"])}
            for row in csv.DictReader(handle)
        ]


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run the bounded local Bitcoin forecast benchmark"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    snapshot = subparsers.add_parser("snapshot")
    snapshot.add_argument("--base-url", required=True)
    snapshot.add_argument("--start-date", required=True, type=date.fromisoformat)
    snapshot.add_argument("--end-date", required=True, type=date.fromisoformat)
    snapshot.add_argument("--output", required=True, type=Path)
    benchmark = subparsers.add_parser("benchmark")
    benchmark.add_argument("--snapshot", required=True, type=Path)
    benchmark.add_argument("--output", required=True, type=Path)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    if args.command == "snapshot":
        daily_rows = fetch_daily_snapshot(args.base_url, args.start_date, args.end_date)
        weekly = aggregate_daily_rows(daily_rows)
        _write_weekly_csv(args.output, weekly)
        print(
            json.dumps(
                {
                    "daily_rows": len(daily_rows),
                    "weekly_rows": len(weekly),
                    "first_week": weekly[0]["date"],
                    "last_week": weekly[-1]["date"],
                    "sha256": _file_sha256(args.output),
                    "output": str(args.output),
                },
                sort_keys=True,
            )
        )
        return 0

    weekly = _read_weekly_csv(args.snapshot)
    report = run_benchmark(weekly)
    report["snapshot"] = {
        "file_sha256": _file_sha256(args.snapshot),
        "weekly_rows": len(weekly),
        "first_week": weekly[0]["date"],
        "last_week": weekly[-1]["date"],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, indent=2, sort_keys=True), encoding="utf-8"
    )
    print(
        json.dumps(
            {"output": str(args.output), "weekly_rows": len(weekly)}, sort_keys=True
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
