# OCR And Plate Processing

## Selected OCR Engine

The integrated prototype uses PaddleOCR on CPU with PaddlePaddle 3.2.x. It was
selected after reaching 37 exact matches out of 44 preserved held-out crops
(84.1%), compared with EasyOCR's 15/44 (34.1%) on the same evaluation protocol.
The recognizer uses uppercase-alphanumeric normalization suited to Malaysian
plates. PaddleOCR assets remain local and Git-ignored; its first use can download
models, so prepare them only with approval.

## Still-Image Flow

1. Run the one-class YOLO detector on an image.
2. Select the highest-confidence `car plate` result.
3. Expand the detected box by a five-percent margin and clamp it to image bounds.
4. Send the crop to EasyOCR.
5. Remove whitespace, punctuation, and casing differences from the OCR output.
6. Preserve raw OCR text, normalized text, detection confidence, and OCR confidence.
7. Permit downstream simulated charging only when both values meet configured thresholds and the normalized text matches an accepted Malaysian plate layout.

The detector threshold defaults to `0.50`; the OCR threshold defaults to `0.70`.
These are configuration defaults to tune with a curated OCR test set, not claims
of production-quality recognition.

## Malaysian Plate Validation and Correction Policy

Normalization uppercases text and retains only ASCII letters and digits. A
charge-eligible result must then match the common Malaysian layout of one to
three leading letters, one to four digits, and up to three optional trailing
letters. Plausibility is a safety gate; it does not claim to cover every special
registration format.

The recognizer may apply a narrowly constrained correction for common OCR pairs
(`0/O`, `1/I/L`, `2/Z`, `5/S`, `8/B`) only when exactly one valid layout results.
It retains the raw OCR text alongside the corrected normalized text. If two or
more layouts are possible, it makes no substitution and rejects the read safely.
Neither correction nor a confidence gate proves that a plate is correct.

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

The checked-in development-set protocol is in `ml/evaluation/development/`.
Its 150-candidate review manifest is sampled from non-held-out training and
validation images and deliberately leaves all human-verification fields blank.
It excludes the preserved 44-crop test manifest exactly. Add one or more
semicolon-separated condition labels—`clear`, `angled`, `low_light`,
`motion_blur`, `partial_obstruction`, `small_or_distant`,
`glare_or_overexposure`, and `unusual_plate_format`—after visual review.
`evaluate_ocr_accuracy.py` then emits a condition-by-condition exact-match
breakdown.

After a human completes the development manifest, evaluate detection separately
with a model-output CSV (`sample_id,plate_detected,detector_confidence,notes`):

```powershell
backend/.venv/Scripts/python.exe scripts/evaluate_plate_detection.py `
  --manifest ml/evaluation/development/labels.csv `
  --predictions ml/evaluation/development/detection_predictions.csv `
  --output ml/evaluation/results/development_detection
```

This creates per-sample true-positive, false-positive, true-negative, and
false-negative results only from the human-verified presence labels.

## Local Evaluation Commands

Generate local review crops and OCR candidates from the held-out set:

```powershell
backend/.venv/Scripts/python.exe scripts/generate_ocr_review_set.py `
  --images-dir ml/datasets/generated/car_plate_yolo/test/images `
  --model models/trained/car_plate_yolo_best.pt `
  --output-dir ml/evaluation/review
```

Enter visually verified text in `ml/evaluation/ocr_ground_truth_template.csv`, then
calculate exact-match accuracy and retain result rows for the capstone report:

```powershell
backend/.venv/Scripts/python.exe scripts/evaluate_ocr_accuracy.py `
  --ground-truth ml/evaluation/ocr_ground_truth_template.csv `
  --candidates ml/evaluation/review/ocr_candidates.csv `
  --output-dir ml/evaluation/results
```

## Held-Out Evaluation Result

The first OCR baseline was evaluated against 44 manually verified plate-text labels
from the held-out YOLO test split. The workflow used the trained `car plate` YOLO
model to generate each crop, then EasyOCR with the uppercase alphanumeric
allow-list. Both the OCR output and the ground truth were normalized before
comparison.

| Measure | Result |
| --- | --- |
| Evaluated images | 44 |
| Exact matches | 15 |
| Exact-match OCR accuracy | 34.1% |
| Failures | 29 |

This result does not meet the 80% prototype target. The dominant observed failure
modes are omitted prefix/suffix characters and confusion between visually similar
letters and digits. Detection confidence was generally high, so the immediate
improvement work should focus on crop preprocessing and plate-specific OCR
rather than detector retraining.

The verified label CSV and generated per-image results remain local evaluation
artifacts. The reusable commands above regenerate the candidates and metric.

## PaddleOCR Comparison

PaddleOCR was evaluated using the same 44 manually verified held-out images,
YOLO-generated crops, normalization policy, and exact-match metric as EasyOCR.

| Engine | Exact matches | Exact-match accuracy |
| --- | ---: | ---: |
| EasyOCR baseline | 15 / 44 | 34.1% |
| PaddleOCR | 37 / 44 | 84.1% |

PaddleOCR meets the 80% prototype target on this evaluated set and is the selected
engine for the next integration stage. Its remaining seven errors are partial reads
or visually similar character substitutions. Because this set was used to compare
engines, future preprocessing tuning must use a separate labeled development set;
keep this set unchanged for confirmation only.
