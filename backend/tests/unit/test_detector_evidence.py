import json

from app.services import detector_evidence


def test_verified_transfer_evidence_is_separate_and_consistent():
    evidence = detector_evidence.singaporean_detector_evidence()
    assert evidence["verified"]
    assert evidence["split"] == "test"
    assert evidence["fine_tuned_on_singaporean"] is False
    assert evidence["images"] == 31 and evidence["labelled_plates"] == 33
    assert evidence["operational_metrics"]["true_positive_plates"] == 24
    assert evidence["operational_metrics"]["recall"] == 24 / 33
    assert evidence["false_positive_rate"] is None


def test_missing_or_unverified_evidence_is_not_presented_as_verified(tmp_path, monkeypatch):
    path = tmp_path / "evidence.json"
    monkeypatch.setattr(detector_evidence, "EVIDENCE_PATH", path)
    assert detector_evidence.singaporean_detector_evidence() is None
    path.write_text(json.dumps({"verified": False}))
    assert detector_evidence.singaporean_detector_evidence() is None
