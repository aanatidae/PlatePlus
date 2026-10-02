# ML Pipeline

Machine learning and OCR workspace for Malaysian license plate recognition.

The V3 ALPR path also has a conservative Malaysian/Singaporean pattern-origin stage. Its supported shapes, overlap behavior, and limits are documented in `../docs/PLATE_ORIGIN.md`.

The first prototype should process still images, detect the `car plate` class only, crop the plate, run OCR, and return normalized plate text with confidence values.
