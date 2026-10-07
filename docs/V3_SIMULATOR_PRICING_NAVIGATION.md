# V3 Simulator, pricing, and three-page presentation

Sections J, L, and N were completed on 2026-10-07. No schema migration or new
dependency is required beyond the existing `20261007_0014` network migration.

## Simulator crossing lifecycle

Both `/api/webcam/sessions/{id}/frames` and `/api/webcam/images?location_id=<Simulator UUID>`
use the local YOLO/PaddleOCR pipeline, confidence gates, origin classifier,
synthetic vehicle lookup, and simulated payment path. Inputs are ephemeral;
detection/payment metadata remains persisted.

Simulator congestion counts accepted or known-origin unknown-vehicle crossings
from local ALPR sources in **(now - 60 seconds, now]**, capped at 100% for a
10-crossing capacity. A crossing expires at exactly 60 seconds. Future-dated
records do not count. Malaysian and Singaporean accepted crossings use the same
window, including accepted recognitions whose payment failed for insufficient
funds. Unknown/ambiguous-origin rejection cannot create an active crossing or debit.
Average speed stays unavailable.

Expiry reads do not delete history or create traffic, prices, or transactions.
`measured_at` is the time the rolling state was calculated; `last_crossing_at`
retains the last historical accepted crossing. An idle, freshly calculated
Simulator state does not become stale merely because its last crossing is old.

The shared plate cooldown covers both webcam and uploads. A different input or
webcam session does not bypass it. A suppressed duplicate creates no new detection,
transaction, traffic, or price record. An idempotency-key replay returns the stored
payment components without a second deduction or a new traffic/price decision.

## Pricing and final charge

The dynamic toll uses the location base and congestion multiplier, subject to
minimum toll, maximum multiplier, minimum-change interval, and hysteresis. The
Simulator reports the actual applied band when a safeguard holds it, rather than
labelling a held price with the candidate congestion band.

`Why this price?` explains only the congestion toll. Origin never changes its band
or multiplier. Eligible Singaporean transactions add a separate configured simulated
foreign-vehicle charge. Overview, camera results, and upload results show the stored
dynamic toll, foreign charge, and final simulated total. Failed payments are labelled
as **attempted** totals; they do not imply a debit. Malaysian rows stay compact when
the foreign component is zero. Decimal strings are formatted as currency without
recalculating charge components in the browser.

## Information within three pages

Navigation remains Overview, Dynamic Pricing Management, and Prediction. Retired
routes redirect to Overview. Simulator camera/upload stays in Overview; Prediction
remains an isolated traffic/toll forecast and does not predict origin or foreign fees.

Overview recent detections label Malaysian, Singaporean, or unknown/unsupported
**patterns**, with the recorded reason available on the label. These labels do not
verify nationality, ownership, or issued registration. Transaction rows and local
input results expose the separate charges without adding a sidebar destination.

Dynamic Pricing Management includes an expandable read-only section for recorded
congestion/toll history and pricing-policy audit. It follows the pricing-preview
location. Malaysia-date/category filters apply server-side; daily analytics are
bounded to 1,000 records per type, and stored toll decisions to the latest 50 matches.
The chart has an accessible table alternative. Network policy audit is explicitly
separate from the location/date filters. Empty/error states do not fabricate values;
history requests never mutate live state or wallet balances.

Model Performance remains a compact keyboard-accessible modal. It separates the
protected held-out OCR evidence from the selected 32-case synthetic text origin
fixture (25/32 exact-origin decisions, 78.1%; zero cross-country errors and safe
abstentions). This is fixture evidence, not field or OCR accuracy. Positive detector
review reports 146 scorable plate-present images; four non-scorable scenes are
excluded. Unsupported detector metrics remain unavailable.

## Verification and limits

- Full backend suite: 143 tests, including 74 unit and 69 dedicated PostgreSQL tests.
- ML suite: 35 tests; no model tuning or changes to the held-out OCR set.
- Frontend suite: 80 tests, including component rendering, upload results, read-only
  history filters, navigation redirects, modal close/focus, and charge breakdowns.
- Production build and relevant Ruff/diff checks pass; the existing bundle-size
  warning remains.
- After the final telemetry timestamp/audit-empty-state adjustments, the 14 targeted
  Simulator/window tests and two history tests also passed.

The new endpoint tests use a controlled processor with the real session, API,
PostgreSQL, origin, payment, and telemetry services. They do not claim physical
webcam or optical recognition verification. No browser camera permission, real
payment/data integration, dependency installation, commit, push, or deployment was
performed for this slice.
