# Multi-location monitoring

PlatePlus retains its dark command-centre design and uses the four locations seeded by migration `20260904_0004`: Penchala, Sungai Besi, Ayer Keroh, and Lima Kedai. Operational values and all payments remain simulated. Map positions form a north-to-south schematic, not a geographic navigation map.

## Dashboard context

The top-bar selector defaults to All Locations and saves its value under `plateplus.location.v1` in browser local storage. Invalid/deleted location IDs fall back to All Locations. Selection is shared by Overview, Recognition, Dynamic Pricing, and AI Intelligence. Native select controls and keyboard-operable map buttons provide equivalent location selection.

Simulator has its own selector and local results. Its selected location supplies road capacity and base toll. Changing its location clears previous results; running it does not write live traffic, prices, detections, or transactions. Full simultaneous multi-location simulation and independent peak-hour profiles remain future improvements. Local webcam retains the default Penchala context, explicitly labelled in the top bar.

## Read-only monitoring API

All endpoints require administrator authentication.

| Request | Meaning |
| --- | --- |
| `GET /api/locations` | Seeded location metadata |
| `GET /api/live/overview?scope=all_locations` | Network monitoring, location states, and recent activity |
| `GET /api/live/overview?location_id=<uuid>` | One location's monitoring and recent activity |

The existing unscoped `/api/live/overview` remains a legacy compatibility endpoint; the dashboard uses an explicit scope. Unknown location IDs return 404. Monitoring requests never write records.

Activity metrics use a rolling last-hour window. Transaction count includes every outcome; revenue counts successful payments only. Recent lists contain up to 12 records. Network congestion and speed are weighted by road capacity, traffic flow is summed, and network toll is an arithmetic mean across locations with telemetry. The response reports the number of reporting locations so partial coverage is visible. Missing telemetry is represented as unavailable rather than zero traffic.

Telemetry uses the latest persisted simulation when available and a labelled time-profile fallback otherwise. Average speed is estimated. Camera and system states are synthetic values derived from location status. These are not physical device-health measurements. Locations without history still share the baseline time pattern; richer independent profiles remain future work.

The frontend polls every 30 seconds with a 15-second request timeout, cancels old scope requests, and shows stale/error states without relabelling another location's data. Measurements older than two minutes are marked stale; the last successful refresh and measurement time are shown separately.

## History and image recognition

The `/api/data/detections`, `/api/data/transactions`, and `/api/data/toll-prices` list endpoints accept `location_id`, `start_at`, and `end_at`. Detection history also accepts `plate`, `registration`, and `detection_status`; transactions accept `transaction_status` and `minimum_amount`; prices accept `congestion_category`. Filters are applied before pagination. The UI displays the latest 50 matching records and converts selected dates to explicit Malaysia-time boundaries.

Local `POST /api/webcam/images?location_id=<uuid>` passes location ownership through the detection and simulated payment workflow. The UI requires a specific location before upload. Omitting the parameter retains the API's legacy default-location behavior. No image bytes are retained and no cloud inference is introduced.

## Verification

On 2026-09-05, the production frontend build, 8 frontend tests, and all 52 backend tests passed, including PostgreSQL integration tests. Tests cover location ownership, network aggregation, filtering, empty/unavailable telemetry, and read-only monitoring. Development PostgreSQL was at migration head; Docker's development/test containers were healthy.

Manual browser verification used disposable synthetic fixtures and covered desktop/mobile layout, keyboard marker selection, persistent location context, history filtering, Simulator isolation, and stale/API-outage states. These checks do not constitute an automated browser suite or a full accessibility audit. Physical webcam inference was not run. No deployment was performed.
