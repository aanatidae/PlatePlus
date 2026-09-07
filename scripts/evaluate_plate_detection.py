"""Calculate labelled detection outcomes from a verified development manifest."""

from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--predictions", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args()


def rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def main() -> None:
    args = parse_args()
    manifest = rows(args.manifest)
    predictions = {row["sample_id"]: row for row in rows(args.predictions)}
    results: list[dict[str, str]] = []
    counts: Counter[str] = Counter()
    for sample in manifest:
        present = sample["valid_plate_present"].strip().lower()
        if present not in {"true", "false"}:
            raise ValueError(f"{sample['sample_id']} needs a human-verified valid_plate_present value")
        prediction = predictions.get(sample["sample_id"])
        detected = prediction and prediction.get("plate_detected", "").strip().lower() == "true"
        outcome = (
            "true_positive" if present == "true" and detected else
            "false_negative" if present == "true" else
            "false_positive" if detected else "true_negative"
        )
        counts[outcome] += 1
        results.append({**sample, "plate_detected": str(bool(detected)).lower(), "detection_outcome": outcome})
    precision_denominator = counts["true_positive"] + counts["false_positive"]
    recall_denominator = counts["true_positive"] + counts["false_negative"]
    precision = counts["true_positive"] / precision_denominator if precision_denominator else None
    recall = counts["true_positive"] / recall_denominator if recall_denominator else None
    f1 = 2 * precision * recall / (precision + recall) if precision and recall else None
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.with_suffix(".csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=results[0].keys())
        writer.writeheader()
        writer.writerows(results)
    negative_examples = counts["true_negative"] + counts["false_positive"]
    false_positive_rate = counts["false_positive"] / negative_examples if negative_examples else None
    metrics = {
        "true_positive": counts["true_positive"],
        "false_negative": counts["false_negative"],
        "false_positive": counts["false_positive"],
        "true_negative": counts["true_negative"],
        "negative_examples": negative_examples,
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "false_positive_rate": false_positive_rate,
    }
    args.output.with_suffix(".json").write_text(
        json.dumps(metrics, indent=2) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
