# Presentation reliability and Singaporean detector transfer evaluation

Completed on 8 October 2026 on `feature/sgimplementation`. This pass fixes the
four presentation issues, evaluates the existing detector, and surfaces separate
verified transfer evidence. No training, origin-rule changes, OCR replacement,
new dashboard page, physical webcam test, commit, push, merge or deployment.

## 1–2. Modal clipping: cause, fix and verification

`ModelPerformance` rendered its fixed backdrop inside the sticky top-control bar.
That ancestor has `backdrop-filter: blur(12px)`, creating a containing block for
fixed descendants. The modal was centered relative to the header instead of the
viewport, which could place its top above the usable page.

The modal now uses a `document.body` portal. Its viewport backdrop centers a flex
column panel with a responsive 24–40px margin. The header stays outside the
internally scrollable body, and background page scrolling is locked while open.
Close button, Escape, backdrop-only dismissal, focus trap and trigger-focus return
are preserved. The evidence body is keyboard-focusable and scrollable.

Actual browser checks used the running API and the enlarged verified evidence:

| Viewport | Modal top | Modal bottom | Header after internal scroll |
| --- | ---: | ---: | --- |
| 1920×1080 | 40px | 1040px | Remained in place |
| 1600×900 | 36px | 864px | Remained in place |
| 1366×768 | 30.72px | 737.27px | Remained in place |

All panels were viewport-centered and bounded. Their content exceeded available
height and scrolled internally; the header/close button remained accessible.
Local screenshots and measurements: `.plateplus-demo/qa-presentation/`.

## 3–4. Pricing Preview: cause, trace and proof

The original request did send the entered congestion to the existing read-only
backend endpoint. The useful returned band/multiplier/new toll was rendered only
inside a collapsed `Why this price?` disclosure. The two always-visible fields
were previous toll and a generic decision reason, so different results looked
identical. Editing congestion also retained the prior result while the explanation
used the new input, and late requests were not protected against input changes.

The corrected trace is:

`input → finite/hundredth validation → request sequence → GET pricing-preview →
Decimal validation → existing decide_price → returned submitted percentage and
decision → always-visible result breakdown`.

Changing congestion/location or saving policy invalidates the result; a late
response cannot replace a newer input. GET requests omit an unnecessary JSON
Content-Type header. The backend rejects values outside 0–100 and more than two
decimal places, avoiding unsupported fractional gaps between hundredth bands.
No pricing calculation was duplicated in React.

Actual AKLEH saved-policy API and browser results:

| Entered congestion | Band | Base toll | Multiplier | Preview toll | Previous toll |
| --- | --- | ---: | ---: | ---: | ---: |
| 10% | Low | RM2.40 | 1.00× | RM2.40 | RM2.40 |
| 90% | Severe | RM2.40 | 2.50× | RM6.00 | RM2.40 |

Database price/traffic/detection/transaction counts and every wallet balance were
unchanged across the actual previews. PostgreSQL regressions prove no live price
is persisted and exercise interval holds and caps. The existing interval and
hysteresis can legitimately retain a prior band; the visible reason explains
that. Floor/cap application is now appended to the backend decision reason.
Saved rules/safeguards were not edited in the development database.

## 5. Shared dropdown truncation

The portalled menu width was forced to the trigger width, and option spans used
nowrap/ellipsis. The shared selector now measures the hidden menu's intrinsic
label width independently of the compact trigger, clamps it to the viewport,
and preserves the existing upward/downward positioning logic. Labels can wrap
at constrained widths, horizontal scrolling is suppressed, and each option has
its full label as a title. Selected-state and keyboard/Escape behavior remain.

The actual six-option menu (All Locations plus five plazas) was 212px wide at the
checked laptop viewport. Grand Saga's full label occupied 184px without clipping;
all five requested plaza names were visible. The menu remained inside the viewport.
Near-edge/wider-menu unit tests also exercise a 390px viewport.

## 6–7. Feed stopping: diagnosed paths and lifecycle fix

There is no record-count cap, fixed feed duration, token check in the worker, or
browser visibility timer that stops backend generation. Three failure paths were
identified:

1. Only `generate_crossing` was inside a catch block. Session opening, querying
   locations/vehicles and obtaining `_state` telemetry occurred outside it. Any
   exception there terminated the daemon thread permanently. Crossing exceptions
   inside the narrow catch were rolled back silently with no diagnostic state.
2. The five-second polling tick aborted any request still in flight before its
   fifteen-second deadline. A response taking more than five seconds could be
   canceled on every tick, leaving the display frozen. Polling now serializes
   requests; periodic refresh skips a busy request without increasing deadlines.
   Location changes still abort the old scope. Fake-timer regressions reproduce
   the old starvation path and verify a ten-second response is now rendered.
3. Frontend polling retained old data on authentication/network failure, and the
   feed text ignored `feed.error`. The browser session encountered during this
   pass had expired and could no longer fetch administrator data. That can make
   fresh backend activity appear stopped. Control requests also ignored non-2xx
   status, so a failed action could appear successful.

