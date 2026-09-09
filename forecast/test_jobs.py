from datetime import date, datetime, timedelta, timezone
import json
import math
import os
from pathlib import Path

import pytest

from forecast import jobs


UTC = timezone.utc
MONDAY = datetime(2026, 9, 7, 2, tzinfo=UTC)


def test_only_monday_and_one_tuesday_attempt_are_eligible():
    assert jobs.emission_slot(MONDAY) == (date(2026, 8, 31), "valid")
    assert jobs.emission_slot(MONDAY + timedelta(days=1)) == (
        date(2026, 8, 31),
        "delayed",
    )
    for days in range(2, 7):
        assert jobs.emission_slot(MONDAY + timedelta(days=days)) is None
    with pytest.raises(ValueError, match="UTC"):
        jobs.emission_slot(MONDAY.replace(tzinfo=None))


def test_missing_day_and_stale_week_are_not_imputed():
    daily = [
        {"date": (date(2026, 8, 31) + timedelta(days=i)).isoformat(), "close": 100}
        for i in range(7)
    ]
    assert jobs.fresh_weekly(daily, MONDAY)[-1]["date"] == "2026-08-31"
    with pytest.raises(ValueError, match="complete"):
        jobs.fresh_weekly(daily[:-1], MONDAY)
    with pytest.raises(ValueError, match="fresh"):
        jobs.fresh_weekly(daily, MONDAY + timedelta(days=7))
    with pytest.raises(ValueError, match="future"):
        jobs.fresh_weekly(daily + [{"date": "2026-09-07", "close": 110}], MONDAY)


@pytest.mark.parametrize(
    "measured,projected", [(5, 0), (0, 5), (float("nan"), 0), (-1, 0)]
)
def test_cost_gate_fails_closed_at_five_dollars(measured, projected):
    with pytest.raises(ValueError, match="cost"):
        jobs.check_cost(
            {"month": "2026-09", "measured_usd": measured, "projected_usd": projected},
            MONDAY,
        )


def test_cost_record_must_be_for_current_month():
    with pytest.raises(ValueError, match="month"):
        jobs.check_cost(
            {"month": "2026-08", "measured_usd": 0, "projected_usd": 0}, MONDAY
        )
    jobs.check_cost(
        {"month": "2026-09", "measured_usd": 1, "projected_usd": 4.99}, MONDAY
    )


def test_scoring_waits_until_target_day_closes_and_keeps_provenance():
    point = {
        "horizon_weeks": 1,
        "target_date": "2026-09-13",
        "USD": [80, 90, 100, 110, 120],
    }
    observed = {"date": "2026-09-13", "close": 130, "revision": "source-v1"}
    assert jobs.score_point(point, observed, 100, MONDAY + timedelta(days=6)) is None
    result = jobs.score_point(point, observed, 100, MONDAY + timedelta(days=7))
    assert result["mae"] == 30
    assert result["naive_mae"] == 30
    assert result["wis"] == pytest.approx((0.5 * 30 + 0.25 * 100 + 0.1 * 140) / 2.5)
    assert result["observation_revision"] == "source-v1"
    assert result["evidence"] == "unverified"
    assert jobs.score_point(point, None, 100, MONDAY + timedelta(days=7)) is None
    with pytest.raises(ValueError):
        jobs.score_point(
            point, {**observed, "close": math.nan}, 100, MONDAY + timedelta(days=7)
        )


def test_monthly_report_keeps_all_52_horizons_and_never_changes_model():
    rows = [
        {
            "horizon": 1,
            "metrics": {
                "mae": 4,
                "wis": 2,
                "coverage_50": 1,
                "coverage_80": 1,
                "naive_mae": 5,
            },
        }
    ]
    report = jobs.calibration_report(rows, "2026-09")
    assert len(report["per_horizon"]) == 52
    assert report["per_horizon"][0]["origins"] == 1
    assert report["per_horizon"][51]["origins"] == 0
    assert report["action"] == "manual_review_only"


