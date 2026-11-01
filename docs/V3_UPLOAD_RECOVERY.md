# Upload stall containment and recovery

Verified 2026-11-01.

## Cause and evidence

The async upload and webcam-frame handlers called the synchronous local
YOLO/PaddleOCR service directly. Native model loading/inference therefore occupied
FastAPI's event loop. During the reported stall, even an actual `/health` request
timed out; refreshing the dashboard could not load `/api/locations`. Current logs
stopped during Paddle model setup. The precise internal native-library stall was
not established from those logs; this fix contains slow initialization, inference
hangs and child crashes without relying on a particular Paddle exception.

The upload component also had no request deadline and generated a fresh event key
on every submission. That allowed indefinite disabled controls and made a retry
after a lost response unsafe once the ordinary plate cooldown expired.

## Implementation

- `IsolatedFrameProcessor` runs one lazy, cached local model process. A nonblocking
  admission lock rejects overlapping scans instead of creating an unlimited queue.
  Startup readiness and result waits share a bounded deadline. Timeout terminates
  and reaps the owned child; the next scan starts a fresh one. IPC startup waits
  for readiness before sending the bounded image. Images travel only in memory.
- Both API inputs dispatch synchronous local work through a threadpool, leaving
  the API event loop available. The child performs recognition only and has no
  database, pricing, payment or Gemini access. A timeout/crash returns readable
  HTTP 503 before those downstream stages. API shutdown closes its worker.
- `LOCAL_INFERENCE_TIMEOUT_SECONDS` defaults to 60 seconds, configurable from 1–120.
  Existing thresholds, OCR normalization, origin validation and payment safeguards
  remain unchanged. Optional upload-only Gemini retains its own existing deadline.
- The browser adds warm-up feedback, a 150-second request deadline, abort on
  clear/unmount and guards against a late response replacing a newer selection.
- Pending upload identity is scoped to location and SHA-256 of image contents.
  Only the hash and random event key are stored in sessionStorage. An uncertain
  submission can be retried after refresh with the same key; completed backend
  results replay without inference/provider calls or a second deduction. A complete
  HTTP success clears the pending identity. An intentional later submission can
  create a new event, subject to normal duplicate protection.

Stopping a browser wait does not undo an event already committed by the server.
The preserved event key resolves that uncertainty safely. Stopping the native worker
on its server deadline is stronger: that worker cannot later return recognition
and reach a payment stage. No automatic retry is introduced.

## Verification

| Boundary | Evidence |
| --- | --- |
| Native worker lifecycle | Real spawned synthetic workers verify cached reuse, timeout termination, fresh-worker recovery, crash recovery and bounded concurrent admission. |
| API responsiveness | Unit HTTP tests for upload and webcam frames hold a scan open while a concurrent async health request succeeds; failed inference cannot call fallback, pricing or payment. |
| Database safety | Dedicated PostgreSQL timeout regression verifies unchanged detections, transactions, traffic, prices, wallet ledger and balances. Existing upload, mocked fallback, Simulator and toll payment cases pass. |
| Actual cached local models | Fictional VAA1234 and GBC6427R recognized as MY/SG in 16.95s and 2.78s in a fresh isolated worker; no provider or database calls. |
| Actual running API | Fictional MY upload returned HTTP 200 in 12.31s while 23 concurrent health/location checks all passed; slowest combined pair 94ms. The existing synthetic account correctly reported insufficient balance for RM2.00. No top-up/reset was performed. |
| Replay | Same event returned duplicate=true with identical amount/balance in 78ms; no additional deduction or inference. |
| Browser recovery | Installed Edge with synthetic responses and an accelerated test clock verifies timeout feedback, enabled controls, refresh, same-image key reuse and successful result rendering. No actual image egress or database writes from browser fixtures. |

128 backend unit tests passed. The existing targeted PostgreSQL run passed 64
cases; after adding the timeout regression, all six image-upload cases passed.
114 frontend tests passed in 22 files. TypeScript/production build, changed Python
Ruff and diff checks passed; the existing large-bundle warning remains. The first
synthetic child startup test needed a longer startup allowance under simultaneous
native smoke-test load; its hang-specific deadline remains short and independently
verified. No model accuracy claim is derived from smoke fixtures.

The verified wedged local API was replaced; the frontend and databases were left
running. The last recorded feed-control action was start, so that running state
was restored. Existing private settings and synthetic history were preserved.
Ignored runtime/browser evidence is in `.plateplus-demo/qa-upload-recovery/`.

No dependency installation, model download, training, migration, physical camera
verification, real external provider call, dataset edit, history reset, commit or
push was performed. Unrelated pre-existing user source/dataset changes remain.
