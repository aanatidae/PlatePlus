# Optional Gemini upload fallback

## Live setup follow-up — 2026-10-09

The user installed google-genai 2.29.0, configured the private backend key and
enabled fallback. Live text-only diagnostics found the typed `response_schema`
request rejected with HTTP 400. The provider now sends `response_json_schema`
from the same strict Pydantic model and still validates output locally. No provider
exception contents are logged; a small allowlist of HTTP status codes may be shown
in the fixed unavailable message, without headers, key or request/response body.

`gemini-3.8-flash` was listed as available but returned HTTP 503 on two corrected
text-only probes; `gemini-2.5-flash` returned 404. `gemini-3.5-flash` returned a valid
strict structured response. The central default and only the private model setting
were changed to `gemini-3.5-flash`, and the existing API was restarted successfully
with its private environment preserved. No image, webcam frame or dataset was sent
during these diagnostics; live multimodal/user-image verification remains separate.
Schema/payment regressions: 39 passed; relevant Ruff and secret audit passed.
This supersedes the original activation-pending/no-live-call notes below for the
now-configured local setup, while preserving their implementation-stage history.



YOLO11, cropping, PaddleOCR, normalization and local origin rules remain primary.

Gemini is an optional backend-only second opinion, **disabled by default** and

implemented for administrator uploads only. Webcam frames never invoke Gemini.



## Architecture, triggers and bounds



`React -> FastAPI -> local ALPR -> optional Gemini -> PlatePlus validation -> synthetic payment`



Central service: `backend/app/services/detection/gemini_fallback.py`. It uses

