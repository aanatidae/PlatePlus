# OCR And Plate Processing

## Selected OCR Engine

The first prototype uses EasyOCR. It is a Python-native OCR library that can run
on the existing CPU PyTorch environment and does not require the separate
operating-system installation that Tesseract needs. The recognizer is configured
for English characters and an uppercase alphanumeric allow-list, which matches
Malaysian plate recognition.

EasyOCR remains an optional ML dependency. Installing it will also cause EasyOCR
to download its recognition model the first time it is initialized. Keep model
files local and ignored by Git.

## Still-Image Flow

1. Run the one-class YOLO detector on an image.
2. Select the highest-confidence `car plate` result.
3. Expand the detected box by a five-percent margin and clamp it to image bounds.
4. Send the crop to EasyOCR.
5. Remove whitespace, punctuation, and casing differences from the OCR output.
6. Preserve raw OCR text, normalized text, detection confidence, and OCR confidence.
7. Permit downstream simulated charging only when both values meet configured thresholds.

The detector threshold defaults to `0.50`; the OCR threshold defaults to `0.70`.
These are configuration defaults to tune with a curated OCR test set, not claims
of production-quality recognition.

## Normalization Policy

Normalization is intentionally conservative: it uppercases text and retains only
ASCII letters and digits. It does not auto-substitute ambiguous pairs such as
`O`/`0`, `I`/`1`, or `S`/`5`, since an incorrect substitution could match the
wrong synthetic vehicle. A later lookup stage can use candidate-aware correction
only when it is auditable and still satisfies the confidence gate.

## OCR Evaluation Ground Truth

The YOLO dataset filenames do not reliably contain plate strings, so evaluation
must use a manually curated CSV. Use one row per held-out image/crop:

```csv
image_path,ground_truth_plate
samples/plate_001.jpg,BKV1234
```

Split this curated data into development and final held-out sets. Compare
normalized OCR output against normalized ground truth, report exact-match
accuracy, and retain failure samples for the capstone report.
