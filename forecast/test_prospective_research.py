from copy import deepcopy
from datetime import date, datetime, timedelta, timezone
import json
import hashlib
from pathlib import Path
import sys

import pytest

from forecast import prospective_research as research


def test_frozen_sources_allow_only_git_line_ending_conversion(monkeypatch, tmp_path):
    source = tmp_path / "recipe.py"
    original = b"def predict():\r\n    return 1\r\n"
    source.write_bytes(original.replace(b"\r\n", b"\n"))
    distribution = tmp_path / "standardized-distribution.json"
    distribution.write_text('{"quantiles": []}')
    manifest = tmp_path / "manifest.json"
    manifest.write_text(
        json.dumps(
            {
                "dependencies": research.dependencies(),
                "source_sha256": {source.name: hashlib.sha256(original).hexdigest()},
            }
        )
    )
    monkeypatch.setattr(research, "MODEL_MANIFEST", research.sha256(manifest))
    monkeypatch.setattr(research, "DISTRIBUTION_HASH", research.sha256(distribution))
    monkeypatch.setattr(research.hybrid, "sources", lambda: [source])
    assert research.frozen_distribution(tmp_path) == []
    source.write_bytes(original.replace(b"return 1", b"return 2"))
    with pytest.raises(ValueError, match="source changed"):
        research.frozen_distribution(tmp_path)


def emission():
    start = date(2024, 1, 1)
    weekly = [
        {"date": (start + timedelta(weeks=i)).isoformat(), "close": 100.0}
        for i in range(140)
    ]
    now = datetime.combine(
        start + timedelta(weeks=140), datetime.min.time(), timezone.utc
    )
    document = research.make_emission(
        weekly, [[-2, -1, 0, 1, 2]] * 52, now, evidence="prospective"
    )
    return document, weekly, now


def test_target_is_not_mature_on_its_sunday():
    document, weekly, now = emission()
    next_monday = date.fromisoformat(weekly[-1]["date"]) + timedelta(weeks=1)
    weekly.append({"date": next_monday.isoformat(), "close": 101.0})
    sunday = now + timedelta(days=6)
    report = research.score_emissions([document], weekly, sunday)
    assert all(row["origins"] == 0 for row in report["per_horizon"])
    report = research.score_emissions([document], weekly, sunday + timedelta(days=1))
    assert report["per_horizon"][0]["origins"] == 1
    assert report["per_horizon"][1]["origins"] == 0
    assert not report["minimum_counts_met"]
    assert not report["publishable"]


def test_refuses_duplicate_synthetic_backdated_and_wrong_targets():
    document, weekly, now = emission()
    with pytest.raises(ValueError, match="Duplicate"):
        research.score_emissions([document, document], weekly, now)
    for changed in (
        {"evidence": "fixture"},
        {"created_at": (now + timedelta(days=2)).isoformat()},
    ):
        with pytest.raises(ValueError):
            research.score_emissions([{**document, **changed}], weekly, now)
    altered = deepcopy(document)
    altered["points"][0]["target_date"] = now.date().isoformat()
    with pytest.raises(ValueError, match="target"):
        research.validate_emission(altered)


def test_emission_refuses_stale_snapshot_and_wrong_day():
    _, weekly, now = emission()
    for observed, created in ((weekly[:-1], now), (weekly, now + timedelta(days=2))):
        with pytest.raises(ValueError):
            research.make_emission(
                observed, [[-2, -1, 0, 1, 2]] * 52, created, evidence="fixture"
            )


def test_empty_evidence_keeps_all_52_horizons_explicitly_immature():
    report = research.score_emissions([], [], datetime.now(timezone.utc))
    assert len(report["per_horizon"]) == 52
    assert all(row["wis"] is None for row in report["per_horizon"])
    assert not report["ready_for_confirmation_review"]


def test_legacy_exception_is_limited_to_the_previously_frozen_emission():
    document, _, _ = emission()
    origin = date(2026, 8, 31)
    document.update(
        {
            "origin_week": str(origin),
            "created_at": "2026-09-10T18:03:51.868753+00:00",
            "legacy_shadow_sha256": research.LEGACY_SHADOW_HASH,
        }
    )
    for point in document["points"]:
        point["target_date"] = str(
            origin + timedelta(days=6, weeks=point["horizon_weeks"])
        )
    research.validate_emission(document)
    with pytest.raises(ValueError, match="weekly slot"):
        research.validate_emission(
            {**document, "legacy_shadow_sha256": "not-the-published-hash"}
        )
    with pytest.raises(ValueError, match="weekly slot"):
        research.validate_emission(
            {**document, "created_at": "2026-09-11T18:03:51.868753+00:00"}
        )


def test_legacy_reader_refuses_an_unrecognized_archive(tmp_path):
    (tmp_path / "research-shadow.json").write_text("{}")
    with pytest.raises(ValueError, match="Original shadow changed"):
        research.read_legacy_emission(tmp_path, [[-2, -1, 0, 1, 2]] * 52)


