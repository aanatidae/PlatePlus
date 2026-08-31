"""Generate a visual review set for manually verified OCR ground truth."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path
from typing import Protocol

import cv2
from alpr.ocr.easyocr_recognizer import EasyOcrPlateRecognizer
from alpr.ocr.paddleocr_recognizer import PaddleOcrPlateRecognizer
from alpr.plate.crop import extract_plate_crop
from alpr.types import BoundingBox, OcrResult, PlateDetection
from ultralytics import YOLO


class PlateRecognizer(Protocol):
    def recognize(self, crop: object) -> OcrResult: ...


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--images-dir", type=Path, required=True)
    parser.add_argument("--model", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--confidence", type=float, default=0.50)
    parser.add_argument("--ocr-engine", choices=("easyocr", "paddleocr"), default="easyocr")
    parser.add_argument("--ocr-model-storage", type=Path)
    parser.add_argument("--limit", type=int)
    return parser.parse_args()


def make_contact_sheet(rows: list[dict[str, str]], output_path: Path) -> None:
    tile_width, tile_height, columns = 640, 220, 2
    tiles: list[object] = []
    for row in rows:
        crop = cv2.imread(row["crop_path"])
        if crop is None:
            continue
        scale = min(tile_width / crop.shape[1], (tile_height - 44) / crop.shape[0])
        resized = cv2.resize(crop, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)
        tile = cv2.copyMakeBorder(
            resized,
            26,
            tile_height - 26 - resized.shape[0],
            0,
            tile_width - resized.shape[1],
            cv2.BORDER_CONSTANT,
            value=(255, 255, 255),
        )
        cv2.putText(
            tile,
            f"{row['id']}: OCR {row['ocr_normalized_text'] or '-'} ({float(row['ocr_confidence']):.2f})",
            (8, 18),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.55,
            (0, 0, 0),
            1,
            cv2.LINE_AA,
        )
        tiles.append(tile)

    if not tiles:
        raise RuntimeError("no detected crops were available for the contact sheet")
    blank = 255 * cv2.UMat(tile_height, tile_width, cv2.CV_8UC3).get()
    while len(tiles) % columns:
        tiles.append(blank.copy())
    rows_of_tiles = [cv2.hconcat(tiles[index : index + columns]) for index in range(0, len(tiles), columns)]
    cv2.imwrite(str(output_path), cv2.vconcat(rows_of_tiles))


def create_recognizer(engine: str, model_storage: Path | None) -> PlateRecognizer:
    if engine == "easyocr":
        return EasyOcrPlateRecognizer(model_storage or Path("models/ocr"))
    return PaddleOcrPlateRecognizer(model_storage or Path("models/paddleocr"))


def main() -> None:
    args = parse_args()
    image_paths = sorted(args.images_dir.glob("*.jpg"))
    if args.limit:
        image_paths = image_paths[: args.limit]
    if not image_paths:
        raise ValueError("no JPG images found")

    args.output_dir.mkdir(parents=True, exist_ok=True)
    crops_dir = args.output_dir / "crops"
    crops_dir.mkdir(exist_ok=True)
    model = YOLO(args.model)
    recognizer = create_recognizer(args.ocr_engine, args.ocr_model_storage)
    results = model([str(path) for path in image_paths], conf=args.confidence, verbose=False)
    rows: list[dict[str, str]] = []

    for index, (image_path, result) in enumerate(zip(image_paths, results, strict=True), start=1):
        if result.boxes is None or len(result.boxes) == 0:
            continue
        image = cv2.imread(str(image_path))
        values = result.boxes.xyxy[0].tolist()
        detection = PlateDetection(
            BoundingBox(*(round(value) for value in values)), float(result.boxes.conf[0])
        )
        crop = extract_plate_crop(image, detection)
        crop_path = crops_dir / f"{index:02d}_{image_path.stem}.jpg"
        cv2.imwrite(str(crop_path), crop.image)
        ocr = recognizer.recognize(crop.image)
        rows.append(
            {
                "id": str(index),
                "image_path": str(image_path),
                "crop_path": str(crop_path),
                "detection_confidence": f"{crop.detection_confidence:.6f}",
                "ocr_raw_text": ocr.raw_text,
                "ocr_normalized_text": ocr.normalized_text,
                "ocr_confidence": f"{ocr.confidence:.6f}",
            }
        )

    csv_path = args.output_dir / "ocr_candidates.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    make_contact_sheet(rows, args.output_dir / "ocr_review_sheet.jpg")
    print(f"Wrote {len(rows)} detected plate crops to {args.output_dir}")


if __name__ == "__main__":
    main()