The user's earlier stalled session has no retained failure traceback. Therefore
the exact historical exception cannot honestly be identified. The dead-worker
path was reproduced with injected failures; slow-poll starvation was reproduced
with fake timers; the expired browser session was directly observed. This is not
a claim that a particular historical database
exception occurred, or that extending a timeout fixes the issue.

The worker now catches the entire cycle, closes the failed session, logs the
traceback, exposes `recovering`/last-error state and retries with interruptible
5/10/20/30-second capped backoff. Success clears recovery state. Normal operation
retains congestion-controlled cadence, bounded jitter, the 96-vehicle fleet,
16-per-location/four-global repeat suppression and canonical stored prices.

Start refuses to create a second worker while the prior thread is alive. Each
start has a separate stop event; pause joins the worker outside its lock. Reset
first stops the worker and refuses deletion while a cycle is still in flight,
then uses the original scoped refund/deletion behavior. Backend shutdown requests
pause. The UI shows recovery, stopping, unavailable polling and failed controls
explicitly; it does not label stale cached status as current healthy running.
Authentication remains enforced; an expired browser session needs sign-in again,
while the backend feed continues independently.

Verification: 3,996 crossings across 10,000 virtual seconds (2h46m40s), all four
normal locations, all 96 plates used; injected cycle failures recovered with
bounded backoff; pause/restart remained singleton. A real API-backed run stayed
running over 80 seconds, with counter samples 88→97→106→114→122. It then paused,
and the counter stayed 122. The database audit confirmed LDP/AKLEH/NPE/Grand Saga
only, never Simulator. No development history was reset.

## 8–12. Dataset, split and exact results

Found archive:
`C:/Codex/CapstoneProject/SG License Plate.v2i.yolo26.zip`
(357,503,836 bytes). Original archive SHA-256:
`c1125a9a693cb652e82a3f1518a7a2446ccdd64ee00398178489aab827076671`.
The archive is unchanged and explicitly ignored, together with `.plateplus-eval/`.

The provided YOLO export has `data.yaml`, README metadata, one class
`license-plate`, and matching image/label folders:

- Train: 5,850 images.
- Valid: 328 images.
- **Selected provided test: 31 images, 33 labelled plates.**

Only the test split was extracted. It contains 31 box rows and two polygon rows;
polygons were converted into enclosing boxes in a separate local prepared copy
for localisation-only evaluation. Original ZIP/dataset annotations were preserved.
Three duplicate `data.yaml` entries have identical content; conflicting entries,
path traversal and ZIP symlinks are rejected by the tool.

Model: `models/trained/car_plate_yolo_best.pt`, SHA-256
`50826f9351d90f35e8d4bcb24b382c058d94438a0bf7ba59bbffa7ddb265df35`.
Dataset class 0 maps to detector class 0 (`car plate`) only for evaluation. No
country label is learned/inferred by YOLO, and OCR/origin logic was not called.

CPU evaluation used installed Ultralytics 8.4.173, 640px input, NMS IoU 0.70,
batch 4 for standard validation, AP confidence floor 0.001. Separate operational
matching used the current 0.50 confidence gate and one-to-one IoU ≥0.50 matches.

| Metric | Exact result | Display |
| --- | ---: | ---: |
| Standard precision | 0.8260703744891922 | 82.6% |
| Standard recall | 0.7878787878787878 | 78.8% |
| mAP@0.5 | 0.8102867751807709 | 81.0% |
| mAP@0.5:0.95 | 0.5666682092240574 | 56.7% |
| Runtime-gate plate recall | 24/33 = 0.7272727272727273 | 72.7% |
| Runtime-gate precision | 24/26 = 0.9230769230769231 | 92.3% |
| Image hit rate | 23/31 = 0.7419354838709677 | 74.2% |

There were nine unmatched labels and two unmatched predictions at the runtime
gate. Explicit polygon conversion reproduced the same standard and operational
results. Full per-image results/manifests stay in the ignored evaluation output;
only small aggregate provenance/metrics are checked into the application.

## 13–15. Definitions, negatives and recommendation

- **Standard precision/recall:** Ultralytics values at the confidence maximizing
  its smoothed mean-F1 curve on this split, with interpolation. They are not the
  app's fixed 50% confidence operating point.
- **mAP50:** area under the precision–recall curve at IoU 0.50; one plate class.
- **mAP50–95:** mean AP at ten IoU thresholds from 0.50 through 0.95 in 0.05 steps.
- **Runtime-gate recall:** uniquely matched labelled boxes / all labelled boxes,
  at confidence ≥0.50 and IoU ≥0.50.
- **Runtime-gate precision:** matched predictions / all retained predictions at
  the same gate. Duplicate predictions cannot double-count a labelled plate.
- **Image hit rate:** positive images with at least one correct match / all
  plate-present images. This is not general detector accuracy.

All 31 selected images have annotations; **zero annotation-negative images** and
no representative human-labelled no-plate set were supplied. General accuracy,
specificity and a general false-positive rate are not claimed. Positive-image
precision can still measure unmatched detections within these annotated images.

