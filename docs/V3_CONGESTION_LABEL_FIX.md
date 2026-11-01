# Current congestion status and recorded pricing band

Verified on 2026-11-01.

## Cause

`app.api.locations._state` first calculated the current congestion percentage,
then replaced its category with `TollPrice.congestion_category`. For NPE, live
time-profile fallback reported approximately 33.5%, while the stored RM5.60 price
retained the `high` band. The map and selected-location panel therefore incorrectly
called current traffic Peak hour. The live source was `mixed`: estimated traffic
with a recorded toll, rather than a new matching traffic/price decision.

## Change

Normal-location `congestion_category` now classifies the displayed percentage with
the current configurable ranges. It applies equally to persisted measurements and
time-profile fallback and reclassifies historical measurements when ranges change.
No thresholds are duplicated in the frontend.

`pricing_category` separately identifies the stored price band, or the calculated
band when no price exists. `PricingExplanation` uses that field when present and
falls back to `congestion_category` for other existing telemetry contracts. When
the bands differ, it explicitly explains that current congestion and the recorded
toll belong to different bands. Existing map, status and Prediction current-state
consumers continue to use the corrected traffic category.

This fix changes neither persisted prices nor historical traffic. It does not
force a new price decision, change safeguards, alter foreign charges, generate
traffic or change the Simulator event/expiry pricing path. Normal-location reads
remain read-only. Runtime demo-feed generation retains its existing behavior.

## Verification

- Backend: 121 unit tests passed, including persisted/fallback mismatch regressions
  across selected Overview, network Overview, location live and network live APIs.
  Tests also verify custom ranges, unchanged recorded prices and no normal-read writes.
- PostgreSQL: 17 existing location, policy propagation and pricing safeguard tests
  passed against the guarded, dedicated test database.
- Frontend: 110 tests passed in 21 files, including distinct current congestion and
  recorded pricing-band rendering. Production build passed with the existing
  bundle-size warning. Changed Python Ruff and Git diff checks passed.
- Live local API: before restart NPE returned 33.52%, `high`, RM5.60; after restart
  it returned 33.52%, `moderate`, `pricing_category=high`, RM5.60. Each normal
  location's classification matched the saved configured ranges, including its
  individual live endpoint.

Only the verified local API was restarted. The presentation feed was paused for
restart and restored to its prior running state. Private local credentials were
used without printing or persisting tokens. Scoped before/after evidence is in
ignored `.plateplus-demo/qa-congestion-fix/`. No physical camera, external model
call, dependency installation, database reset, policy edit, commit or push occurred.
Legacy harnesses and unrelated existing user changes were preserved.

The first sandboxed test attempts could not complete because Windows blocked
Python event-loop socket creation and Vitest cache renames. The successful runs
used the reviewed execution escalation; no dependencies or test configuration
were changed to work around those sandbox restrictions.
