"""Validate and prepare a one-class YOLO dataset for Malaysian car plates.

The source dataset contains two classes:

- 0: car
- 1: car plate

For the first prototype, only `car plate` should be trained. This script filters class 1,
remaps it to class 0, and converts polygon/segmentation annotations to detection boxes when
writing the prepared dataset.
"""

from __future__ import annotations

import argparse
import json
import random
import shutil
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable

SOURCE_PLATE_CLASS_ID = 1
TARGET_PLATE_CLASS_ID = 0
IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}


@dataclass(frozen=True)
class SplitSummary:
    split: str
    images: int
    labels: int
    missing_labels: list[str]
    missing_images: list[str]
    plate_objects: int
    car_objects: int
    box_annotations: int
    polygon_annotations: int
    invalid_lines: list[str]


@dataclass(frozen=True)
class DatasetSummary:
    source_root: str
    splits: list[SplitSummary]
    reserved_test_images: list[str]
    recommendation: str


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--source-root",
        type=Path,
        default=Path("Malaysian Car Plate Dataset"),
        help="Original YOLO dataset root.",
    )
    parser.add_argument(
        "--output-root",
        type=Path,
        default=Path("ml/datasets/generated/car_plate_yolo"),
        help="Generated one-class YOLO dataset root used with ml/configs/car_plate_data.yaml.",
    )
    parser.add_argument(
        "--test-ratio",
        type=float,
        default=0.5,
        help="Fraction of original validation images reserved as test images.",
    )
    parser.add_argument("--seed", type=int, default=20260831, help="Deterministic split seed.")
    parser.add_argument(
        "--report-json",
        type=Path,
        default=Path("docs/dataset_yolo_report.json"),
        help="Path for the validation report JSON.",
    )
    parser.add_argument(
        "--test-manifest",
        type=Path,
        default=Path("ml/datasets/car_plate_test_manifest.txt"),
        help="Path for the reserved test image manifest.",
    )
    parser.add_argument(
        "--write-prepared-dataset",
        action="store_true",
        help="Copy images and write filtered/remapped detection labels.",
    )
    return parser.parse_args()


def image_files(split_root: Path) -> list[Path]:
    images_dir = split_root / "images"
    if not images_dir.exists():
        return []
    return sorted(path for path in images_dir.iterdir() if path.suffix.lower() in IMAGE_SUFFIXES)


def label_files(split_root: Path) -> list[Path]:
    labels_dir = split_root / "labels"
    if not labels_dir.exists():
        return []
    return sorted(path for path in labels_dir.glob("*.txt"))


def label_path_for_image(source_root: Path, split: str, image_path: Path) -> Path:
    return source_root / split / "labels" / f"{image_path.stem}.txt"


def image_path_for_label(source_root: Path, split: str, label_path: Path) -> Path | None:
    images_dir = source_root / split / "images"
    for suffix in IMAGE_SUFFIXES:
        candidate = images_dir / f"{label_path.stem}{suffix}"
        if candidate.exists():
            return candidate
    return None


def parse_yolo_line(line: str) -> tuple[int, list[float]]:
    parts = line.split()
    if len(parts) < 5:
        raise ValueError("expected at least 5 fields")
    class_id = int(parts[0])
    values = [float(part) for part in parts[1:]]
    if len(values) == 4:
        return class_id, values
    if len(values) >= 6 and len(values) % 2 == 0:
        return class_id, values
    raise ValueError("expected xywh box or even-length polygon coordinates")


def polygon_to_box(values: list[float]) -> list[float]:
    xs = values[0::2]
    ys = values[1::2]
    x_min = max(0.0, min(xs))
    y_min = max(0.0, min(ys))
    x_max = min(1.0, max(xs))
    y_max = min(1.0, max(ys))
    width = max(0.0, x_max - x_min)
    height = max(0.0, y_max - y_min)
    return [x_min + width / 2, y_min + height / 2, width, height]


def normalize_plate_annotation(values: list[float]) -> list[float]:
    if len(values) == 4:
        return values
    return polygon_to_box(values)


def iter_label_records(label_path: Path) -> Iterable[tuple[int, list[float], bool]]:
    for raw_line in label_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line:
            continue
        class_id, values = parse_yolo_line(line)
        yield class_id, values, len(values) > 4