def test_promotion_refuses_missing_horizon_confirmation_and_naive_recipe():
    rows = [
        {
            "horizon_weeks": h,
            "origins": 20,
            "mae": 1,
            "naive_mae": 1,
            "wis": 1,
            "coverage_50": 0.5,
            "coverage_80": 0.8,
        }
        for h in range(1, 53)
    ]
    report = {
        "candidate": "gaussian_random_walk",
        "per_horizon": rows,
        "confirmation_review": "review-with-block-dependence",
        "data_verified": True,
        "resources_verified": True,
        "evidence": "prospective",
    }
    jobs.check_promotion(report)
    for change in (
        {"per_horizon": rows[:-1]},
        {"confirmation_review": ""},
        {"candidate": "price_unchanged"},
        {"data_verified": False},
        {"evidence": "fixture"},
    ):
        with pytest.raises(ValueError, match="promotion"):
            jobs.check_promotion({**report, **change})
    active = [{**row, "wis": 1} for row in rows]
    with pytest.raises(ValueError, match="promotion"):
        jobs.check_promotion({**report, "active_per_horizon": active})


def test_retention_protects_active_rollback_shared_and_last_target():
    now = date(2026, 9, 7)
    assert not jobs.artifact_expired(
        now, protected=True, last_target=date(2020, 1, 1), rejected_at=None
    )
    assert not jobs.artifact_expired(
        now, protected=False, last_target=date(2024, 9, 8), rejected_at=None
    )
    assert jobs.artifact_expired(
        now, protected=False, last_target=date(2024, 9, 7), rejected_at=None
    )
    assert not jobs.artifact_expired(
        now, protected=False, last_target=None, rejected_at=date(2026, 6, 10)
    )
    assert jobs.artifact_expired(
        now, protected=False, last_target=None, rejected_at=date(2026, 6, 9)
    )
    assert not jobs.artifact_expired(
        now, protected=False, last_target=None, rejected_at=None
    )


@pytest.fixture
def connection():
    import psycopg
    from psycopg.conninfo import conninfo_to_dict

    url = os.getenv("FORECAST_JOBS_TEST_DATABASE_URL")
    if not url:
        pytest.skip(
            "Set FORECAST_JOBS_TEST_DATABASE_URL for isolated PostgreSQL job tests"
        )
    parsed = conninfo_to_dict(url)
    assert parsed["host"] in ("localhost", "127.0.0.1")
    assert parsed["dbname"] in ("forecast_jobs_test", "bitcoin_test")
    with psycopg.connect(url, autocommit=True) as conn:
        conn.execute("DROP SCHEMA IF EXISTS forecast CASCADE")
        for migration in sorted(
            (Path(__file__).parent / "migrations").glob("*.up.sql")
        ):
            conn.execute(migration.read_text())
        yield conn
        conn.execute("DROP SCHEMA IF EXISTS forecast CASCADE")


def daily_rows():
    return [
        {
            "date": (date(2026, 8, 31) + timedelta(days=i)).isoformat(),
            "close": 100,
            "revision": "r1",
        }
        for i in range(7)
    ]


def seeded_store(connection):
    from forecast.storage import ForecastStore
    from forecast.artifacts import FEATURES

    store = ForecastStore(connection)
    manifest = dict(
        schema_version=1,
        features=FEATURES,
        recalibration=None,
        quantiles=[0.1, 0.25, 0.5, 0.75, 0.9],
        horizons=list(range(1, 53)),
        files={"state.json": "fixture"},
    )
    store.register_version("candidate", manifest, "development/candidate")
    store.activate_version("candidate", lambda *args: None)
    return store


def candidate_loader(*args):
    from forecast.benchmark import PersistenceCandidate

    return PersistenceCandidate()


def snapshot_writer(prefix, document):
    return {"key": prefix + "/fixture-snapshot.json", "sha256": "fixture-only"}


