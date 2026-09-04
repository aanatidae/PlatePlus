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
