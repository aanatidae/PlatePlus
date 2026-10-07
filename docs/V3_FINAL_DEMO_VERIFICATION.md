# V3 final localhost demo verification

Verified on 7 October 2026 on `feature/sgimplementation`. All section Y checks
other than physical webcam capture/inference are complete. The user explicitly
requested **“Leave physical webcam verification pending”** during this run.
The camera permission attempt was closed without granting permission. Webcam
session/frame API verification below does not replace the deferred hardware check.

## Startup and persistence

The existing one-command launcher successfully started/reused Docker PostgreSQL,
applied migrations, seeded synthetic data, started FastAPI/Vite, and started the
normal-location feed. The database reports head `20261007_0014`. Local administrator
sign-in worked in the actual browser. Repeating seed preserved all entity counts
and every existing wallet balance. No operational data was reset.

All Locations shows LDP, AKLEH, NPE and Grand Saga, with Simulator Toll Plaza
separate. Actual generated activity appeared at the four normal locations only.
The feed was paused for isolated optical, replay, seed and Prediction checks and
remains paused after verification; use Start Live Feed for a presentation.

## Real local optical and payment checks

Fictional plate/vehicle scenes were drawn as software fixtures and passed through
the actual local YOLO/PaddleOCR HTTP endpoints. No inference response was mocked.
The cached models were reused; no models or dependencies were installed/downloaded.

| Fixture | Input | Result |
| --- | --- | --- |
| VAA1234 | Uploaded image | Malaysian; successful RM2.00 toll, zero foreign charge |
| GBC6427R | Uploaded image | Singaporean; successful RM2.00 toll + RM20.00 simulated foreign charge = RM22.00 |
| YN4821R | Uploaded image | Singaporean; insufficient funds, RM22.00 attempted total, no debit ledger entry |
| SBA1234A | Uploaded image | Ambiguous supported patterns; unknown origin, no successful deduction |
| XD7316E | Webcam session/frame API with fictional PNG | Singaporean; successful itemized RM22.00 simulated payment |

Each image event was replayed with the same idempotency key. Every replay returned
the original outcome, preserving all counts and wallet balances. Successful
payments had one ledger debit equal to the stored final total; rejected and
insufficient-balance outcomes had no debit. Uploading XD7316E immediately after its
webcam API frame exercised shared cooldown and produced no additional payment.
The API session was explicitly stopped with HTTP 204.

These are selected synthetic optical smoke examples, **not** a new OCR/origin
accuracy benchmark or legal registration validation. The existing protected OCR
held-out manifest and evaluation evidence were not changed.

The actual browser file chooser/upload flow also recognized GBC6427R and XD7316E
and displayed successful, separately itemized RM2.00/RM20.00/RM22.00 results. The
browser used the running local API and database, without intercepted responses.
The generated fixtures are intentionally retained as local QA assets; application
raw-image retention remains off. Audited simulated payments/history are retained,
so subsequent demonstrations must use current balances, not initial seed balances.

## Simulator, pricing and Prediction

Four accepted crossings (including the insufficient-balance crossing) yielded
40% congestion at capacity 10. After 63 real seconds without further local input,
active crossings and congestion were zero while last-crossing history remained.
Unknown origin was excluded; average speed remained unavailable.

Read-only pricing decisions using the current persisted four-band rules increased
between Normal and Severe for each normal location. Existing automated tests
verified the floor, cap, interval and hysteresis. The actual AKLEH UI preview at
67% showed Peak hour, RM2.40 × 2.00 = RM4.80. The Simulator explanation showed
actual crossing-derived congestion and RM2.00 × 1.00; both explicitly kept the
foreign charge outside congestion pricing. No policy or safeguard was changed.

The browser completed a 12-hour, 145-frame AKLEH prediction at 4× playback, from
7 October 23:00 to 8 October 11:00 Malaysia time. The date rolled over correctly
and playback stopped at frame 145. Database counts and every wallet exactly
matched the snapshot before playback. Simulator was excluded. Model Performance
opened with the documented evidence and closed with Escape.

## Presentation correction and evidence

Final compact-browser inspection found top-bar overflow between the desktop and
mobile breakpoints. The top bar now wraps at 821–1100px and allows the location
control to shrink. This keeps sign-out and other actions reachable. No navigation,
data behavior, model, pricing policy, or payment implementation was changed.

Local evidence lives in the ignored `.plateplus-demo/qa-y/` directory:

- `api-results.json`: actual optical outcomes, replay/ledger checks, head/seed
  evidence, real Simulator expiry and Prediction database invariance.
- `model-performance.jpg`, `pricing.jpg`, `prediction-complete.jpg`,
  `singaporean-upload.jpg` and final network/Simulator screenshots: real UI evidence.
- Fictional PNG fixtures for the optical smoke flow.

The runtime code/dependency review found no bank/eWallet/payment-provider or
government/owner-query integration. Origin-module government URLs are documentation
references, not requests. All records and displayed operations remain simulated.

## Verification and practical limits

- Backend: **160 passed**, including 78 dedicated PostgreSQL integration tests.
- ML: **40 passed**.
- Frontend: **94 passed**; production build passed.
- New verification script: Ruff and Python syntax checks passed.
- Existing production bundle warning (>500 kB) remains.

Initial cold local model/OCR loading exceeded a 90-second client probe timeout.
The request finished and its replay returned the original payment without another
debit. Subsequent cached inference completed normally. Warm the local model with
a deliberate fictional-image submission before presenting; use its idempotency
key to retry a timed-out API submission. No cold-start speed guarantee is claimed.

The persisted traffic scheduler is disabled and the launcher does not start its
separate process. LDP's old persisted traffic is correctly shown as stale even
while the presentation feed runs. This existing state is preserved and explicitly
reported; the feed follows congestion and does not manufacture traffic telemetry.
Use the documented scheduler/manual simulation when a demonstration requires
fresh persisted network traffic. No settings were silently enabled or reset.

Reproduce the operator smoke check with the feed paused, sufficient synthetic
balances, the API running, and existing local weights/OCR assets:

```powershell
cd backend
.\.venv\Scripts\python.exe ..\scripts\verify_v3_local_demo.py --create-demo-events
```

This explicitly creates simulated payments/history and waits for real expiry;
it never resets wallets/history or requests camera access. It requires the local
development database, uses localhost only, and refuses a running presentation feed.
Physical webcam verification remains the sole deferred Y item. No commit, push,
merge, deployment, dependency/model installation or training was performed.