def batch(connection, now=MONDAY, **overrides):
    return jobs.run_batch(
        connection,
        now=now,
        evidence="fixture",
        daily_loader=lambda cutoff: daily_rows(),
        fx_loader=lambda cutoff: {},
        candidate_loader=candidate_loader,
        snapshot_writer=snapshot_writer,
        cost={"month": "2026-09", "measured_usd": 0, "projected_usd": 1},
        **overrides,
    )


def test_repeated_batch_cannot_emit_twice_even_after_active_version_changes(connection):
    store = seeded_store(connection)
    assert batch(connection)["emission"] == "valid"
    manifest = connection.execute(
        "SELECT manifest FROM forecast.versions LIMIT 1"
    ).fetchone()[0]
    store.register_version("other", manifest, "development/other")
    store.activate_version("other", lambda *args: None)
    assert batch(connection)["emission"] == "already_published"
    assert (
        connection.execute("SELECT count(*) FROM forecast.emissions").fetchone()[0] == 1
    )


def test_failed_monday_and_single_tuesday_retry_then_skip(connection):
    seeded_store(connection)
    calls = []

    def broken(*args):
        calls.append(1)
        raise ValueError("bad artifact")

    def invoke(now):
        return jobs.run_batch(
            connection,
            now=now,
            evidence="fixture",
            daily_loader=lambda cutoff: daily_rows(),
            fx_loader=lambda cutoff: {},
            candidate_loader=broken,
            snapshot_writer=snapshot_writer,
            cost={"month": "2026-09", "measured_usd": 0, "projected_usd": 1},
        )

    assert invoke(MONDAY)["emission"] == "failed"
    assert invoke(MONDAY)["emission"] == "attempt_consumed"
    assert invoke(MONDAY + timedelta(days=1))["emission"] == "failed"
    assert invoke(MONDAY + timedelta(days=1))["emission"] == "attempt_consumed"
    assert invoke(MONDAY + timedelta(days=2))["emission"] == "outside_window"
    assert len(calls) == 2


def test_tuesday_emission_uses_real_date_and_scoring_is_idempotent(connection):
    seeded_store(connection)
    assert batch(connection, MONDAY + timedelta(days=1))["emission"] == "delayed"
    payload = connection.execute("SELECT payload FROM forecast.emissions").fetchone()[0]
    assert payload["emission_date"] == "2026-09-08"
    assert payload["origin_close"] == 100
    assert payload["snapshot_sha256"]
    future = daily_rows() + [
        {"date": "2026-09-13", "close": 120, "revision": "observed-v1"}
    ]
    for _ in range(2):
        result = jobs.run_batch(
            connection,
            now=MONDAY + timedelta(days=9),
            evidence="fixture",
            daily_loader=lambda cutoff: future,
            fx_loader=lambda cutoff: {},
            candidate_loader=candidate_loader,
            snapshot_writer=snapshot_writer,
            cost={"month": "2026-09", "measured_usd": 0, "projected_usd": 1},
        )
    assert result["emission"] == "outside_window"
    scores = connection.execute(
        "SELECT horizon,observed,metrics FROM forecast.scores"
    ).fetchall()
    assert len(scores) == 1
    assert scores[0][0:2] == (1, 120)
    assert scores[0][2]["naive_mae"] == 20
    assert scores[0][2]["evidence"] == "fixture"


def test_concurrent_worker_does_not_consume_attempt(connection):
    import psycopg

    with psycopg.connect(connection.info.dsn, autocommit=True) as other:
        other.execute("SELECT pg_advisory_lock(%s)", (jobs.JOB_LOCK,))
        assert batch(connection)["emission"] == "locked"
        assert (
            connection.execute("SELECT count(*) FROM forecast.attempts").fetchone()[0]
            == 0
        )
        other.execute("SELECT pg_advisory_unlock(%s)", (jobs.JOB_LOCK,))


