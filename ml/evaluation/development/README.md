# OCR Development Set

This directory is reserved for a separately labelled OCR **development** set.
It must never contain the 44 preserved held-out crops used for the reported
PaddleOCR 37/44 (84.1%) result.

`labels.csv` contains 150 deterministically selected candidate images: 138 from
the training split and 12 from the validation split after excluding all 44 paths
in `ml/datasets/car_plate_test_manifest.txt`. It is a review queue, **not** a
labelled development set yet.

For every retained sample, fill in `valid_plate_present`, `condition_labels`,
`verified_by`, and `verified_at`. Fill `verified_ground_truth_plate` whenever a
visible plate can be read with confidence. If a plate is present but unreadable,
leave its text blank and explain why in `verification_notes`; it remains valid
for detector false-negative analysis but is excluded from OCR exact-match scoring.
Use one or more semicolon-separated conditions: `clear`, `angled`, `low_light`,
`motion_blur`, `partial_obstruction`, `small_or_distant`,
`glare_or_overexposure`, or `unusual_plate_format`. Remove unsuitable samples
rather than guessing a label.

The evaluator accepts the earlier shorthand `glare_or_exposure` and reports it
as the canonical `glare_or_overexposure`; use the canonical spelling for all
new review entries.

Do not populate labels from a filename, YOLO annotation, or OCR output. A human
must verify every ground-truth plate. Raw webcam frames and crops remain
ephemeral and must not be placed here.

For OCR, run the local crop/OCR workflow against only the verified entries, then
run `scripts/evaluate_ocr_accuracy.py`; it reads `verified_ground_truth_plate`
and produces multi-condition exact-match results. For detection, write a
separate model-output CSV with `sample_id,plate_detected` and run
`scripts/evaluate_plate_detection.py`. The latter produces true/false positive
and negative outcomes plus precision, recall, and F1 only after human presence
labels exist.
