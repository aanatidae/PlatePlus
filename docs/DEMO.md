# Capstone Demo Flow

This is a controlled demonstration of a simulated prototype. Do not present any traffic condition, account, toll price, transaction, or vehicle identity as real.

## Before the demo

1. Confirm the required local model exists at `models/trained/car_plate_yolo_best.pt` if demonstrating ALPR inference.
2. Copy `.env.example` to `.env` if needed, and replace the default demo password and token secret.
3. Start Docker PostgreSQL, apply migrations, and seed synthetic data as described in [SETUP.md](SETUP.md).
4. Start the FastAPI backend and the React frontend. Use the health endpoint before opening the dashboard.
5. Keep a known still image available only if demonstrating local inference. Do not upload personal or real vehicle images.

## Suggested presentation

1. Open the administrator sign-in page and state that access is restricted to administrators.
2. Sign in with the synthetic demo administrator from the local `.env` file. Do not display the password in slides or recordings.
3. On the Overview, point out the Malaysia-time traffic telemetry, congestion category, toll price, ALPR activity, and simulated financial metrics.
4. Open Dynamic Pricing to show the four configurable congestion bands: Low (RM2), Moderate (RM3), High (RM4), and Severe (RM5). Explain that changes are stored as simulated audit history.
5. Open the Simulator, choose a traffic scenario or custom vehicle rate, and run a manual simulation. Explain that the sandbox does not write live traffic, prices, or payment records.
6. Open Plate Recognition. On the cloud dashboard, explain that raw image upload is intentionally unavailable. On a local operator setup, optionally submit a pre-approved still image to demonstrate plate detection, OCR normalization, confidence gates, vehicle matching, and an idempotent simulated toll result.
7. Show recent detections and transactions, emphasizing that an unregistered plate, insufficient balance, low confidence, or a replayed idempotency key never produces an additional successful deduction.
8. Close with the measured prototype evidence: reported YOLO test accuracy of 93.1% and PaddleOCR exact-match accuracy of 84.1% (37/44 held-out crops). Refer to [TESTING_EVALUATION.md](TESTING_EVALUATION.md) for limits.

## Explicit exclusions to state

- No real payment, banking, Touch 'n Go, toll-road, enforcement, government, or vehicle-owner integration exists.
- Webcam frames and still images are processed locally and are not retained by default.
- The Vercel dashboard excludes local webcam/image inference; its Render API has no local model files.
- Physical browser-camera permission and live hardware inference remain separately deferred unless explicitly approved.
- Free Render deployments can sleep after inactivity, so allow time for the API to wake before the dashboard refreshes.

## Recovery notes

- If the dashboard cannot load data, check the backend `/health` endpoint and confirm the Vercel API base URL/CORS configuration.
- If a local ALPR request reports missing weights or OCR assets, do not download or reinstall during the presentation. Use dashboard telemetry and the documented evaluated flow instead.
- If Docker is unavailable, use the deployed read-only dashboard and explain that its data remains simulated; do not attempt a payment demonstration against an unavailable local database.