def test_ingestion_success_survives_forecast_failure_and_runs_after_dbt(connection):
    from raw_ingest import orchestrator

    events = []

    def fail_forecast():
        events.append("forecast")
        raise ValueError("invalid artifact")

    result = orchestrator.run_pipeline(
        connection.info.dsn,
        run_id="test",
        market_ingestor=lambda *args: events.append("market"),
        indicator_ingestor=lambda *args: events.append("indicators"),
        dbt_runner=lambda *args: events.append("dbt"),
        forecast_runner=fail_forecast,
    )
    assert result == 0
    assert events == ["market", "indicators", "dbt", "forecast"]


def test_forecast_hook_is_disabled_without_explicit_config(monkeypatch):
    from raw_ingest import orchestrator

    monkeypatch.delenv("FORECAST_JOB_CONFIG", raising=False)
    assert orchestrator.run_forecast() == {"status": "disabled"}


def test_forecast_supervisor_bounds_one_combined_process(monkeypatch, tmp_path):
    from raw_ingest import orchestrator
    from forecast import pipeline

    calls = []
    monkeypatch.setenv("FORECAST_JOB_CONFIG", str(tmp_path / "config.json"))
    monkeypatch.setattr(
        pipeline,
        "supervise",
        lambda command, log_path, **limits: calls.append((command, limits)) or {},
    )
    orchestrator.run_forecast()
    assert len(calls) == 1
    assert calls[0][1] == {"seconds": 300, "rss_bytes": 4 * 1024**3}
    assert calls[0][0][-3:] == ["worker", "--config", str(tmp_path / "config.json")]
    assert "--no-sync" in calls[0][0]


def test_monthly_storage_selects_latest_revision_and_excludes_fixtures(connection):
    from forecast.storage import ForecastStore

    seeded_store(connection)
    batch(connection)
    identifier = connection.execute("SELECT id FROM forecast.emissions").fetchone()[0]
    store = ForecastStore(connection)
    metrics = {
        "mae": 5,
        "wis": 2,
        "coverage_50": 1,
        "coverage_80": 1,
        "naive_mae": 6,
        "evidence": "fixture",
    }
    store.record_score(identifier, 1, "v1", 105, metrics)
    store.record_score(identifier, 1, "v2", 103, {**metrics, "mae": 3})
    report = jobs.monthly_report(connection, "candidate", "2026-09", evidence="fixture")
    assert report["per_horizon"][0]["origins"] == 1
    assert report["per_horizon"][0]["mae"] == 3
    assert (
        jobs.monthly_report(connection, "candidate", "2026-09")["per_horizon"][0][
            "origins"
        ]
        == 0
    )
    assert (
        jobs.monthly_report(connection, "candidate", "2026-08", evidence="fixture")[
            "per_horizon"
        ][0]["origins"]
        == 0
    )


def test_purge_keeps_emission_metadata_and_protects_active(connection):
    seeded_store(connection)
    calls = []
    assert (
        jobs.purge_artifacts(
            connection, date(2029, 9, 7), lambda prefix, manifest: calls.append(prefix)
        )
        == []
    )
    manifest = connection.execute(
        "SELECT manifest FROM forecast.versions LIMIT 1"
    ).fetchone()[0]
    from forecast.storage import ForecastStore

    ForecastStore(connection).register_version(
        "rejected", manifest, "development/rejected"
    )
    connection.execute(
        "INSERT INTO forecast.maintenance(artifact_prefix,rejected_at) VALUES ('development/rejected','2026-01-01')"
    )
    assert jobs.purge_artifacts(
        connection, date(2026, 9, 7), lambda prefix, manifest: calls.append(prefix)
    ) == ["development/rejected"]
    assert calls == ["development/rejected"]
    assert (
        connection.execute("SELECT count(*) FROM forecast.versions").fetchone()[0] == 2
    )
    assert (
        jobs.purge_artifacts(
            connection, date(2026, 9, 7), lambda *args: pytest.fail("Already purged")
        )
        == []
    )


