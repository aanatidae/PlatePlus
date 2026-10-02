# Synthetic plate-origin evaluation

This evaluation uses **32 explicitly labelled synthetic text cases** in `labels.csv`. `reference_origin` is the scenario label, not a verified registration record. `expected_decision` is the safe classifier outcome; a Malaysian or Singaporean scenario may expect `unknown` when the visible text overlaps both supported patterns. `case_type` separates supported, ambiguous, and unsupported cases. No image or OCR inference is run.

Run from `ml` with the existing environment:

```powershell
..\backend\.venv\Scripts\python.exe scripts\evaluate_plate_origin.py
```

The script validates fixture provenance and writes `results.json` with per-case decisions, a reference-origin confusion matrix, cross-country errors, and rejection counts. It reads only this CSV. The protected 44-crop OCR held-out manifest and image data are not inputs.

| Reference origin | Predicted Malaysian | Predicted Singaporean | Predicted unknown |
| --- | ---: | ---: | ---: |
| Malaysian | 9 | 0 | 3 |
| Singaporean | 0 | 8 | 4 |
| Unknown/unsupported | 0 | 0 | 8 |

Exact origin labels: **25/32 (78.1%)** on this intentionally constructed synthetic fixture. MY-to-SG and SG-to-MY confusions: **0** each. All **7/7 ambiguous** and **8/8 unsupported** cases were rejected as `unknown` with the expected reason. The seven known-origin abstentions are a deliberate consequence of rejecting overlapping plate shapes.

These counts measure the current deterministic text-pattern policy on selected examples. The fixture is small, synthetic, and enriched with ambiguous cases, so 78.1% is **not** real-world origin-classification accuracy. It says nothing about YOLO detection, PaddleOCR text reading, registration issuance, nationality, ownership, or check-letter validity. No Singaporean image set or human-verified origin labels have been evaluated. Keep these results separate from the held-out PaddleOCR 37/44 exact-match result and the development OCR 125/146 result.
