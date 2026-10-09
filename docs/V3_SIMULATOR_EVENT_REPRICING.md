# Simulator event repricing — 2026-10-09

## Root cause and sequence

`prepare_webcam_crossing_price` called `decide_price` with its default `traffic`
context. Normal minimum-change/hysteresis holds therefore applied to discrete
Simulator crossings. Each arrival appended a TollPrice even when held, refreshing
the timestamp from which the next cooldown was measured. With a 60-second window,
frequent arrivals could continually hold the initial low-band RM2.00 decision.
Read-side telemetry also calculated a hypothetical decision without persisting an
expiry transition. Missing expiry persistence and those rolling interval holds
kept displayed, attempted and stored prices stale.

Before: local/fallback acceptance -> current-window telemetry -> next count ->
normal traffic safeguard hold -> append held price -> payment's latest-price query.

After: local/fallback acceptance -> shared cooldown/replay check -> per-plaza lock
-> current accepted active count + 1 -> congestion -> canonical decide_price with
`webcam_crossing` context -> persist/reuse authoritative price -> pass its exact ID
to payment -> persist detection/transaction -> refresh canonical state.

The prepared price and TrafficRecord are flushed before payment. Payment selects
that exact price with matching location and non-future effective time, avoiding
timestamp-tie ambiguity. Price selection additionally orders by creation timestamp
and ID. New Simulator transitions explicitly record their creation time because
PostgreSQL now() stays constant within a transaction.

## Expiry, deduplication and safeguards

Live Simulator reads recalculate the same `(now - 60 seconds, now]` window. They
use `webcam_crossing_expiry` context, append only when amount or applied band
changes, and commit that transition at the canonical location-state boundary.
Unchanged reads reuse the stored price. Expiry creates no detection, traffic,
payment, speed or generated feed event. Arrivals still write one actual crossing
TrafficRecord, but do not spam identical price records within a band.

Discrete Simulator contexts skip normal traffic interval/hysteresis holds. Minimum
toll and maximum multiplier remain enforced by the same pricing service. Normal
generated traffic retains interval/hysteresis behavior; Simulator-specific contexts
are refused for non-Simulator locations. Explicit policy updates still price the
actual active window with their existing context and atomically persist updates.

Accepted/unknown-vehicle detections remain counted, including accepted recognition
with insufficient funds. Unknown origin, rejected/duplicate results and foreign
registration mismatch keep their existing semantics. Country/provider does not
enter congestion calculation. A failed unknown-vehicle attempt uses the new dynamic
toll while debiting nothing. MY gets zero foreign charge; SG/accepted foreign gets
the independently configured charge after the dynamic toll. Its setting is untouched.

## Verification report

| Requested item | Verified outcome |
| --- | --- |
| Root cause | Default traffic interval/hysteresis plus held-record timestamp renewal; expiry was not persisted |
| Prior/updated call sequence | Described above; exact prepared price ID passed into payment |
| Incoming crossing included | Active count + 1 before price/transaction; capacity 10, window 60 seconds |
| Upward pricing | Both upload/webcam, MY/SG: 3 -> 4 crossings gives RM3; 6 -> 7 RM4; 8 -> 9 RM5 with fixture rules |
| Expiry | Canonical HTTP reads: 7 crossings/RM4 -> 5/RM3 -> 0/RM2 |
| No price spam | Repeated identical live reads leave all price counts unchanged; reads create no TrafficRecord |
| Guards | Simulator floor/cap remain; normal interval/hysteresis regressions pass; policy updates remain immediate |
| MY totals | New dynamic toll, zero foreign fee; account debited once |
| SG totals | New dynamic toll + unchanged stored fee; components and account verified separately |
| Gemini | Mocked local-unresolved/overlap results cross 30 -> 40% using identical pricing for MY/SG/UK; no prompt/model changes |
| Unknown vehicle | Fourth accepted crossing counts; RM3 attempted dynamic toll, no debit |
| Database linkage | Transaction.toll_price_id resolves prepared price linked to incoming TrafficRecord at each band change |
| Backend tests | 232 passed: 118 unit + 114 dedicated PostgreSQL integration |
| Frontend tests | 109 passed in 21 files; card/KPI and arrival/expiry feedback use canonical backend amounts |
| Production build | Passed; existing >500 KB bundle warning remains |
| Static/security | Changed Python Ruff, git diff and source/bundle/log key audit passed |
| Harness | V3 AGENTS/PLAN/TODOLIST updated; legacy harnesses untouched |
| Git | No commit/push/merge/tag/main modification |

Frontend expiry message now says `Congestion decreased ... Toll adjusted from ...
to ...`, using received values only. The API was restarted with its private
environment retained; existing normal feed running state was restored. A live
Simulator GET verified 0 crossings / 0% / low / RM2. No plate was submitted, no
Gemini request made, and no Simulator charge generated by that smoke check.
Database/history/settings were not reset; foreign fee was not edited.

## Files changed in this pricing task

- `backend/app/services/traffic/pricing.py`
- `backend/app/services/traffic/webcam_crossings.py`
- `backend/app/services/transactions/toll_payment.py`
- `backend/app/api/webcam.py`
- `backend/app/api/locations.py`
- `backend/tests/integration/test_simulator_v3.py`
- `backend/tests/integration/test_gemini_upload.py`
- `backend/tests/integration/test_v3_pricing_safeguards.py`
- `frontend/src/presentationFeedback.ts`
- `frontend/src/presentationFeedback.test.ts`
- `frontend/src/SimulatorRepricing.test.tsx`
- `frontend/src/App.ui-contract.test.ts`
- `docs/V3_SIMULATOR_EVENT_REPRICING.md`
- `.harnessV3/AGENTS.md`, `.harnessV3/PLAN.md`, `.harnessV3/TODOLIST.md`

Previously uncommitted Gemini implementation/repair files remain in the workspace.
This task does not commit them, alter Gemini prompts/models, retrain, access physical
camera hardware, upload evaluation images or change the configured foreign fee.
