"""Derive per-sample detector outcomes from an ALPR candidate CSV."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--candidates", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    with args.manifest.open(newline="", encoding="utf-8") as handle:
        manifest = list(csv.DictReader(handle))
    with args.candidates.open(newline="", encoding="utf-8") as handle:
        candidates = list(csv.DictReader(handle))
    confidence_by_path = {
        Path(row["image_path"]).resolve(): row["detection_confidence"] for row in candidates
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle, fieldnames=("sample_id", "plate_detected", "detector_confidence", "notes")
        )
        writer.writeheader()
        for sample in manifest:
            confidence = confidence_by_path.get(Path(sample["image_path"]).resolve())
            writer.writerow(
                {
                    "sample_id": sample["sample_id"],
                    "plate_detected": str(confidence is not None).lower(),
                    "detector_confidence": confidence or "",
                    "notes": "Derived from the reviewed-manifest candidate run.",
                }
            )


if __name__ == "__main__":
    main()
