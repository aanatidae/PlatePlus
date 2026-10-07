# V3 database schema

PostgreSQL uses SQLAlchemy entities in `backend/app/models/entities.py` and additive
Alembic migrations. UUID primary keys identify operational records; timestamps are
timezone-aware. All owners, wallets, payments and traffic are synthetic.

| Table | Purpose and relationships |
| --- | --- |
| admins | Hashed credentials for authenticated administrator access |
| users | Fictional owners; parent of accounts, vehicles and payment notifications |
| accounts | MYR synthetic balance/opening balance, active/primary flags, user FK; nonnegative balance |
| vehicles | Unique normalized plate, user FK, active flag, declared `registration_origin` (`malaysian` or `singaporean`) |
| toll_locations | Unique code, display/route metadata, prototype coordinates, status, nonnegative flat base toll, positive capacity and JSONB simulation profile |
| detection_records | Location FK, nullable vehicle FK, raw/normalized text, confidence, `plate_origin`, `origin_reason`, source and review metadata |
| traffic_records | Location FK, bounded congestion, positive capacity, vehicle count, scenario, timestamp and simulated flag |
| toll_prices | Location/optional traffic FKs, effective timestamp, nonnegative MYR amount and applied congestion category |
| toll_transactions | Location and optional account/vehicle/price/detection FKs, unique event key, status, stored components, balance after and reversal metadata |
| foreign_vehicle_charge_settings | Singleton `default`, nonnegative two-decimal amount and update timestamp |
| wallet_ledger_entries | Account/optional transaction FKs, immutable opening/debit/top-up/reversal entries, unique key, amount/direction and balance after |
| payment_notifications | Fictional user/optional transaction FKs, message, type and read timestamp |
| traffic_simulation_settings / dynamic_pricing_rules | Schedule, safeguards and four contiguous congestion bands with location-relative multipliers |
| admin_audit_logs / operational_alerts / operational_events | Configuration audit, stable deduplicated incidents and retained lifecycle transitions |

Detection origin is an observed pattern decision (`malaysian`, `singaporean`,
`unknown`); declared vehicle registration origin is separate. A pattern match does
not verify legal registration. Sources include `webcam_alpr`, `uploaded_image` and
`demo_generated`. Raw frames/uploads/crops are ephemeral by default; optional legacy
image/crop path columns do not imply that raw bytes are retained.

Transactions reconcile `amount = dynamic_toll_amount + foreign_vehicle_charge`.
Amounts are nonnegative. For success, `amount` is the debit; for failure it is the
attempted total, with no ledger debit. MY foreign charge is zero; eligible SG
transactions use the configured setting once. Replay returns recorded components;
refund credits the actual original debit even if settings subsequently change.

## Migration history and ownership

- `20261002_0012`: detection origin and reason; historical decisions remain unknown.
- `20261002_0013`: vehicle origin, charge components and foreign setting. Existing
  transaction amount is backfilled to dynamic toll with zero foreign charge.
- `20261007_0014`: current normal network LDP/AKLEH/NPE/GRAND_SAGA. LDP retains its
  ID, DUKE/KESAS retire with original history, AKLEH/Grand Saga receive independent
  IDs, and Simulator history retains ownership.

Never rewrite applied migrations or relabel retired highway history. A downgrade
that would remove populated new highways is refused by RESTRICT foreign keys.
Clean and upgraded schemas converge with idempotent seed. See
[migration evidence](V3_DATABASE_MIGRATIONS.md) and [network](MULTI_LOCATION.md).
