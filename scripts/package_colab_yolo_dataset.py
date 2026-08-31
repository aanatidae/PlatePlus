"""Package the generated one-class YOLO dataset for Google Colab upload."""

from __future__ import annotations

import argparse
import zipfile
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dataset-root",
        type=Path,
        default=Path("ml/datasets/generated/car_plate_yolo"),
        help="Prepared YOLO dataset root containing train, val, and test splits.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("ml/datasets/car_plate_yolo_colab.zip"),
        help="Output zip path to upload to Google Drive or Colab.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    dataset_root = args.dataset_root
    if not dataset_root.exists():
        raise SystemExit(
            f"Prepared dataset not found: {dataset_root}. "
            "Run scripts/prepare_car_plate_yolo_dataset.py --write-prepared-dataset first."
        )

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(args.output, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(dataset_root.rglob("*")):
            if path.is_file():
                archive.write(path, path.relative_to(dataset_root.parent))

    print(f"Wrote {args.output}")


if __name__ == "__main__":
    main()