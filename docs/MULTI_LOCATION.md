# Multi-location monitoring

The normal simulated V3 network is **LDP, AKLEH, NPE, and Grand Saga**.
Simulator Toll Plaza is a fifth, separate local-ALPR location. Traffic, toll
rates, vehicles, wallets, and payments are simulated. The map is a stylized
regional schematic, not a GIS or navigation map.

| Code | Route label | Prototype coordinates | Base toll | Capacity/hour | Peak hours (Malaysia time) |
| --- | --- | --- | --- | --- | --- |
| LDP | LDP / E11 | 3.145200, 101.621700 | RM2.00 | 1,000 | 7, 8, 17, 18 |
| AKLEH | AKLEH | 3.160000, 101.735000 | RM2.40 | 1,200 | 7, 8, 17, 18 |
| NPE | NPE / E10 | 3.095000, 101.672000 | RM2.80 | 1,300 | 8, 9, 17, 18 |
| GRAND_SAGA | Grand Saga | 3.045000, 101.765000 | RM3.20 | 1,500 | 6, 7, 16, 17, 18 |

Coordinates, capacities, base tolls, speed bounds, and demand profiles are demo
configuration, not surveyed toll-plaza positions, official tariffs, or measured
traffic. Independent deterministic profiles calculate congestion percentage
before selecting a pricing band. The scheduler and presentation feed target only
operational normal locations. Simulator never receives generated traffic or speed.

## Monitoring and selection

All endpoints require administrator authentication. `GET /api/locations` lists
current locations and omits retired ones. `GET /api/locations/network/live` and
`GET /api/live/overview?scope=all_locations` exclude retired locations and their
activity from current network totals. `location_id` scopes monitoring to one
location; network congestion and speed are capacity weighted, and network toll is
the arithmetic mean of reporting locations. Persisted telemetry takes priority
over deterministic profile fallback. Normal activity uses the last hour;
Simulator activity uses its rolling 60-second window. Recent lists contain up to
12 records, and successful payments contribute to simulated revenue.

Overview opens in All Locations. Map markers and the keyboard-accessible selector
share persisted location context with Dynamic Pricing Management. A saved retired
selection falls back to All Locations. Prediction offers only the four normal
locations, runs browser-local five-minute frames for up to 12 hours, and never
changes live records or wallet balances. Simulator retains its Overview webcam
PiP and still-image upload, 10-crossing capacity, and 60-second congestion window.
Processed history persists and raw images remain ephemeral. Frontend monitoring
polls every five seconds, cancels obsolete requests, and uses a 15-second timeout.

## Upgrade and historical ownership

Migration `20261007_0014` follows `20261002_0013`. It renames the existing
Penchala/LDP code to `LDP`, retaining its ID, profile, configuration, and ownership.
It retires DUKE and KESAS, preserving their IDs, metadata, traffic, prices,
detections, transactions, and other history. AKLEH and Grand Saga receive new
stable IDs and independent histories. Old highway activity is never relabelled
as activity at a different highway. NPE and Simulator remain unchanged.

Retired metadata remains available through `GET /api/locations/{id}`. Historical
`/api/data/detections`, `/api/data/transactions`, and `/api/data/toll-prices` APIs
remain filterable by original `location_id`, dates, and supported status fields.
Retired locations have no live fallback telemetry and cannot receive generated
traffic or demo crossings. Pricing-policy edits leave their stored prices unchanged.

Run the existing `alembic upgrade head` and idempotent seed before using the new
network. Location configuration is migration-owned; repeat seeding does not reset
operator settings, history, or balances. Fresh and upgraded databases converge to
five current locations plus two retired historical entries.

Downgrade to `0013` removes the two new locations and restores legacy naming and
operational status. PostgreSQL RESTRICT foreign keys refuse that downgrade if
AKLEH or Grand Saga has acquired linked history; the migration transaction rolls
back without deleting or reassigning records. Preserve that history and remain at
V3, or explicitly plan a separate archival procedure before attempting rollback.

## Verification

PostgreSQL tests cover fresh/upgraded seed convergence, retained IDs and ownership,
downgrade/re-upgrade, populated rollback refusal, retired-history API access,
current aggregation, four-road scheduler generation, independent daily congestion
and speed profiles, useful pricing bands, and Simulator exclusion. Frontend tests
cover V3 routes and markers, Prediction selection and Malaysia-time rollover, and
existing navigation and presentation behavior.
