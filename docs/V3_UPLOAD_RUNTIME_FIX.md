# Simulator image-upload runtime recovery — 2026-10-09

## Final outcome: approved runtime repair verified

The user approved installation. Microsoft's signed x64 Visual C++ v14 installer
was downloaded from `https://aka.ms/vc14/vc_redist.x64.exe`; its Authenticode
signature was valid with a Microsoft Corporation publisher. Runtime version
**14.51.36247.0** installed, including `C:\Windows\System32\vcomp140.dll`.
The installer returned **3010** (success, reboot required); no reboot was performed.

With the original failing API's exact PATH, a fresh subprocess now imports Torch
and Paddle 3.2.2 successfully without any Codex DLL path or diagnostic preload.
Only the existing API was restarted, preserving its original normal-launcher
environment and all database data. Actual fictional ambiguous-plate upload then
returned HTTP 200/CORS, recognized `SBA1234A`, safely classified unknown origin,
and replayed the earlier RM0.00 rejection using the existing idempotency key.
`payment_duplicate=true`; no new debit was created. No physical webcam test or
user-image accuracy claim is made. Setup documentation now records this prerequisite.
Installation logs and API logs remain ignored under `.plateplus-demo/logs/`.

This resolves the normal-launcher runtime failure described below; the previous
successful Codex-environment check alone was insufficient.

## Follow-up: normal launcher still fails — confirmed root cause

After the user restarted from the normal launcher, uploads again returned the
readable OCR-unavailable response. The earlier successful API had inherited Codex's
extra runtime PATH directories; that result did not establish normal-launcher
recovery. The retained DLL-directory handles cannot supply a missing dependency.

The machine is missing **VCOMP140.DLL** from its normal 64-bit runtime search path.
PE import inspection shows Paddle's `mkldnn.dll` requires that Microsoft OpenMP DLL.
A fresh subprocess with the failing API's exact PATH reproduces the Paddle import
failure. With the identical PATH, preloading only an already-existing VCOMP140 DLL
from Codex's bundled Poppler runtime makes `import paddle` succeed. This isolates
the missing library; no DLL was copied, installed, or added to the application.

The durable remedy is install/repair of Microsoft's supported x64 Visual C++ v14
Redistributable, followed by API restart and normal-launcher verification. Official
source: https://learn.microsoft.com/en-us/cpp/windows/latest-supported-vc-redist
Installation initially awaited explicit user approval under `.harnessV3/AGENTS.md`
section 15; the approved repair and normal-launcher verification are recorded above.

## Observed failure

The running local API received Simulator upload requests, but returned HTTP 500.
The preserved `.plateplus-demo/logs/backend.err.log` traceback ends in
`ImportError: DLL load failed while importing libpaddle` during lazy PaddleOCR
construction. The unhandled error response lacked browser-readable CORS headers,
so the upload component displayed `NetworkError when attempting to fetch resource`.
This was an OCR runtime failure after a successful request, rather than a rejected
image format or a vehicle-payment failure.

Fresh processes using the same installed Torch/Paddle packages and cached models
initialized successfully even before the changes. The precise reason the old
server process could not resolve its DLLs was not independently reproduced.

## Changes

- The OCR adapter retains Windows DLL-directory handles for Paddle's installed
  `libs` and `base` directories, imports Torch then Paddle explicitly, and wraps
  native import/constructor load failures with runtime guidance. It does not
  change machine PATH, dependencies, weights, or OCR settings.
- Shared webcam/upload processing logs detector/OCR exceptions and converts them
  into `FrameProcessorError`. Existing endpoints return a readable HTTP 503 with
  CORS headers. OCR failures occur before toll processing, so no debit is created.
- Only the verified existing local API process was restarted. Original logs were
  preserved; new logs use `backend-upload-fix.*.log`. PostgreSQL, frontend, wallet
  balances and existing history were not reset. The feed remains paused.

## Verification

- Backend unit suite: **90 passed**, including two upload HTTP regressions for
  native DLL import and general OCR inference failures. Both assert HTTP 503,
  browser-readable CORS, a useful message and no call to payment processing.
- ML suite: **49 passed**, including retained DLL handles, failed construction,
  retry without duplicate registration, and original exception preservation.
- Fresh local inference recognized the existing fictional `VAA1234` fixture.
- The restarted real upload API processed the existing fictional `SBA1234A`
  fixture with **HTTP 200** and `Access-Control-Allow-Origin:
  http://localhost:5173`. It returned `ambiguous_plate_origin`, origin `unknown`,
  payment `low_confidence`, and **RM0.00**, with no successful debit. This request
  created a simulated rejection record using a dedicated idempotency key.
- No new browser UI verification, PostgreSQL integration suite, or physical
  webcam check was run. The user's actual image was not separately supplied;
  verification used existing fictional fixtures, not a new accuracy dataset.

No packages/models were installed or downloaded; no training, commit, push or
deployment occurred. Hardware webcam verification remains explicitly deferred.