def summarize_split(source_root: Path, split: str) -> SplitSummary:
    split_root = source_root / split
    images = image_files(split_root)
    labels = label_files(split_root)
    image_stems = {path.stem for path in images}
    label_stems = {path.stem for path in labels}

    missing_labels = sorted(stem for stem in image_stems - label_stems)
    missing_images = sorted(stem for stem in label_stems - image_stems)
    plate_objects = 0
    car_objects = 0
    box_annotations = 0
    polygon_annotations = 0
    invalid_lines: list[str] = []

    for label_path in labels:
        for index, raw_line in enumerate(label_path.read_text(encoding="utf-8").splitlines(), start=1):
            line = raw_line.strip()
            if not line:
                continue
            try:
                class_id, values = parse_yolo_line(line)
            except Exception as exc:  # noqa: BLE001 - report all malformed labels with context.
                invalid_lines.append(f"{label_path}:{index}: {exc}")
                continue
            if class_id == SOURCE_PLATE_CLASS_ID:
                plate_objects += 1
            elif class_id == 0:
                car_objects += 1
            if len(values) == 4:
                box_annotations += 1
            else:
                polygon_annotations += 1

    return SplitSummary(
        split=split,
        images=len(images),
        labels=len(labels),
        missing_labels=missing_labels,
        missing_images=missing_images,
        plate_objects=plate_objects,
        car_objects=car_objects,
        box_annotations=box_annotations,
        polygon_annotations=polygon_annotations,
        invalid_lines=invalid_lines,
    )


def reserve_test_images(source_root: Path, test_ratio: float, seed: int) -> list[Path]:
    validation_images = image_files(source_root / "val")
    rng = random.Random(seed)
    shuffled = validation_images[:]
    rng.shuffle(shuffled)
    test_count = max(1, round(len(shuffled) * test_ratio)) if shuffled else 0
    return sorted(shuffled[:test_count])


def destination_split(original_split: str, image_path: Path, reserved_test: set[str]) -> str:
    if original_split == "train":
        return "train"
    if image_path.name in reserved_test:
        return "test"
    return "val"


def write_prepared_dataset(source_root: Path, output_root: Path, reserved_test: set[str]) -> None:
    if output_root.exists():
        shutil.rmtree(output_root)

    for split in ("train", "val", "test"):
        (output_root / split / "images").mkdir(parents=True, exist_ok=True)
        (output_root / split / "labels").mkdir(parents=True, exist_ok=True)

    for original_split in ("train", "val"):
        for image_path in image_files(source_root / original_split):
            label_path = label_path_for_image(source_root, original_split, image_path)
            if not label_path.exists():
                continue

            prepared_lines: list[str] = []
            for class_id, values, _is_polygon in iter_label_records(label_path):
                if class_id != SOURCE_PLATE_CLASS_ID:
                    continue
                box = normalize_plate_annotation(values)
                if box[2] <= 0 or box[3] <= 0:
                    continue
                prepared_lines.append(
                    f"{TARGET_PLATE_CLASS_ID} " + " ".join(f"{value:.8f}" for value in box)
                )

            if not prepared_lines:
                continue

            split = destination_split(original_split, image_path, reserved_test)
            shutil.copy2(image_path, output_root / split / "images" / image_path.name)
            (output_root / split / "labels" / f"{image_path.stem}.txt").write_text(
                "\n".join(prepared_lines) + "\n",
                encoding="utf-8",
            )


def main() -> None:
    args = parse_args()
    source_root = args.source_root
    reserved_test_paths = reserve_test_images(source_root, args.test_ratio, args.seed)
    reserved_test_names = {path.name for path in reserved_test_paths}

    summary = DatasetSummary(
        source_root=str(source_root),
        splits=[summarize_split(source_root, split) for split in ("train", "val")],
        reserved_test_images=[str(path.relative_to(source_root)) for path in reserved_test_paths],
        recommendation=(
            "Use YOLO detection for the first prototype. The source includes polygon labels, "
            "but the product needs bounding boxes for plate cropping; convert plate polygons to "
            "boxes, filter out class 0 cars, and remap source class 1 to target class 0."
        ),
    )

    args.report_json.parent.mkdir(parents=True, exist_ok=True)
    args.report_json.write_text(json.dumps(asdict(summary), indent=2), encoding="utf-8")

    args.test_manifest.parent.mkdir(parents=True, exist_ok=True)
    args.test_manifest.write_text(
        "\n".join(summary.reserved_test_images) + "\n",
        encoding="utf-8",
    )

    if args.write_prepared_dataset:
        write_prepared_dataset(source_root, args.output_root, reserved_test_names)

    print(json.dumps(asdict(summary), indent=2))


if __name__ == "__main__":
    main()