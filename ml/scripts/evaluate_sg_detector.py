"""Evaluate unchanged local plate weights on a provided YOLO test/valid split.

No training, OCR, origin inference, model download, or operational writes.
ZIP inputs are inspected safely and only the selected split is extracted.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath
from unittest.mock import patch
from zipfile import ZipFile

import numpy as np
import yaml

IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp"}


def digest(path: Path) -> str:
    with path.open("rb") as file:
        return hashlib.file_digest(file, "sha256").hexdigest()


def safe_member(name: str) -> PurePosixPath:
    path = PurePosixPath(name)
    if path.is_absolute() or ".." in path.parts or "\\" in name or ":" in name:
        raise ValueError(f"Unsafe ZIP member: {name}")
    return path


def prepare_dataset(source: Path, output: Path) -> tuple[Path, str, dict]:
    if source.is_dir():
        split = next(
            (s for s in ["test", "valid", "val"] if (source / s / "images").is_dir()), None
        )
        if split is None:
            raise ValueError(
                "No provided test/valid split. Supply a documented deterministic evaluation subset."
            )
        metadata = yaml.safe_load((source / "data.yaml").read_text())
        return source, split, {"class_names": metadata["names"], "source": source.name}
    with ZipFile(source) as archive:
        entries = {}
        for info in archive.infolist():
            safe_member(info.filename)
            if (info.external_attr >> 16) & 0o170000 == 0o120000:
                raise ValueError("ZIP symlinks are not accepted")
            if not info.is_dir():
                if info.filename in entries and archive.read(
                    entries[info.filename]
                ) != archive.read(info):
                    raise ValueError("Conflicting duplicate archive entry")
                entries[info.filename] = info
        split_counts = {
            s: sum(
                n.startswith(s + "/images/") and Path(n).suffix.lower() in IMAGE_SUFFIXES
                for n in entries
            )
            for s in ["train", "valid", "val", "test"]
        }
        split = next((s for s in ["test", "valid", "val"] if split_counts[s]), None)
        if split is None:
            raise ValueError(
                "Archive has no provided test/valid split; never silently evaluate training images."
            )
        metadata = yaml.safe_load(archive.read(entries["data.yaml"]))
        if metadata["nc"] != 1:
            raise ValueError("Evaluation requires a documented one-plate-class mapping")
        directory = output / "dataset"
        for name, info in entries.items():
            if name.startswith((split + "/images/", split + "/labels/")):
                target = directory.joinpath(*safe_member(name).parts)
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(archive.read(info))
        return (
            directory,
            split,
            {
                "source": source.name,
                "archive_sha256": digest(source),
                "class_names": metadata["names"],
                "split_image_counts": split_counts,
                "archive_unchanged": True,
            },
        )


def read_labels(path: Path, width: int, height: int) -> np.ndarray:
    boxes = []
    for line in path.read_text().splitlines():
        if not line.strip():
            continue
        values = [float(v) for v in line.split()]
        if values[0] != 0 or not all(0 <= v <= 1 for v in values[1:]):
            raise ValueError(f"Unsupported detection annotation: {path.name}")
        if len(values) == 5:
            _, x, y, w, h = values
        elif len(values) >= 7 and len(values) % 2 == 1:
            # YOLO polygons become enclosing boxes for localisation-only evaluation.
            points = np.asarray(values[1:]).reshape(-1, 2)
            left, top = points.min(axis=0)
            right, bottom = points.max(axis=0)
            x, y, w, h = (left + right) / 2, (top + bottom) / 2, right - left, bottom - top
        else:
            raise ValueError(f"Unsupported detection annotation: {path.name}")
        boxes.append(
            [(x - w / 2) * width, (y - h / 2) * height, (x + w / 2) * width, (y + h / 2) * height]
        )
    return np.asarray(boxes, dtype=float).reshape(-1, 4)


def matched_plates(truth: np.ndarray, predictions: np.ndarray, threshold: float = 0.5) -> int:
    """Greedy descending-IoU, one-to-one matching; predictions cannot double count a label."""
    candidates = []
    for i, gt in enumerate(truth):
        for j, pred in enumerate(predictions):
            intersection = np.maximum(
                0, np.minimum(gt[2:], pred[2:]) - np.maximum(gt[:2], pred[:2])
            ).prod()
            union = (
                np.maximum(0, gt[2:] - gt[:2]).prod()
                + np.maximum(0, pred[2:] - pred[:2]).prod()
                - intersection
            )
            iou = intersection / union if union > 0 else 0
            if iou >= threshold:
                candidates.append((iou, i, j))
    used_truth, used_predictions = set(), set()
    for _, i, j in sorted(candidates, reverse=True):
        if i not in used_truth and j not in used_predictions:
            used_truth.add(i)
            used_predictions.add(j)
    return len(used_truth)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--model", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=Path(".plateplus-eval/sg-license-plates"))
    parser.add_argument("--confidence", type=float, default=0.5)
    args = parser.parse_args()
    if not args.model.is_file():
        raise ValueError("Local trained weights are required; never download a replacement model")
    root, split, provenance = prepare_dataset(args.dataset.resolve(), args.output.resolve())
    images = sorted(
        p for p in (root / split / "images").iterdir() if p.suffix.lower() in IMAGE_SUFFIXES
    )
    if not images:
        raise ValueError("No evaluation images")
    from PIL import Image
    from ultralytics import YOLO, __version__

    model = YOLO(str(args.model.resolve()))
    if len(model.names) != 1:
        raise ValueError("PlatePlus detector must remain one-class")
    labels, manifest = {}, []
    prepared = args.output.resolve() / "prepared"
    converted_polygons = 0
    for path in images:
        with Image.open(path) as image:
            width, height = image.size
        label_path = root / split / "labels" / (path.stem + ".txt")
        labels[path.name] = read_labels(label_path, width, height)
        converted_polygons += sum(
            len(line.split()) > 5 for line in label_path.read_text().splitlines() if line.strip()
        )
        image_target = prepared / split / "images" / path.name
        image_target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(path, image_target)
        label_target = prepared / split / "labels" / label_path.name
        label_target.parent.mkdir(parents=True, exist_ok=True)
        rows = []
        for left, top, right, bottom in labels[path.name]:
            rows.append(
                f"0 {(left + right) / 2 / width:.12f} {(top + bottom) / 2 / height:.12f} {(right - left) / width:.12f} {(bottom - top) / height:.12f}"
            )
        label_target.write_text("\n".join(rows), encoding="utf8")
        manifest.append(
            {"image": path.name, "sha256": digest(path), "plates": len(labels[path.name])}
        )
    evaluated = len(images)
    plates = sum(len(value) for value in labels.values())
    negatives = sum(len(value) == 0 for value in labels.values())
    config = args.output.resolve() / "evaluation.yaml"
    config.parent.mkdir(parents=True, exist_ok=True)
    config.write_text(
        yaml.safe_dump(
            {
                "path": str(prepared),
                # Required YAML key, intentionally unusable for accidental training.
                "train": "unused-training/images",
                "val": split + "/images",
                "test": split + "/images",
                "names": model.names,
            }
        ),
        encoding="utf8",
    )
    print(
        f"Evaluating provided {split} split: {evaluated} images, {plates} labelled plates, {negatives} annotation-negative images",
        flush=True,
    )
    # check_det_dataset looks up a plotting font even with plots=False. Disable it.
    with patch("ultralytics.data.utils.check_font", return_value=None):
        metrics = model.val(
            data=str(config),
            split="test" if split == "test" else "val",
            imgsz=640,
            conf=0.001,
            iou=0.7,
            device="cpu",
            batch=4,
            workers=0,
            plots=False,
            save=False,
            project=str(args.output.resolve()),
            name="validation",
            exist_ok=True,
            verbose=False,
        )
    tp = fp = correct_images = 0
    cases = []
    for result in model.predict(
        source=[str(p) for p in images],
        conf=args.confidence,
        iou=0.7,
        imgsz=640,
        device="cpu",
        stream=True,
        verbose=False,
    ):
        truth = labels[Path(result.path).name]
        predictions = result.boxes.xyxy.cpu().numpy()
        matched = matched_plates(truth, predictions)
        tp += matched
        fp += len(predictions) - matched
        correct_images += int(matched > 0)
        cases.append(
            {
                "image": Path(result.path).name,
                "labelled": len(truth),
                "matched": matched,
                "unmatched_predictions": len(predictions) - matched,
            }
        )
    report = {
        "verified": True,
        "evaluated_at": datetime.now(UTC).isoformat(),
        "dataset": provenance,
        "split": split,
        "images": evaluated,
        "labelled_plates": plates,
        "annotation_negative_images": negatives,
        "polygon_annotations_converted_to_boxes": converted_polygons,
        "model_sha256": digest(args.model),
        "model_name": args.model.name,
        "fine_tuned_on_singaporean": False,
        "ultralytics_version": __version__,
        "class_mapping": {
            "dataset_class_0": provenance["class_names"],
            "model_class_0": model.names[0],
        },
        "parameters": {
            "imgsz": 640,
            "ap_confidence_floor": 0.001,
            "nms_iou": 0.7,
            "operational_confidence": args.confidence,
            "matching_iou": 0.5,
        },
        "standard_metrics": {
            "precision": float(metrics.box.mp),
            "recall": float(metrics.box.mr),
            "map50": float(metrics.box.map50),
            "map50_95": float(metrics.box.map),
            "precision_recall_definition": "Ultralytics precision/recall at maximum mean-F1 confidence on this split; not the runtime confidence gate.",
        },
        "operational_metrics": {
            "true_positive_plates": tp,
            "false_negative_plates": plates - tp,
            "unmatched_predictions": fp,
            "recall": tp / plates if plates else None,
            "precision": tp / (tp + fp) if tp + fp else None,
            "images_with_correct_detection": correct_images,
            "plate_present_images": evaluated - negatives,
            "image_hit_rate": correct_images / (evaluated - negatives)
            if evaluated - negatives
            else None,
            "definition": "One-to-one box matches at IoU >= 0.50 and confidence >= configured runtime threshold.",
        },
        "false_positive_rate": None,
        "negative_note": "Annotation-negative images are counted, but no human-verified representative negative set is supplied; no general false-positive rate or accuracy is claimed.",
        "cases": cases,
        "manifest": manifest,
    }
    (args.output / "results.json").write_text(json.dumps(report, indent=2), encoding="utf8")
    print(
        json.dumps(
            {
                k: report[k]
                for k in [
                    "split",
                    "images",
                    "labelled_plates",
                    "standard_metrics",
                    "operational_metrics",
                ]
            },
            indent=2,
        ),
        flush=True,
    )


if __name__ == "__main__":
    main()