def test_database_loaders_bound_daily_and_freeze_real_fx_dates(connection):
    connection.execute("CREATE SCHEMA job_source")
    try:
        connection.execute(
            "CREATE TABLE job_source.obt_fact_day_btc(date_prices date,close_usd double precision)"
        )
        connection.execute(
            "INSERT INTO job_source.obt_fact_day_btc VALUES ('2026-09-06',100),('2026-09-07',110)"
        )
        connection.execute(
            "CREATE TABLE job_source.btc_usd_ohlcv(date date,close double precision,ingest_date_time timestamp)"
        )
        connection.execute(
            "INSERT INTO job_source.btc_usd_ohlcv VALUES ('2026-09-06',100,'2026-09-07 01:00:00'),('2026-09-06',999,'2026-09-08')"
        )
        connection.execute(
            "CREATE TABLE job_source.usd_eur_rates(date date,rate double precision,ingest_date_time timestamp)"
        )
        connection.execute(
            "CREATE TABLE job_source.usd_chf_rates(LIKE job_source.usd_eur_rates)"
        )
        for currency in ("eur", "chf"):
            connection.execute(
                f"INSERT INTO job_source.usd_{currency}_rates VALUES ('2026-09-04',0.9,'2026-09-05'),('2026-09-07',0.8,'2026-09-08')"
            )
        source = jobs.DatabaseSource(connection, "job_source", "job_source", MONDAY)
        rows = source.daily(date(2026, 9, 6))
        assert len(rows) == 1 and rows[0]["revision"]
        assert rows[0]["source"] == "job_source.btc_usd_ohlcv"
        assert rows[0]["observed_at"] == "2026-09-07T01:00:00+00:00"
        assert source.fx(date(2026, 9, 7))["EUR"] == {"date": "2026-09-04", "rate": 0.9}
    finally:
        connection.execute("DROP SCHEMA job_source CASCADE")


def test_artifact_loader_rejects_future_training_and_wrong_environment(tmp_path):
    class Repository:
        def materialize(self, *args):
            pytest.fail("Invalid manifest must fail before download")

    loader = jobs.artifact_loader(Repository(), "development")
    with pytest.raises(ValueError, match="environment"):
        loader(
            {"context": {"last_week": "2026-08-31"}},
            "production/model",
            date(2026, 8, 31),
        )
    with pytest.raises(ValueError, match="future"):
        loader(
            {"context": {"last_week": "2026-09-07"}},
            "development/model",
            date(2026, 8, 31),
        )


def test_quarterly_claim_cannot_bypass_failed_cycle_limit(connection):
    jobs.claim_quarter(connection, MONDAY, "snapshot-sha")
    with pytest.raises(ValueError, match="quarter"):
        jobs.claim_quarter(connection, MONDAY + timedelta(days=10), "another-snapshot")
    assert (
        connection.execute("SELECT count(*) FROM forecast.candidate_cycles").fetchone()[
            0
        ]
        == 1
    )


def test_worker_rejects_stale_cost_before_opening_database(
    tmp_path, monkeypatch, capsys
):
    import psycopg

    cost = tmp_path / "cost.json"
    cost.write_text(
        json.dumps({"month": "2001-01", "measured_usd": 0, "projected_usd": 0})
    )
    config = tmp_path / "config.json"
    config.write_text(json.dumps({"cost_record": str(cost)}))
    monkeypatch.setattr(
        psycopg,
        "connect",
        lambda *args, **kwargs: pytest.fail("Cost gate must run first"),
    )
    assert jobs.main(["worker", "--config", str(config)]) == 1
    assert "ValueError" in capsys.readouterr().out


def test_job_saves_previous_month_report_once(connection):
    seeded_store(connection)
    batch(connection)
    batch(connection)
    rows = connection.execute("SELECT month,report FROM forecast.reports").fetchall()
    assert len(rows) == 1
    assert rows[0][0] == date(2026, 8, 1)
    assert rows[0][1]["evidence"] == "prospective"


