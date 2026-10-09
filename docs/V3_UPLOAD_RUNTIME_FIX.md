# Simulator image-upload runtime recovery — 2026-10-09

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
