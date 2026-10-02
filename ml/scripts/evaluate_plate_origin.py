"""Evaluate deterministic origin rules on a separately labelled text fixture.

This is a synthetic pattern check, not an OCR or real-world origin benchmark.
"""

from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from pathlib import Path

from alpr.plate.origin import classify_plate_origin

ORIGINS = ("malaysian", "singaporean", "unknown")
CASE_TYPES = ("supported", "ambiguous", "unsupported")
REQUIRED_COLUMNS = {
    "sample_id", "plate_text", "reference_origin", "expected_decision",
    "expected_reason", "case_type", "label_basis",
}
ML_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_FIXTURE = ML_ROOT / "evaluation" / "origin" / "labels.csv"
DEFAULT_OUTPUT = ML_ROOT / "evaluation" / "origin" / "results.json"


def load_cases(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as source:
        reader = csv.DictReader(source)
        if reader.fieldnames is None or set(reader.fieldnames) != REQUIRED_COLUMNS:
            raise ValueError("Origin fixture columns do not match the documented schema.")
        cases = list(reader)
    if not cases:
        raise ValueError("Origin fixture is empty.")
    ids: set[str] = set()
    plates: set[str] = set()
    for case in cases:
        sample_id = case["sample_id"]
        plate = case["plate_text"]
        if not sample_id or sample_id in ids or plate in plates:
            raise ValueError(f"Missing or duplicate sample identifier/plate: {sample_id}")
        ids.add(sample_id)
        plates.add(plate)
        if case["reference_origin"] not in ORIGINS or case["expected_decision"] not in ORIGINS:
            raise ValueError(f"Invalid origin label: {sample_id}")
        if case["case_type"] not in CASE_TYPES or case["label_basis"] != "synthetic_scenario":
            raise ValueError(f"Invalid case type or provenance: {sample_id}")
        if case["case_type"] == "supported" and case["expected_decision"] != case["reference_origin"]:
            raise ValueError(f"Supported case must expect its reference origin: {sample_id}")
        if case["case_type"] == "ambiguous" and (
            case["reference_origin"] == "unknown"
            or case["expected_decision"] != "unknown"
            or case["expected_reason"] != "ambiguous_supported_patterns"
        ):
            raise ValueError(f"Invalid ambiguous-case label: {sample_id}")
        if case["case_type"] == "unsupported" and (
            case["reference_origin"] != "unknown"
            or case["expected_decision"] != "unknown"
            or case["expected_reason"] != "unsupported_plate_pattern"
        ):
            raise ValueError(f"Invalid unsupported-case label: {sample_id}")
    return cases


def evaluate(cases: list[dict[str, str]]) -> dict[str, object]:
    matrix = {reference: {prediction: 0 for prediction in ORIGINS} for reference in ORIGINS}
    category_total: Counter[str] = Counter()
    category_rejected: Counter[str] = Counter()
    exact_origin_matches = 0
    policy_matches = 0
    results: list[dict[str, str | bool]] = []
    for case in cases:
        decision = classify_plate_origin(case["plate_text"])
        reference = case["reference_origin"]
        category = case["case_type"]
        matrix[reference][decision.origin] += 1
        category_total[category] += 1
        exact_origin_matches += decision.origin == reference
        policy_match = (
            decision.origin == case["expected_decision"]
            and decision.reason == case["expected_reason"]
        )
        policy_matches += policy_match
        if category in {"ambiguous", "unsupported"} and policy_match:
            category_rejected[category] += 1
        results.append({
            "sample_id": case["sample_id"],
            "plate_text": case["plate_text"],
            "reference_origin": reference,
            "case_type": category,
            "expected_decision": case["expected_decision"],
            "predicted_origin": decision.origin,
            "predicted_reason": decision.reason,
            "policy_match": policy_match,
        })
    total = len(cases)
    return {
        "fixture_type": "synthetic_text_only",
        "sample_count": total,
        "reference_origin_confusion": matrix,
        "exact_origin_matches": exact_origin_matches,
        "exact_origin_accuracy_percent": round(100 * exact_origin_matches / total, 1),
        "malaysian_to_singaporean": matrix["malaysian"]["singaporean"],
        "singaporean_to_malaysian": matrix["singaporean"]["malaysian"],
        "malaysian_to_unknown": matrix["malaysian"]["unknown"],
        "singaporean_to_unknown": matrix["singaporean"]["unknown"],
        "ambiguous_rejected": {"correct": category_rejected["ambiguous"], "total": category_total["ambiguous"]},
        "unsupported_rejected": {"correct": category_rejected["unsupported"], "total": category_total["unsupported"]},
        "policy_decision_agreement": {"correct": policy_matches, "total": total},
        "cases": results,
        "limitations": (
            "Synthetic normalized text only; no image, OCR, issued-registration, "
            "or real-world population accuracy is measured. The intentionally enriched "
            "ambiguous cases make the aggregate percentage non-representative."
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fixture", type=Path, default=DEFAULT_FIXTURE)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    report = evaluate(load_cases(args.fixture))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(f"{report['exact_origin_matches']}/{report['sample_count']} exact origin labels; "
          f"MY-to-SG {report['malaysian_to_singaporean']}, "
          f"SG-to-MY {report['singaporean_to_malaysian']}; "
          f"report: {args.output}")


if __name__ == "__main__":
    main()
