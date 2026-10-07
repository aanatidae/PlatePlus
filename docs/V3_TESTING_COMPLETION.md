# V3 backend, ML and frontend testing

Sections T, U and V were completed on 2026-10-07. Existing coverage was reviewed
before adding missing regressions. No application behavior or dependencies changed.

## Coverage

| Checklist | Verified coverage |
| --- | --- |
| T: origin classifier | `backend/tests/unit/test_v3_payment.py`: MY, SG, overlap and unsupported decisions |
| T: country charge behavior | Unit payment workflow checks MY zero fee, SG configurable/zero fee, exact-total sufficiency, insufficient balance and ledger debit; PostgreSQL payment tests cover replay, mismatch, missing setting and reversal |
| T: flat-rate location validation | `test_pricing_decision.py` tests local-base/congestion-only pricing; `test_v3_pricing_safeguards.py` exercises all four seeded V3 bases with floor, cap, interval and hysteresis; network/migration tests verify codes, capacities and bases |
| T: origin and charge persistence | `test_toll_payment.py` verifies stored detection reasons/components and authenticated API serialization |
| T: location-aware SG payment | New parameterized test processes an SG payment at each normal highway, verifies its own stored price, wallet total and origin/components, and rejects leakage into another location's API history |
| T: upgraded migration | `test_v3_migrations.py` and `test_v3_network_migration.py` cover fresh/upgraded convergence, backfills, preserved history, downgrade and re-upgrade |
| T: regressions | Full backend suite includes location/network, Simulator, wallet/reversal, foreign-setting isolation and origin-alert lifecycle tests |
| U: fixtures and classifier | `test_plate_origin.py` covers supported SG/MY layouts, ambiguity, unsupported inputs, OCR confusions and normalized input decisions; `test_origin_evaluation.py` checks the separate 32-case fixture confusion matrix |
| U: protected OCR set | New regression checks the canonical Git blob hash `b723d69850778f9a65d1a3db1bd386272aea80f7` before origin evaluation and unchanged contents afterward; the 44-crop manifest was not edited |
| V: normal network and map | `locations.test.ts` and `selangorNetwork.test.ts` check V3 codes, route labels and marker routing, with Simulator separate |
| V: Prediction selector | New rendered `V3LocationSelect.test.tsx` opens the real selector, verifies exactly the four active highway labels, excludes Simulator/retired highways and selects Grand Saga by its ID |
| V: origin and charges | `V3Presentation.test.tsx` verifies origin labels, separately itemized SG totals, compact MY zero-fee rows and local-input feedback |
| V: navigation | `DashboardNavigation.test.tsx` verifies three destinations, retired-route redirects and the evidence modal |

## Results

- Backend: **160 passed** (82 unit, 78 dedicated PostgreSQL integration), no skips.
- ML: **40 passed**.
- Frontend: **90 passed** in 16 files.
- Frontend production build: passed; existing warning for a bundle above 500 kB remains.
- Ruff on changed Python tests and `git diff --check`: passed.

Commands use the existing environment:

```powershell
cd backend
$env:RUN_POSTGRES_TESTS = '1'
.\.venv\Scripts\python.exe -m pytest tests -q
cd ../ml
..\backend\.venv\Scripts\python.exe -m pytest tests -q
cd ../frontend
npm test
npm run build
```

The user approved starting only `postgres_test`; no development service was started.
The integration fixture guards the separate `capstone_alpr_test` target and resets
its disposable schema. Initial sandbox runs encountered localhost/cache restrictions;
the complete authorized reruns passed with the required local access. The dedicated
test service remains running. No package/model installation, physical webcam test,
commit, push or deployment occurred. Final physical/demo verification is still separate.

This full integration run also verifies the previously pending P/Q/S PostgreSQL
regressions. It does not substitute for section Y's final localhost presentation run.
