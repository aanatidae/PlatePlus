# Capstone Demo Flow

This is a controlled demonstration of a simulated prototype. Do not present any traffic condition, account, toll price, transaction, or vehicle identity as real.

## Before the demo

1. Confirm the required local model exists at `models/trained/car_plate_yolo_best.pt` if demonstrating ALPR inference.
2. Copy `.env.example` to `.env` if needed, and replace the default demo password and token secret.
3. Start Docker PostgreSQL, apply migrations, and seed synthetic data as described in [SETUP.md](SETUP.md).
4. Start the FastAPI backend and the React frontend. Use the health endpoint before opening the dashboard.
5. Keep a known still image available only if demonstrating local inference. Do not upload personal or real vehicle images.

## Suggested presentation

1. Sign in with the demo administrator from the local `.env`. Do not display its password in slides or recordings.
2. In Overview, inspect All Locations and the LDP/AKLEH/NPE/Grand Saga map. Select one location to show its canonical congestion, dynamic toll, activity, and `Why this price?` explanation. All operational data is simulated.
3. Select Simulator Toll Plaza in Overview. Its Open Camera and Upload Plate Image controls stay here; there is no standalone recognition or simulator page. Physical camera verification remains separately deferred unless explicitly requested.
4. Using a prepared fictional plate image whose OCR matches a synthetic registered vehicle, demonstrate a Malaysian result with zero foreign charge. Use a prepared Singaporean example where available to show the separately stored dynamic toll, simulated foreign charge, and final total. Do not imply these pattern labels verify legal nationality or registration. See the seed examples and [foreign charge documentation](FOREIGN_VEHICLE_CHARGE.md).
5. Show that insufficient funds produce an attempted total with no debit, and unknown/ambiguous patterns fail safely. Repeated plates share a cooldown across camera and upload; replaying an event key returns its existing result without another deduction or traffic/price record.
6. Observe Simulator congestion expire at 60 seconds while processed history remains stored. Its average speed is unavailable. Price safeguards can hold a band even when congestion changes; the explanation displays the applied band.
7. Open Dynamic Pricing Management to show the four location-relative congestion multipliers and safeguards. Preview the current saved policy. Expand Recorded congestion, toll history and policy audit to inspect recorded Malaysia-time data and the location/date filters. Congestion tolls exclude transaction-only foreign charges.
8. Open Prediction to compare current and browser-local future traffic/toll values for the four normal locations. The forecast does not mutate live history, wallets, or the demo feed and excludes Simulator.
9. Open Model Performance from the top bar. Distinguish the user-reported 93.1% detector figure, held-out OCR 37/44 (84.1%), development-only evidence, and synthetic-text-only origin fixture 25/32 (78.1%). Unsupported detector metrics remain unavailable. Close with Escape or the close button.

Automated endpoint regressions use controlled inference output; they do not establish real Singaporean optical recognition accuracy or replace a physical camera check. The administrator navigation remains exactly three pages. See [V3 presentation verification](V3_SIMULATOR_PRICING_NAVIGATION.md).

Prepared SG synthetic seed examples are `GBC6427R` (initial RM75.00), `YN4821R`
(initial RM8.00, insufficient for seeded RM20 foreign charge) and `XD7316E`
(initial RM45.00). Use current balances and configured charge when explaining a
demo; repeated seed does not restore spent wallets. Generated feed vehicles remain
Malaysian-style; the optical SG example must be prepared separately. See
[seed details](SETUP.md) and [API components](API.md).

## Presentation accessibility

Use the top-bar Toll location selector as a keyboard alternative to the schematic
map. Enter opens it, arrows/Home/End move between options, Enter selects, and Escape
closes. Marker labels name their location and congestion state in text. Camera and
upload results show recognition messages, origin and successful/attempted payment
totals separately. The camera panel is height-bounded and keyboard-scrollable;
at shorter resolutions, focus it and scroll to see the complete charge breakdown.
Model Performance supports Escape and focus return, while reduced-motion settings
disable presentation animations. Browser fixture checks at six viewport sizes are
recorded in [W/X verification](V3_ACCESSIBILITY_DOCUMENTATION.md).

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
