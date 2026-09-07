"""Create an unlabelled, deterministic ALPR development-set review manifest.

The resulting CSV intentionally leaves every human-verification field blank.
It excludes every path in the preserved held-out manifest and never copies,
renames, or modifies dataset images.
"""

from __future__ import annotations

import argparse
import csv
import random
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset-root", type=Path, required=True)
    parser.add_argument("--held-out-manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--limit", type=int, default=150)
    parser.add_argument("--seed", type=int, default=20260907)
    return parser.parse_args()


def normalized_path(value: str | Path) -> str:
    return str(value).replace("\\", "/").lower()


def main() -> None:
    args = parse_args()
    if args.limit <= 0:
        raise ValueError("limit must be positive")
    held_out = {
        normalized_path(line.strip())
        for line in args.held_out_manifest.read_text(encoding="utf-8").splitlines()
        if line.strip()
    }
    candidates: list[tuple[str, Path]] = []
    for split in ("train", "val"):
        image_dir = args.dataset_root / split / "images"
        for image_path in sorted(image_dir.glob("*.jpg")):
            relative = Path(split) / "images" / image_path.name
            if normalized_path(relative) not in held_out:
                candidates.append((split, image_path))
    if len(candidates) < args.limit:
        raise ValueError(
            f"Only {len(candidates)} non-held-out images are available; requested {args.limit}."
        )

    selected = random.Random(args.seed).sample(candidates, args.limit)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=(
                "sample_id",
                "image_path",
                "source_split",
                "detector_annotation_path",
                "verified_ground_truth_plate",
                "condition_labels",
                "valid_plate_present",
                "verification_notes",
                "verified_by",
                "verified_at",
                "review_status",
                "ocr_scorable",
                "detection_evaluation_role",
            ),
        )
        writer.writeheader()
        for index, (split, image_path) in enumerate(sorted(selected), start=1):
            annotation = args.dataset_root / split / "labels" / f"{image_path.stem}.txt"
            writer.writerow(
                {
                    "sample_id": f"DEV-{index:03d}",
                    "image_path": image_path.resolve(),
                    "source_split": split,
                    "detector_annotation_path": annotation.resolve(),
                    "verified_ground_truth_plate": "",
                    "condition_labels": "",
                    "valid_plate_present": "",
                    "verification_notes": "",
                    "verified_by": "",
                    "verified_at": "",
                    "review_status": "",
                    "ocr_scorable": "",
                    "detection_evaluation_role": "",
                }
            )
    print(f"Wrote {args.limit} unverified, non-held-out candidates to {args.output}")


if __name__ == "__main__":
    main()
