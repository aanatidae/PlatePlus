# W/X accessibility and documentation completion

Completed on 2026-10-07. W verifies responsive presentation and local-result UX;
X reconciles the V3 documentation with code and preserved evaluation evidence.
This is focused regression evidence, not a complete WCAG certification or a
physical camera/model benchmark. Section Y remains the final localhost demo.

## W: changes and evidence

- Fixed clipping of the Grand Saga marker at compact viewport edges and separated
  adjacent marker labels. The schematic route identities remain unchanged.
- Upload messages wrap instead of one-line ellipsis truncation. The shared ALPR
  details render recognition status and the full response message alongside text
  origin labels and stored charge components.
- Input controls no longer stretch into an oversized camera button beside a
  narrow upload column. Camera height is viewport-bounded; its result area scrolls,
  accepts keyboard focus and exposes a visible focus outline. Camera status uses
  a polite status announcement.
- Existing visible focus, text congestion/origin states, reduced-motion rules,
  selector keyboard behavior and definition-list charge semantics are retained.

Installed Edge with the existing bundled Playwright runtime verified these CSS
viewport sizes: **1280×720**, **1366×768**, **1920×1080**, **1024×768**, **390×844**,
and **960×540**. The final small viewport checks reflow at a reduced CSS viewport;
it is not a claim of testing every browser's native zoom behavior.

Each viewport checks five contained, non-overlapping marker hitboxes, no document
horizontal overflow, keyboard-only selector selection, bounded/scrollable camera
results, separate SG charges and full unknown-origin rejection text. A synthetic
canvas stream supplies camera video, and intercepted API responses supply outcomes.
No physical device permission, real model inference or database write occurs.
Page JavaScript errors are asserted absent. Map, upload, rejection and camera
screenshots were reviewed; generated evidence is stored locally under the ignored
`.plateplus-demo/qa-w/` directory with `results.json`.

Reproduce after starting the frontend with approval, using an existing Playwright
installation (set `NODE_PATH` to its package directory if needed):

```powershell
node scripts/verify_v3_accessibility.cjs
```

`PLATEPLUS_BROWSER_CHANNEL` defaults to installed `msedge` and can select an
installed Chrome channel; `PLATEPLUS_PLAYWRIGHT` can point to an existing package.
`PLATEPLUS_QA_OUTPUT` overrides the local evidence directory. No install is performed.

Frontend unit/component verification: **94 tests passed in 16 files**, including
four new full-message cases for rejection, low confidence, duplicate and error.
Production build passed with the existing >500 kB bundle warning. Documentation
links/schema descriptions, script syntax and `git diff --check` were checked.
The React accessibility review covered shared component semantics, focus behavior,
unchanged hooks/data boundaries and the existing TypeScript build.

## X: reconciled references

| Requirement | Documentation |
| --- | --- |
| MY/SG pattern scope and flat-rate-only scope | README, PLATE_ORIGIN.md, FLAT_RATE_SCOPE.md |
| Current normal network plus separate Simulator | README, MULTI_LOCATION.md, ARCHITECTURE.md |
| SG seed examples, preserved balances and configurable fee | SETUP.md, FOREIGN_VEHICLE_CHARGE.md, DEMO.md |
| Origin metadata, charge components, ledger and migration ownership | DATABASE_SCHEMA.md |
| Authenticated read/write contracts and local result fields | API.md |
| Separate fixture confusion matrix, protected OCR set and latest checks | TESTING_EVALUATION.md, V3_TESTING_COMPLETION.md |
| Current pipeline and local/deployed boundaries | ARCHITECTURE.md with Mermaid flow diagram |
| MY/SG demonstration and accessibility controls | DEMO.md |

All references retain explicit synthetic traffic/payment/owner data, ephemeral raw
inputs, no government/owner/bank/eWallet integration, and origin-as-pattern-only
wording. No new model metric is claimed. Legacy harness files remain unchanged.
No commit, push or deployment was performed for this slice. Only the frontend
service was started for W with user approval; the test service was already approved
in T/U/V. Physical webcam verification remains deferred.
