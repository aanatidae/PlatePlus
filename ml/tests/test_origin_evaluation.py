from __future__ import annotations

from hashlib import sha1
from pathlib import Path

from scripts.evaluate_plate_origin import DEFAULT_FIXTURE, evaluate, load_cases


def test_labelled_synthetic_fixture_reports_confusion_and_safe_rejections() -> None:
    cases = load_cases(DEFAULT_FIXTURE)
    report = evaluate(cases)

    assert report["sample_count"] == 32
    assert report["reference_origin_confusion"] == {
        "malaysian": {"malaysian": 9, "singaporean": 0, "unknown": 3},
        "singaporean": {"malaysian": 0, "singaporean": 8, "unknown": 4},
        "unknown": {"malaysian": 0, "singaporean": 0, "unknown": 8},
    }
    assert report["exact_origin_matches"] == 25
    assert report["ambiguous_rejected"] == {"correct": 7, "total": 7}
    assert report["unsupported_rejected"] == {"correct": 8, "total": 8}
    assert report["policy_decision_agreement"] == {"correct": 32, "total": 32}


def test_origin_evaluation_preserves_the_protected_ocr_manifest():
    manifest = Path(__file__).resolve().parents[1] / "datasets/car_plate_test_manifest.txt"
    # Git blob hash ignores platform-specific CRLF checkout conversion and matches
    # the preserved manifest identity recorded in the V3 harness.
    before = manifest.read_text(encoding="utf-8")
    content = before.encode("utf-8")
    blob = f"blob {len(content)}\0".encode() + content
    assert sha1(blob).hexdigest() == "b723d69850778f9a65d1a3db1bd386272aea80f7"
    evaluate(load_cases(DEFAULT_FIXTURE))
    assert manifest.read_text(encoding="utf-8") == before