def test_archive_reader_rejects_modified_source_snapshot(tmp_path):
    document, weekly, _ = emission()
    first = date.fromisoformat(weekly[0]["date"])
    daily = [
        {"date": (first + timedelta(days=i)).isoformat(), "close": 100.0}
        for i in range(140 * 7)
    ]
    snapshot = tmp_path / "daily.json"
    research.write_json(snapshot, daily)
    document.update(
        {
            "daily_snapshot_file": str(snapshot),
            "daily_snapshot_sha256": research.sha256(snapshot),
        }
    )
    archive = tmp_path / "emissions"
    archive.mkdir()
    path = archive / f"{document['origin_week']}.json"
    research.write_json(path, document)
    path.with_suffix(".sha256").write_text(research.sha256(path))
    assert len(research.read_emissions(archive, [[-2, -1, 0, 1, 2]] * 52)) == 1
    daily[-1]["close"] = 101.0
    snapshot.write_text(json.dumps(daily))
    with pytest.raises(ValueError, match="source snapshot changed"):
        research.read_emissions(archive, [[-2, -1, 0, 1, 2]] * 52)


def test_cli_archives_source_before_emission_and_preserves_monday_on_tuesday(
    monkeypatch, tmp_path
):
    _, weekly, monday = emission()
    first = date.fromisoformat(weekly[0]["date"])
    daily = [
        {"date": (first + timedelta(days=i)).isoformat(), "close": 100.0}
        for i in range(140 * 7)
    ]

    class Clock(datetime):
        current = monday

        @classmethod
        def now(cls, tz=None):
            return cls.current

    monkeypatch.setattr(research, "datetime", Clock)
    monkeypatch.setattr(
        research, "frozen_distribution", lambda _: [[-2, -1, 0, 1, 2]] * 52
    )
    monkeypatch.setattr(research.b, "fetch_daily_snapshot", lambda *args: daily)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "collector",
            "--bundle",
            str(tmp_path),
            "--directory",
            str(tmp_path / "observations"),
            "--base-url",
            "https://fixture.invalid",
        ],
    )
    research.main()
    path = next((tmp_path / "observations" / "emissions").glob("*.json"))
    original = path.read_bytes()
    document = json.loads(original)
    assert (
        research.sha256(Path(document["daily_snapshot_file"]))
        == document["daily_snapshot_sha256"]
    )
    Clock.current += timedelta(days=1)
    research.main()
    assert path.read_bytes() == original
    path.write_text("{}")
    Clock.current += timedelta(seconds=1)
    with pytest.raises(ValueError, match="Archived emission changed"):
        research.main()


def test_rescoring_and_source_revision_do_not_add_evidence():
    document, weekly, now = emission()
    weekly.append({"date": now.date().isoformat(), "close": 101.0})
    original = deepcopy(document)
    first = research.score_emissions([document], weekly, now + timedelta(days=7))
    again = research.score_emissions([document], weekly, now + timedelta(days=8))
    weekly[-1]["close"] = 102.0
    revised = research.score_emissions([document], weekly, now + timedelta(days=9))
    for report in (first, again, revised):
        assert report["validation_status"] == "insufficient_evidence"
        assert report["per_horizon"][0]["validation_status"] == "insufficient_evidence"
        assert sum(row["origins"] for row in report["per_horizon"]) == 1
        assert not report["ready_for_confirmation_review"]
        assert not report["publishable"]
        observation = report["observations"][1][0]
        assert observation["origin_close"] == document["origin_close"]
        assert observation["issued_at"] == document["created_at"]
    assert first["observations"] == again["observations"]
    assert revised["observations"][1][0]["mae"] != first["observations"][1][0]["mae"]
    assert document == original


@pytest.mark.parametrize(
    "origins,blocks,mae,c50,c80,expected",
    [
        (1, 1, 1, 1, 1, "insufficient_evidence"),
        (103, 2, 1, 0.5, 0.8, "insufficient_evidence"),
        (104, 1, 1, 0.5, 0.8, "insufficient_evidence"),
        (104, 2, 1.05, 0.4, 0.7, "guardrails_met"),
        (104, 2, 1.05, 0.6, 0.9, "guardrails_met"),
        (104, 2, 1.05001, 0.5, 0.8, "outside_guardrails"),
        (104, 2, 1, 0.60001, 0.8, "outside_guardrails"),
        (104, 2, 1, 0.5, 0.69999, "outside_guardrails"),
    ],
)
def test_evidence_status_preserves_count_block_and_quality_thresholds(
    origins, blocks, mae, c50, c80, expected
):
    row = {
        "origins": origins,
        "dependence_blocks": [{"complete_contiguous": True}] * blocks,
        "mae": mae,
        "naive_mae": 1,
        "coverage_50": c50,
        "coverage_80": c80,
    }
    assert research.horizon_assessment(row)["validation_status"] == expected