[Google's official Python SDK](https://github.com/googleapis/python-genai), inline

JPEG bytes and Pydantic-constrained JSON. The central configurable model default

is `gemini-3.5-flash`, listed in [Google's model documentation](https://ai.google.dev/gemini-api/docs/models).

It does not replace the local models or influence their evaluation metrics.



Only `no_plate_detected`, `unread_plate`, `ocr_unreadable` (empty local OCR) and

`ambiguous_plate_origin` trigger fallback. Clear local results, readable results

below confidence gates, unsupported local patterns, duplicates, payment failures

and native local-runtime exceptions do not trigger it. Crop is preferred when

available, otherwise the original image is decoded/re-encoded. Metadata is removed

and images are downscaled to at most 1600 pixels on the longest side.



HTTP timeout and outer async deadline default to 15 seconds, configurable within

1–30 seconds. SDK attempts=1 means no automatic retries. Timeout/rate limit/API

errors, unavailable SDK, malformed schema and unknown/low-confidence output fail

safely. SDK exceptions/prose are never logged or returned. Completed idempotent

requests replay their stored result before new inference or external transmission.

Intentional separate uploads can each call Gemini. There is no webcam external

loop. Existing Simulator cross-input cooldown and payment replay still apply.



## Schema and acceptance



Strict Pydantic response, extra fields forbidden:



| Field | Allowed value |

| --- | --- |

| plate_detected | boolean |

| plate_text | nullable string, maximum 32 characters |

| origin | malaysian / singaporean / foreign_other / unknown |

| country | nullable string, maximum 64 characters |

| confidence | high / medium / low |

| reason | concise string, maximum 160 characters |



Only high-confidence visible plates can proceed. PlatePlus accepts ASCII letters,

digits and space/hyphen separators, normalizes without country-forcing corrections,

checks length/digits and the claimed origin's supported format. It rejects other

glyphs instead of removing/transliterating them. For local overlap, returned text

must equal the readable local plate; original local OCR and numerical confidence

are retained. Numerical local model scores are never invented for fallback.



MY/SG reuse existing independent pattern predicates. Visual evidence can resolve

overlap, but synthetic vehicle origin must match. Initial other-foreign support is

deliberately limited to modern **United Kingdom** plates (`AA00AAA` shape) with

country `United Kingdom`; unsupported countries remain unknown/manual review.

This is pattern/visual evidence, not legal registration, nationality or ownership.

No owner or government query exists.



The payment service revalidates internal fallback evidence. It still requires an

active synthetic vehicle with matching origin/country, active primary account,

stored non-future price, sufficient balance and location. Existing MY/SG records

with no declared country remain compatible; other-foreign country is required.



| Origin | Simulated outcome |

| --- | --- |

| MY | Dynamic toll, foreign charge zero |

| SG | Dynamic toll + configured separate foreign charge |

| Supported other foreign | Same separate charge; matching synthetic country required |

| Unknown / unavailable / invalid | Pending review, no successful debit |



Unregistered plates never debit a wallet. Balance, ledger, notification, refund and

idempotency use the combined total. Origin never changes congestion multipliers,

bands, traffic or Prediction. The 96-MY/three-SG seeded fleet is unchanged; no

other-foreign seed was invented. An administrator can register a fictional UK

vehicle with `registration_origin=foreign_other`, `origin_country=United Kingdom`.



## Activation and privacy



No packages were installed during implementation. The manifest declares

`google-genai>=1.55,<3.0`; SDK installation remains subject to approval.

After approval, from `backend`:



```powershell

.\.venv\Scripts\python.exe -m pip install -e .

.\.venv\Scripts\python.exe -m alembic upgrade head

```



Set `ENABLE_GEMINI_FALLBACK=true` and provide `GEMINI_API_KEY` only in the backend

environment or private ignored root `.env`. Never paste a key into chat/source or

frontend settings. `.env.example` has a blank key/model placeholder. Blank model

selects the central default. Configure `GEMINI_TIMEOUT_SECONDS` if needed, then

restart the API. No development migration or API restart was done for this feature;

only disposable PostgreSQL tests applied migration `20261009_0015`. The existing

running API still uses its previously loaded code. Live activation is separate.



The client reads its credential solely from backend environment; the explicitly

environment-derived SDK argument prevents a different GOOGLE_API_KEY from silently

overriding it. No literal credential, query parameter, browser SDK, provider URL,

SDK error, auth header or backend environment is exposed to React. Private `.env`

is ignored/untracked. Existing `.env.*` covers `.env.local`/`.env.*.local`, with

`.env.example` excepted. The key was not supplied, copied, printed or written by

this task. Missing key gives safe `gemini_unavailable` without a provider call.



When enabled and invoked, an individual image/crop leaves this machine for Google

processing. PlatePlus does not persist those bytes; Google's retention policies

are separate, and PlatePlus cannot promise remote deletion. Webcam remains local.

No dataset image is automatically transmitted or used to fabricate metrics.



## Database and UI audit



Migration `20261009_0015` adds vehicle `origin_country`; detection

`recognition_source`, `origin_source`, `origin_country`, `fallback_used`,

`fallback_provider`, `fallback_status`; nullable local detector confidence; and

other-foreign origin constraints. Existing records default to local/no-fallback.

History/prices are preserved; downgrade refuses to discard fallback or foreign

audit evidence. Request body, images, headers, key and provider reason prose are

not persisted. `fallback_used` means an attempted provider call, not guaranteed

remote receipt; missing-key/invalid-image preflight has fallback_used=false.



Result UI names recognition/origin sources, fallback status and country. Recent

detections label fallback context. Charge configuration covers accepted foreign

origins. Model Performance separates Gemini from detector/OCR/origin evaluations.

Average local confidence excludes external transcription records; local scores

remain available when Gemini only resolves origin. No new dashboard page exists.



## Tests and security report



Mocks cover local success and disabled/key gates, unread fallback, crop selection,

overlap/text consistency, MY/SG/UK formats, uncertainty/unsupported glyphs,

schema failures, timeout cancellation, rate-limit-like errors, safe SDK configuration

and secret-free responses/logs. PostgreSQL paths verify MY/SG/UK payments, audit,

component totals, ledger, replay without another provider call, unknown/timeout,

unregistered vehicle, insufficient balance and country mismatch. Migration tests

verify backfill, nullable confidence and lossy-downgrade refusal. Frontend tests

verify disclosure/result labels and PlatePlus-only browser uploads.



Run the non-disclosing audit from root:



```powershell

.\backend\.venv\Scripts\python.exe scripts/audit_gemini_secrets.py

```



It inspects tracked/untracked source, ignored frontend environment files,

production bundle and local logs for Google-like keys and any configured backend

key; prints paths only, not contents. Only private root `.env` is exempt.

Exact final test/build/audit results and file inventory are recorded in

`.harnessV3/TODOLIST.md` section AC. No real Gemini requests, model changes,

physical camera tests, dataset transmissions, commits or pushes occurred.



## Changed-file inventory



- `.env.example`

- `.harnessV3/AGENTS.md`

- `.harnessV3/PLAN.md`

- `.harnessV3/TODOLIST.md`

- `README.md`

- `backend/app/api/dashboard.py`

- `backend/app/api/intelligence.py`

- `backend/app/api/live.py`

- `backend/app/api/webcam.py`

- `backend/app/core/settings.py`

- `backend/app/models/entities.py`

- `backend/app/schemas/database.py`

- `backend/app/schemas/webcam.py`

- `backend/app/services/detection/gemini_fallback.py`

- `backend/app/services/detection/webcam_processor.py`

- `backend/app/services/overview.py`

- `backend/app/services/transactions/toll_payment.py`

- `backend/migrations/versions/20261009_0015_gemini_fallback_audit.py`

- `backend/pyproject.toml`

- `backend/tests/integration/test_gemini_migration.py`

- `backend/tests/integration/test_gemini_upload.py`

- `backend/tests/integration/test_v3_migrations.py`

- `backend/tests/integration/test_v3_network_migration.py`

- `backend/tests/unit/test_gemini_fallback.py`

- `backend/tests/unit/test_v3_payment.py`

- `docs/ARCHITECTURE.md`

- `docs/FOREIGN_VEHICLE_CHARGE.md`

- `docs/GEMINI_FALLBACK.md`

- `docs/SETUP.md`

- `frontend/src/AlprResultDetails.tsx`

- `frontend/src/ChargeDetails.tsx`

- `frontend/src/ForeignChargeSettings.tsx`

- `frontend/src/GeminiFallback.test.tsx`

- `frontend/src/ModelPerformance.tsx`

- `frontend/src/RecentActivity.tsx`

- `frontend/src/SimulatorImageUpload.tsx`

- `scripts/audit_gemini_secrets.py`



## Requested completion checklist



| # | Report item | Outcome |

| --- | --- | --- |

| 1 | Files changed | Full inventory above; existing dataset untouched |

| 2 | Backend architecture | Central Google provider + fallback + validated evidence; FastAPI only |

| 3 | Triggers | No plate, unread/empty OCR, ambiguous origin only |

| 4 | Structured schema | Strict fields/types/limits listed above |

| 5 | Local validation | High confidence, ASCII/length/digits, country pattern, overlap text consistency, payment revalidation |

| 6 | Malaysian | Existing patterns, matching synthetic registration; no foreign fee |

| 7 | Singaporean | Explicit pattern/origin retained; separately configured fee |

| 8 | Other foreign | Modern UK format/country only initially; matching synthetic country |

| 9 | Unknown | Pending review; no successful deduction |

| 10 | Foreign charge | Added after stored dynamic toll; existing ledger/refund/price safeguards |

| 11 | Upload | Local first, in-memory crop/original fallback, audit and payment, replay skips provider |

| 12 | Webcam | Fallback intentionally unsupported/disabled; every frame stays local |

| 13 | Timeout/rate limits | 15-second default, 1–30-second bounds, single attempt, safe unavailable status |

| 14 | Feature flag | Default false; missing key/SDK fails safely |

| 15 | Privacy | UI/docs disclose enabled image egress; PlatePlus does not persist bytes; Google policies separate |

| 16 | Database/audit | Migration 0015, safe backfill, source/country/provider/status fields, nullable confidence, guarded downgrade |

| 17 | Added tests | 28 mocked unit cases, 11 payment/API integration cases, one migration case, two UI cases |

| 18 | Test results | Backend 211 passed (118 unit + 93 dedicated PostgreSQL); ML 49 passed; frontend 108 passed in 20 files |

| 19 | Production build | Passed; existing >500 KB bundle warning remains |

| 20 | Frontend calls | React calls only PlatePlus; no browser Gemini SDK/endpoint |

| 21 | Frontend key | Source/config/bundle audit passed; no key or key variable |

| 22 | Environment ignore | .env ignored/untracked; .env.local/.env.*.local ignored; .env.example preserved |

| 23 | Actual key | Not supplied/copied/written; audit found none outside private ignored .env |

| 24 | Git | No commits/pushes/main modifications; feature/sgimplementation retained |

| 25 | Harness | Only V3 AGENTS/PLAN/TODOLIST updated with scope, disclosure, secret rules, results and activation pending |



Changed Python Ruff and git diff checks passed. Unit/provider mocks never called the real Gemini API.

The SDK is declared but not installed, and the running development schema/API are not upgraded.
