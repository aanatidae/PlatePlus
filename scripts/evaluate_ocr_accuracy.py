"""Calculate OCR exact-match accuracy from verified ground truth and OCR candidates."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

from alpr.plate.normalization import is_plausible_malaysian_plate, normalize_plate_text

CONDITION_ALIASES = {"glare_or_exposure": "glare_or_overexposure"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ground-truth", type=Path, required=True)
    parser.add_argument("--candidates", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    return parser.parse_args()


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def main() -> None:
    args = parse_args()
    ground_truth_rows = read_rows(args.ground_truth)
    scorable_rows = [
        row
        for row in ground_truth_rows
        if row.get("review_status", "reviewed").strip().lower() == "reviewed"
        and row.get("ocr_scorable", "").strip().lower() == "true"
    ]
    ground_truth = {
        row["image_path"]: row.get("verified_ground_truth_plate", row.get("ground_truth_plate", ""))
        for row in scorable_rows
        if row.get("verified_ground_truth_plate", row.get("ground_truth_plate", "")).strip()
    }
    if not ground_truth:
        raise ValueError("at least one human-verified ground-truth plate is required")

    evaluated_rows: list[dict[str, str]] = []
    for candidate in read_rows(args.candidates):
        expected = ground_truth.get(candidate["image_path"])
        if expected is None:
            continue
        predicted_normalized = normalize_plate_text(candidate["ocr_normalized_text"])
        expected_normalized = normalize_plate_text(expected)
        evaluated_rows.append(
            {
                **candidate,
                "ground_truth_plate": expected,
                "ground_truth_normalized": expected_normalized,
                "exact_match": str(predicted_normalized == expected_normalized).lower(),
            }
        )

    if len(evaluated_rows) != len(ground_truth):
        raise ValueError("every ground-truth image must have a corresponding OCR candidate")

    correct = sum(row["exact_match"] == "true" for row in evaluated_rows)
    rejected = sum(
        not row["ocr_normalized_text"] or not is_plausible_malaysian_plate(row["ocr_normalized_text"])
        for row in evaluated_rows
    )
    low_confidence = sum(float(row["ocr_confidence"]) < 0.70 for row in evaluated_rows)
    metrics = {
        "reviewed_sample_count": sum(
            row.get("review_status", "reviewed").strip().lower() == "reviewed"
            for row in ground_truth_rows
        ),
        "ocr_scorable_sample_count": len(scorable_rows),
        "verified_ground_truth_available_count": len(ground_truth),
        "excluded_non_scorable_count": len(ground_truth_rows) - len(scorable_rows),
        "evaluation_count": len(evaluated_rows),
        "exact_match_count": correct,
        "exact_match_accuracy": correct / len(evaluated_rows),
        "failure_count": len(evaluated_rows) - correct,
        "rejected_read_count": rejected,
        "low_confidence_read_count": low_confidence,
    }
    if any(
        row.get("condition_labels", row.get("condition", "")).strip()
        for row in ground_truth_rows
    ):
        condition_metrics: dict[str, dict[str, int | float]] = {}
        conditions = {
            row["image_path"]: row.get("condition_labels", row.get("condition", "unclassified")).strip()
            or "unclassified"
            for row in ground_truth_rows
        }
        for row in evaluated_rows:
            for condition in {
                CONDITION_ALIASES.get(item.strip(), item.strip())
                for item in conditions[row["image_path"]].split(";")
                if item.strip()
            }:
                bucket = condition_metrics.setdefault(
                    condition,
                    {"scorable_samples": 0, "exact_matches": 0, "rejected_reads": 0, "low_confidence_reads": 0},
                )
                bucket["scorable_samples"] += 1
                bucket["exact_matches"] += int(row["exact_match"] == "true")
                bucket["rejected_reads"] += int(
                    not row["ocr_normalized_text"]
                    or not is_plausible_malaysian_plate(row["ocr_normalized_text"])
                )
                bucket["low_confidence_reads"] += int(float(row["ocr_confidence"]) < 0.70)
        for bucket in condition_metrics.values():
            bucket["exact_match_accuracy"] = bucket["exact_matches"] / bucket["scorable_samples"]
        metrics["condition_breakdown"] = condition_metrics
    args.output_dir.mkdir(parents=True, exist_ok=True)
    with (args.output_dir / "ocr_evaluation_results.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(evaluated_rows[0]))
        writer.writeheader()
        writer.writerows(evaluated_rows)
    (args.output_dir / "ocr_evaluation_metrics.json").write_text(
        json.dumps(metrics, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(metrics))


if __name__ == "__main__":
    main()
