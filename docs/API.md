# V3 API contracts

The FastAPI API exposes interactive OpenAPI at `/docs` and its current schema at
`/openapi.json`. Operational endpoints require an administrator bearer token from
`POST /api/auth/login`. These APIs operate only on synthetic records; they do not
query JPJ/LTA/VEP, owner databases, banks or real eWallets.

## Origin and charge fields

| Endpoint | V3 contract |
| --- | --- |
| POST/GET `/api/data/vehicles` | `registration_origin`: `malaysian` or `singaporean`, defaults to Malaysian on creation; plate is normalized |
| GET `/api/data/detections` | Persisted `plate_origin`, `origin_reason`, raw/normalized text, confidence, source, `location_id`, status and review state |
| GET `/api/data/transactions` | `dynamic_toll_amount`, `foreign_vehicle_charge`, `amount`, status, nullable failure reason, balance after, location and reversal metadata |
| GET/PUT `/api/data/foreign-vehicle-charge` | `{ "amount": "20.00", "updated_at": "..." }`; PUT accepts amount only, nonnegative with at most two decimal places, and writes an administrator audit |
| POST `/api/data/transactions/{id}/reversal` | Reason and idempotency key; credits the recorded successful unreversed total |
| GET `/api/locations` | Four current normal locations plus separate Simulator; excludes retired entries |
| GET `/api/locations/{id}` | Metadata by original ID, including retained retired history context |
| GET `/api/live/overview` | `scope=all_locations` or `location_id`; canonical telemetry and recent records carry origin/charge fields |

Database Decimal response values serialize as JSON strings; clients must convert
them explicitly for arithmetic. `amount` is a successful debit only when status is
`successful`; failed rows display an attempted total. No partial debit is made.
Manual `POST /api/data/transactions` validates component reconciliation but creates
a record, not an ALPR/payment-processing request. Manual record-create schemas do
not accept a location override; use the local recognition workflow for a crossing.

History endpoints support `location_id`, `start_at`, `end_at`, plate/status/category
filters as applicable, `offset` and `limit` (1–200). Filters are applied before
pagination; use explicit `+08:00` timestamps for Malaysia-time day boundaries.

## Local input result

The local-only router supports `POST /api/webcam/sessions`,
`DELETE /api/webcam/sessions/{id}`, multipart `POST
/api/webcam/sessions/{id}/frames` (`frame`) and `POST /api/webcam/images` (`image`).
The Overview still-image UI supplies the Simulator `location_id`; the API retains
an optional location parameter for legacy local requests. Uploads allow
JPG/JPEG, PNG and WebP up to 5 MB. Pass an `Idempotency-Key` for event replay.
The cloud API excludes this router by design.

`WebcamFrameResult` includes `status`, `message`, `plate_text`, `plate_origin`,
`origin_reason`, detection/OCR confidence, bounding box, `charge_eligible`, cooldown,
and nullable `payment_status`, `payment_amount`, `payment_dynamic_toll_amount`,
`payment_foreign_vehicle_charge`, `payment_balance_after`, plus `payment_duplicate`.
Unlike database Decimal responses, these payment amounts are JSON numbers.
Both input paths share normalization, confidence/origin safety, vehicle lookup,
duplicate protection and payment handling. Unknown/overlapping origin never debits.

Example selected fields for a synthetic SG success:

```json
{
  "status": "accepted_for_vehicle_lookup",
  "plate_origin": "singaporean",
  "payment_status": "successful",
  "payment_dynamic_toll_amount": 2.0,
  "payment_foreign_vehicle_charge": 20.0,
  "payment_amount": 22.0,
  "payment_duplicate": false
}
```

Values above are illustrative configuration. Origin does not change the congestion
multiplier. Missing price/setting/account, mismatched declared origin, low confidence
or insufficient balance fail safely. Invalid requests return validation errors;
missing resources, conflicts and authentication failures use 404, 409 and 401 as
applicable. See [charge behavior](FOREIGN_VEHICLE_CHARGE.md) and
[database schema](DATABASE_SCHEMA.md).
