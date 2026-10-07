# V3 pricing configuration, Prediction, and operational rollups

## Separate simulated foreign-charge configuration

Dynamic Pricing Management exposes the persisted foreign-charge setting in its own
expandable **Simulated foreign-vehicle charge** section, separate from congestion
bands, safeguards, and pricing preview. It loads the configured amount only when
expanded and saves through the existing authenticated
`PUT /api/data/foreign-vehicle-charge` API. No demo amount is substituted if the
setting is unavailable. The form validates two-decimal nonnegative MYR values,
displays backend errors, and reports a save only after receiving the saved response.

The setting affects future eligible Singaporean simulated transactions. It does
not reprice congestion tolls, modify bands/multipliers, rewrite historical payment
components, or affect Prediction. Malaysian transactions add zero. The existing API
records the setting update in administrator audit history. This is configurable
prototype data, not a real toll-plaza fee or legal charging rule.

## Prediction boundary

Prediction uses LDP, AKLEH, NPE, and Grand Saga only. Its default datetime input is
formatted explicitly in `Asia/Kuala_Lumpur`, including midnight and year rollover,
rather than displaying a UTC value under a Malaysia-time label. Runs retain their
five-minute frames and horizons up to 12 hours.

The forecast models congestion and dynamic toll only. Plate origin and foreign
charges are neither inputs nor forecast outputs. Tests compare all four normal
location forecasts with and without origin/foreign-charge properties and verify
identical frame sequences, intact input state, and the next Malaysia date. No live
traffic, prices, detection/payment history, or wallets are mutated.

## Origin-rejection operational decision

Repeated ambiguous/unsupported origins are included in the existing per-location
low-confidence/rejected-recognition rollup. No separate origin alert type and no
per-detection event are introduced. A single rejection remains visible in detection
history; the warning threshold remains three rejected recognitions in 15 minutes.
The message identifies how many were safely rejected origin patterns. Pure origin
rejection volume remains warning severity; critical escalation requires at least
five actual confidence failures, rather than treating expected safe abstention as
a critical nationality/registration finding.

Repeated recognition and failed-payment incidents have a stable per-location/type
key. Monitoring updates the same incident, retains acknowledgement, and records an
event only on creation, severity transition, recovery, or recurrence. The rolling
window is `(now - 15 minutes, now]`; future and exactly-expired records do not count.
When fewer than three qualifying records remain, recovery is recorded once. A new
episode reactivates the incident and clears its prior acknowledgement. Retired
locations do not generate new incidents. Older severity-keyed incidents are
consolidated without deleting their historical rows.

Overview excludes resolved and acknowledged incidents from current issues, while
retaining them in its history section. All behavior remains simulated and creates
no enforcement, owner-data, or external notification integration.

## Verification status

Frontend verification passed: 89 tests and production build (existing bundle-size
warning). Backend unit verification passed: 74 tests. ML verification passed: 35
tests. Relevant Ruff and diff checks passed.

PostgreSQL regressions are implemented for origin rollup threshold/deduplication,
acknowledgement/recovery/recurrence, true-confidence severity changes, location and
retired-state isolation, legacy incident consolidation, and foreign-charge edits
leaving stored congestion policy/prices unchanged. Their execution is pending
permission to start the currently stopped dedicated `postgres_test` service.

No new schema, dependencies, model changes, physical camera test, development-data
reset, commit, push, or deployment is required or performed for this work.
