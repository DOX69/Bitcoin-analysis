from datetime import date, datetime, timedelta, timezone

import pytest

from forecast import candidate_cloud as cloud
from forecast.storage_artifacts import ArtifactRepository
from forecast.test_backups import Objects


class Candidate:
    name = "lightgbm_quantile"

    def predict(self, closes, origin):
        current = closes[origin]
        return [
            [current * value for value in (0.8, 0.9, 1.0, 1.1, 1.2)] for _ in range(52)
        ]


def weekly_rows(count=37):
    start = date(2026, 1, 5)
    return [
        {"date": (start + timedelta(weeks=index)).isoformat(), "close": 100.0 + index}
        for index in range(count)
    ]


def test_candidate_emission_is_frozen_and_scores_only_mature_targets():
    weekly = weekly_rows()
    created = datetime(2026, 9, 21, tzinfo=timezone.utc)
    document = cloud.make_emission(weekly, Candidate(), "manifest-sha", created)

    cloud.validate_emission(document)
    assert document["candidate"] == "lightgbm_quantile"
    assert document["model_manifest_sha256"] == "manifest-sha"
    assert document["origin_week"] == weekly[-1]["date"]
    assert len(document["points"]) == 52

    later_week = {
        "date": (
            date.fromisoformat(weekly[-1]["date"]) + timedelta(weeks=1)
        ).isoformat(),
        "close": 110.0,
    }
    report = cloud.score_emissions(
        [document], weekly + [later_week], created + timedelta(days=7)
    )

    assert report["candidate"] == "lightgbm_quantile"
    assert report["per_horizon"][0]["origins"] == 1
    assert report["per_horizon"][1]["origins"] == 0
    assert report["publishable"] is False
    assert report["validation_status"] == "insufficient_evidence"


def test_candidate_emission_rejects_mixed_recipe():
    weekly = weekly_rows()
    document = cloud.make_emission(
        weekly,
        Candidate(),
        "manifest-sha",
        datetime(2026, 9, 21, tzinfo=timezone.utc),
    )
    document["candidate"] = "gaussian_random_walk"

    with pytest.raises(ValueError, match="candidate"):
        cloud.validate_emission(document)


def test_candidate_collect_reuses_immutable_emission(monkeypatch, tmp_path):
    daily = []
    start = date(2026, 1, 5)
    for index in range(37 * 7):
        daily.append(
            {
                "date": (start + timedelta(days=index)).isoformat(),
                "close": 100.0 + index,
            }
        )
    source = ArtifactRepository(Objects(), "source")
    backup = ArtifactRepository(Objects(), "backup")
    load_count = 0

    def load_model(*_args):
        nonlocal load_count
        load_count += 1
        directory = tmp_path / f"root-{load_count}" / "model"
        directory.mkdir(parents=True)
        return Candidate(), directory

    monkeypatch.setattr(
        cloud,
        "_ensure_model",
        lambda *_args: (
            {"candidate": "lightgbm_quantile", "context": {"last_week": "2026-09-14"}},
            "manifest-sha",
        ),
    )
    monkeypatch.setattr(cloud, "_load_model", load_model)
    now = datetime(2026, 9, 21, tzinfo=timezone.utc)

    first = cloud.collect(source, backup, daily, now)
    second = cloud.collect(source, backup, daily, now + timedelta(days=1))

    assert first["emissions"] == second["emissions"] == 1
    assert first["independent_copy_verified"]
    assert source.client.objects == backup.client.objects