Recommendation: the detector transfers partially, but runtime recall of 72.7%
(nine missed labels) is below the prototype's 85% recall target. **Recommend future
fine-tuning with Singaporean training/development examples**, subject to explicit
approval and a larger independent evaluation. Preserve this test split for
evaluation; do not tune on it. These 31 images do not establish performance for
all Singaporean vehicles. No training/fine-tuning was run.

## 16. Model Performance evidence and reproducibility

A compact Singaporean transfer section shows runtime recall/counts and separate
best-F1 precision/recall, mAP50 and mAP50–95, with split/count/threshold definitions
and “Existing PlatePlus detector evaluated without Singaporean fine-tuning.”
Malaysian user-reported 93.1%, OCR 37/44, development 125/146 and synthetic origin
fixture evidence remain separate and unchanged. Missing/unverified SG evidence
is not rendered as verified. The read-only summary endpoint loads aggregate JSON;
it never performs inference. Package data includes that JSON for deployments.

Reproduce from the repository root with the existing environment:

```powershell
backend/.venv/Scripts/python.exe ml/scripts/evaluate_sg_detector.py `
  --dataset "SG License Plate.v2i.yolo26.zip" `
  --model models/trained/car_plate_yolo_best.pt `
  --output .plateplus-eval/sg-license-plates
```

The tool accepts a dataset ZIP/directory and local model path, prefers test then
valid/val, refuses to silently use training images, and writes reproducible JSON
with hashes and per-image matching. Its evaluation-only YAML deliberately has an
unusable training path. It never trains or runs OCR. The first Ultralytics call
unexpectedly downloaded its ~755 KB Arial plotting font despite plots being off;
subsequent confirmed runs disable that lookup and require no model/dependency
download. Existing weights were reused throughout.

## 17–21. Files, tests, build and harness

Changed/added implementation files:

- `.gitignore`
- `frontend/src/ModelPerformance.tsx`
- `frontend/src/PricingManagement.tsx`
- `frontend/src/PlatePlusSelect.tsx`
- `frontend/src/NetworkOverview.tsx`
- `frontend/src/locations.tsx`
- `frontend/src/styles.css`, `frontend/src/plateplus-select.css`
- `backend/app/services/demo_feed.py`
- `backend/app/services/traffic/pricing.py`
- `backend/app/services/detector_evidence.py`
- `backend/app/api/operations.py`, `backend/app/api/traffic.py`
- `backend/app/api/intelligence.py`, `backend/app/main.py`
- `backend/app/evidence/sg_detector.json`, `backend/pyproject.toml`
- `ml/scripts/evaluate_sg_detector.py`

Tests added/updated:

- `frontend/src/PresentationReliability.test.tsx`: body portal, scroll lock/focus,
  button/backdrop close, verified SG rendering, wide-menu geometry/full labels,
  keyboard/Escape behavior.
- `frontend/src/PricingManagement.test.tsx`: submitted 10/90 values, distinct visible
  results, no writes, stale-response suppression.
- `frontend/src/FeedStatus.test.tsx`: recovery, stale polling/auth status, HTTP 401
  control error visibility.
- `frontend/src/FeedPolling.test.tsx`: slow responses spanning multiple poll ticks,
  unchanged request deadline and old-scope cancellation/late-result rejection.
- `backend/tests/unit/test_demo_feed_lifecycle.py`: long virtual run, full-cycle
  failures/backoff/recovery, singleton pause/restart and interruptible retry.
- `backend/tests/unit/test_detector_evidence.py`: genuine evidence and absence/
  unverified handling.
- `backend/tests/integration/test_presentation_reliability.py`: actual pricing
  service/API 10/90 decisions, read-only counts/wallets, interval/cap explanation,
  input bounds/hundredths, feed diagnostic state and reset while stopping.
- `ml/tests/test_sg_evaluation.py`: safe extraction/split preference, archive
  preservation, polygon mapping, one-to-one matching, training-only refusal.

Final validation:

| Check | Result |
| --- | --- |
| Backend full suite | **169 passed**: 88 unit, 81 dedicated PostgreSQL integration |
| Final preview-validation regressions | **3 passed** after hundredth guard refinement |
| ML suite | **48 passed** |
| Frontend suite | **106 passed in 19 files** |
| Frontend production build | **Passed**; existing >500 KB bundle warning remains |
| New/rewritten Python Ruff checks | **Passed** |
| Git diff whitespace check | **Passed** |
| Actual browser checks | Modal bounds/scroll at all three sizes, full dropdown, real 10/90 previews, local feed controls; no physical camera access |

`.harnessV3/TODOLIST.md` records a dedicated completed Singaporean evaluation item,
all six work items, counts, exact metrics and recommendation. `AGENTS.md` adds only
the durable separate-transfer-evidence/protected-test rule. This report supplies
the detailed findings. Legacy harnesses and `main` are unchanged. Local frontend/
API remain available and the feed is paused; audited synthetic activity is retained.
