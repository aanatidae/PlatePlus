# V3 database migrations

The current V3 schema head is `20261002_0013`. Origin migration `20261002_0012`
follows the V2 head `20260908_0011`; foreign-charge migration `0013` follows `0012`.
Historical migrations remain unchanged.

`0012` adds detection `plate_origin` and `origin_reason`. Historical detections
default to `unknown`; migration does not retroactively classify their OCR text.
`0013` adds vehicle `registration_origin`, separate transaction `dynamic_toll_amount`
and `foreign_vehicle_charge`, and the `foreign_vehicle_charge_settings` singleton.
Legacy vehicles default to Malaysian, consistent with the pre-V3 fleet. Historical
transaction `amount` is retained and copied to the dynamic component; foreign charge
defaults to zero. The idempotent seed adds fictional Malaysian/Singaporean vehicles,
primary wallets, and opening ledger entries without resetting existing balances.

These migrations do not change location IDs or ownership. Simulator traffic, prices,
detections, and transactions remain at Simulator Toll Plaza, with their existing links.
Section I will perform the separate V3 normal-network alignment; G/H completion does
not claim that LDP/AKLEH/NPE/Grand Saga are already seeded.

## Repeatable verification

`backend/tests/integration/test_v3_migrations.py` compares a fresh migration-to-head
plus seed against a populated V2 database upgraded to V3 plus seed. It compares columns,
types, defaults, nullability, checks, foreign keys, indexes, the synthetic fleet and
wallet balances, location metadata/profiles, opening-ledger count, charge setting,
and migration head. It repeats seeding to check idempotency. The upgrade case includes
linked historical Simulator traffic, price, detection, and transaction records and
checks their IDs, ownership, links, timestamp, source, original amount, and V3 backfill.

The test also downgrades to V2 and upgrades back, verifies retained historical amounts,
and restores a clean head schema afterward. Downgrade removes origin and charge-component
columns and the charge-setting table; it cannot preserve V3-only metadata. Back up a
real database before any downgrade. The retained final `amount` is not changed by downgrade.

From `backend`, with the existing PostgreSQL test service running:

```powershell
$env:RUN_POSTGRES_TESTS = '1'
.\.venv\Scripts\python.exe -m pytest tests/integration/test_v3_migrations.py -q
```

The integration fixture destroys and recreates only the separate `capstone_alpr_test`
schema. It rejects a development database target before migration. Never run these
fixtures against development data. No physical webcam or model inference is required.

Full schema resets first clear disposable test rows so historical network downgrades
can remove seeded locations without violating their RESTRICT foreign keys. This cleanup
does not alter historical migrations; the populated V3-to-V2 downgrade is checked before
cleanup. On 2026-10-06 both migration scenarios and the full backend suite passed:
125 tests (73 unit, 52 PostgreSQL integration). Development data was not modified.
