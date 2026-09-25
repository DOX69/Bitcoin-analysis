from copy import deepcopy
from datetime import timedelta
import hashlib
import io
import json
from types import SimpleNamespace
import sys

import pytest

from forecast import research_audit as audit
from forecast import prospective_research as research
from forecast.test_prospective_research import emission


def report_bytes(*, legacy=False):
    document, weekly, now = emission()
    weekly.append({"date": now.date().isoformat(), "close": 101.0})
    report = research.score_emissions([document], weekly, now + timedelta(days=7))
    if legacy:
        report.pop("validation_status")
        for row in report["per_horizon"]:
            for key in ("validation_status", "minimum_counts_met", "guardrails_passed"):
                row.pop(key)
        for row in report["observations"][1]:
            row.pop("issued_at")
            row.pop("origin_close")
    return json.dumps(report).encode()


@pytest.mark.parametrize("legacy", [False, True])
def test_export_new_and_legacy_reports_without_fabricating_missing_metadata(legacy):
    raw = report_bytes(legacy=legacy)
    digest = hashlib.sha256(raw).hexdigest()
    result = audit.summarize(raw, raw, digest)
    assert result["report_sha256"] == digest
    assert result["expected_checksum_verified"]
    assert result["mature_points"] == 1
    assert len(result["per_horizon"]) == 52
    assert result["validation_status"] == "insufficient_evidence"
    point = result["observations"][0]
    assert point["actual"] == 101.0 and point["q50"] == 100.0
    assert point["mae"] == point["naive_mae"] == 1.0
    assert (point["issued_at"] is None) == legacy
    assert (point["origin_close"] is None) == legacy
    assert not result["publishable"] and not result["snapshot_copy_verified"]
    assert "insufficient_evidence" in audit.markdown(result)
    assert "| 52 | 0 |" in audit.markdown(result)


@pytest.mark.parametrize(
    "failure",
    ["copy", "digest", "daily", "duplicate", "aggregate", "decision", "horizons"],
)
def test_audit_rejects_corrupt_mixed_or_inconsistent_evidence(failure):
    raw = report_bytes()
    if failure == "copy":
        with pytest.raises(ValueError, match="copy differs"):
            audit.summarize(raw, b"{}")
        return
    if failure == "digest":
        with pytest.raises(ValueError, match="checksum"):
            audit.summarize(raw, raw, "0" * 64)
        return
    report = json.loads(raw)
    if failure == "daily":
        report["model_manifest_sha256"] = "daily-model"
    elif failure == "duplicate":
        report["observations"]["1"] *= 2
        report["per_horizon"][0]["origins"] = 2
    elif failure == "aggregate":
        report["per_horizon"][0]["mae"] += 1
    elif failure == "decision":
        report["ready_for_confirmation_review"] = True
    else:
        report["per_horizon"].pop()
    changed = json.dumps(report).encode()
    with pytest.raises(ValueError):
        audit.summarize(changed, changed)


class ReadOnlyObjects:
    """No write/list/repair operations exist on this fake client."""

    def __init__(self, objects):
        self.objects = objects
        self.reads = []

    def get_object(self, *, Bucket, Key):
        self.reads.append(Key)
        return {"Body": io.BytesIO(self.objects[Key])}


def test_cloud_audit_only_reads_exact_report_and_snapshot_and_refuses_bad_copy():
    key = audit.PREFIX + "/reports/example.json"
    snapshot_key = audit.PREFIX + "/snapshots/example.json"
    snapshot = b"[]"
    report = json.loads(report_bytes())
    report.update(
        snapshot_key=snapshot_key, snapshot_sha256=hashlib.sha256(snapshot).hexdigest()
    )
    raw = json.dumps(report).encode()
    objects = {key: raw, snapshot_key: snapshot}
    source = SimpleNamespace(
        bucket="primary", client=ReadOnlyObjects(deepcopy(objects))
    )
    backup = SimpleNamespace(bucket="backup", client=ReadOnlyObjects(deepcopy(objects)))
    result = audit.audit_cloud(source, backup, key)
    assert result["snapshot_copy_verified"] and not result["expected_checksum_verified"]
    assert source.client.reads == backup.client.reads == [key, snapshot_key]
    assert source.client.objects == backup.client.objects == objects
    backup.client.objects[snapshot_key] = b"[1]"
    with pytest.raises(ValueError, match="copy differs"):
        audit.audit_cloud(source, backup, key)
    with pytest.raises(ValueError, match="Independent destination"):
        audit.audit_cloud(source, source, key)
    with pytest.raises(ValueError, match="Development hybrid"):
        audit.audit_cloud(source, backup, "production/reports/example.json")


def test_local_cli_is_read_only_and_preserves_archives(monkeypatch, tmp_path, capsys):
    raw = report_bytes(legacy=True)
    source = tmp_path / "report.json"
    backup = tmp_path / "copy.json"
    source.write_bytes(raw)
    backup.write_bytes(raw)
    monkeypatch.setattr(
        sys, "argv", ["audit", "--report", str(source), "--copy", str(backup)]
    )
    audit.main()
    assert json.loads(capsys.readouterr().out)["mature_points"] == 1
    assert source.read_bytes() == backup.read_bytes() == raw
    assert len(list(tmp_path.iterdir())) == 2