def test_real_bundle_registration_and_job_loader_roundtrip(connection, tmp_path):
    from forecast.artifacts import save_model
    from forecast.benchmark import GaussianRandomWalkCandidate
    from forecast.storage import ForecastStore
    from forecast.storage_artifacts import ArtifactRepository
    from forecast.test_storage_artifacts import Bucket

    candidate = GaussianRandomWalkCandidate()
    candidate.fit([100, 110, 105], 3)
    directory = tmp_path / "model"
    save_model(candidate, directory, {"last_week": "2026-08-31"})
    original = (directory / "manifest.json").read_bytes()
    repository = ArtifactRepository(Bucket(), "private")
    store = ForecastStore(connection)
    jobs.register_bundle(store, repository, directory, "v1", "development")
    manifest, prefix = connection.execute(
        "SELECT manifest,artifact_prefix FROM forecast.versions"
    ).fetchone()
    loaded = jobs.artifact_loader(repository, "development")(
        manifest, prefix, date(2026, 8, 31)
    )
    assert loaded.predict([100, 110, 105], 2) == candidate.predict([100, 110, 105], 2)
    assert (directory / "manifest.json").read_bytes() == original
    with pytest.raises(ValueError, match="manifest"):
        jobs.artifact_loader(repository, "development")(
            {**manifest, "context": {"last_week": "2020-01-01"}},
            prefix,
            date(2026, 8, 31),
        )


def test_snapshot_write_failure_prevents_publication(connection):
    seeded_store(connection)

    def failed(*args):
        raise OSError("snapshot storage unavailable")

    result = jobs.run_batch(
        connection,
        now=MONDAY,
        evidence="fixture",
        daily_loader=lambda _: daily_rows(),
        fx_loader=lambda _: {},
        candidate_loader=candidate_loader,
        snapshot_writer=failed,
        cost={"month": "2026-09", "measured_usd": 0, "projected_usd": 1},
    )
    assert result["emission"] == "failed"
    assert (
        connection.execute("SELECT count(*) FROM forecast.emissions").fetchone()[0] == 0
    )


def test_snapshot_is_private_immutable_and_verified():
    from forecast.storage_artifacts import ArtifactRepository
    from forecast.test_storage_artifacts import Bucket

    repository = ArtifactRepository(Bucket(), "private")
    value = {"daily": daily_rows(), "fx": {}}
    result = jobs.persist_snapshot(repository, "development/model", value)
    assert result["key"].startswith("development/model/snapshots/")
    assert len(result["sha256"]) == 64
    assert jobs.persist_snapshot(repository, "development/model", value) == result


def test_promotion_refuses_metrics_without_observations():
    rows = [
        {
            "horizon_weeks": h,
            "origins": 0,
            "mae": 1,
            "naive_mae": 1,
            "wis": 1,
            "coverage_50": 0.5,
            "coverage_80": 0.8,
        }
        for h in range(1, 53)
    ]
    with pytest.raises(ValueError, match="promotion"):
        jobs.check_promotion(
            {
                "candidate": "gaussian_random_walk",
                "per_horizon": rows,
                "evidence": "prospective",
                "confirmation_review": "review",
                "data_verified": True,
                "resources_verified": True,
            }
        )


def test_enabled_forecast_prevents_dbt_from_pruning_preinstalled_dependencies(
    monkeypatch,
):
    from raw_ingest import orchestrator

    calls = []
    monkeypatch.setenv("FORECAST_JOB_CONFIG", "C:/config/forecast.json")
    monkeypatch.setenv("DBT_TARGET_SCHEMA", "development")
    monkeypatch.setattr(
        orchestrator.subprocess, "run", lambda command, **kwargs: calls.append(command)
    )
    orchestrator.run_dbt_build("postgresql://postgres@localhost/bitcoin_test")
    assert "--no-sync" in calls[0]
