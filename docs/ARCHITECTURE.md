# Architecture Notes

The application should be built as a modular prototype with clear boundaries between machine learning, OCR, business logic, persistence, and dashboard views.

## First Prototype Path

1. Accept a still image.
2. Detect the license plate region using a YOLO model trained for `car plate` only.
3. Crop the plate region.
4. Run OCR on the crop.
5. Normalize the recognized plate text.
6. Match against synthetic registered vehicles.
7. Apply confidence gates before any simulated toll transaction succeeds.

## Service Boundaries

- Detection service: YOLO inference and confidence reporting.
- Crop service: plate-region extraction from still images.
- OCR service: text recognition and OCR confidence reporting.
- Plate normalization service: Malaysian plate cleanup and matching format.
- Vehicle service: synthetic registered vehicle lookup.
- Pricing service: configurable congestion-to-price rules.
- Transaction service: simulated balance checks and toll transaction recording.
- Traffic service: simulated traffic records and congestion classification.
- Dashboard service: admin-only metrics and history views.

## Data Scope

All account, traffic, payment, and vehicle-owner data is synthetic. Do not connect to real payment providers, real toll infrastructure, real enforcement systems, or real owner databases.