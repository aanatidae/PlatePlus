"""Calculate OCR exact-match accuracy from verified ground truth and OCR candidates."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

from alpr.plate.normalization import normalize_plate_text


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
    ground_truth = {row["image_path"]: row["ground_truth_plate"] for row in read_rows(args.ground_truth)}
    if not ground_truth or any(not value.strip() for value in ground_truth.values()):
        raise ValueError("ground truth must contain a verified plate value for every row")

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
    metrics = {
        "evaluation_count": len(evaluated_rows),
        "exact_match_count": correct,
        "exact_match_accuracy": correct / len(evaluated_rows),
        "failure_count": len(evaluated_rows) - correct,
    }
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
