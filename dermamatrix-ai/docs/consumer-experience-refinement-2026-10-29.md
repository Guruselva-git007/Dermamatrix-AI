# User-centred frontend refinement — 29 October 2026

This bounded development pass follows the completed CSS polish. The owner
explicitly requested further frontend/UX optimization from the user's perspective
and allowed internet design research. It preserves English, Achromatic ledger
(seed 1478287822), self-hosted IBM Plex, the existing Flask/vanilla JS architecture,
medical evidence, immutable history, account boundaries and disabled providers.
No deployment, classifier, training, schema change or raw-photo retention.

## Design sources and decisions

The app remains a tool for completing a check, understanding its limits and
reopening useful information. It does not need decorative medical imagery or a
new brand to do these jobs well. No external template, font, script or asset was
copied into the application.

- [NHS cards](https://service-manual.nhs.uk/design-system/components/card): group
  related actions; long-form reading should not become a wall of cards. Applied
  as a focused guide reader with a comfortable text measure.
- [NHS buttons](https://service-manual.nhs.uk/design-system/components/buttons):
  make actions explicit and keep them easy to press. Applied to clear photo/file
  actions beside the upload control and reachable reading controls.
- [GOV.UK details](https://design-system.service.gov.uk/components/details/):
  optional detail can be disclosed, while information most people need stays
  visible. Photo preparation remains optional; consent, limits, uncertainty and
  medical warnings stay visible and results retain all original content.
- [Web Interface Guidelines](https://github.com/vercel-labs/web-interface-guidelines/blob/main/command.md):
  preserve focus, label controls, show local recovery feedback and prevent long
  content escaping its container. Used as review guidance, subordinate to this
  project's saved medical/content/visual constraints.

## Reproduced problems and implementation

| Priority / observed behaviour | Consumer impact | Implemented correction | Verification |
| --- | --- | --- | --- |
| P2 — Learn appends the opened article after all 17 catalogue topics and offers no Back action | Reading and browsing compete; returning to the same matches requires scrolling | Separate reader state with Back to guides; keep query/category/list in memory; focus the guide title; readable article width and section rhythm | Browser checks verify preserved filtered matches, correct focus and reading layout |
| P2 — Guide fetch failures expose only a generic error; stale responses can arrive after leaving the page | Recovery is unclear; an old request must not take over the next task | Opening/loading/count feedback, local retry, request invalidation on close/account clearing, no late focus on another route | Interrupted read/retry and delayed-response browser checks; three new source-executing unit regressions |
| P2 — Native WebKit clicks need not focus their button | Back initially returned to search instead of the clicked guide | Capture the actual invoking Read guide button explicitly and retain it through retries | Reproduced in the first WebKit regression, then retested with the same assertion |
| P2 — Camera/gallery actions are inside Prepare a useful photo | An existing input method is difficult to discover | Surface Choose photo and Take photo together beside the native file input; keep full preparation guidance available | Visible-control, capture-intent, no-consent/no-submission browser checks; actual physical camera remains external |
| P2 — Routine notes render at 10px in retired DM Sans | Entered text is hard to read and visually inconsistent | Restore 16px IBM Plex field typography across routine, check-in, profile and optional assessment notes | Computed font verification and responsive screenshots |
| P2 — Long result sections require manual scrolling; Close scrolls out with the initial content | Users lose their place or have to scroll back to dismiss the report | Result contents controls, focused section jumps, explicit technical disclosure, Back to overview and persistent Close | Browser focus/disclosure/dismissal checks and a presentation-only long-result fixture |

The content is never truncated to make a screen shorter. Reader mode hides the
catalogue while an article is open; Back restores the existing list and filters.
It creates no new guide store or competing medical record. Public guide text
still comes from the existing knowledge API; account-owned bookmarks use the
existing continuity service. Sign-out invalidates outstanding guide requests,
clears the reader and removes its account-specific controls.

Result contents are derived from the sections the current result actually has.
They do not manufacture missing care advice or evidence. Urgent warnings remain
first. The normal result, four explanations, uncertainty, research/model limits,
care, sources, technical evidence and report/export paths remain intact.

## Files and evidence

- `frontend/engagement.js`: guide reader lifecycle, focus and recovery.
- `frontend/continuity.js`: bookmark placement, capture controls and result
  presentation callback. Existing writes and canonical explanations are unchanged.
- `frontend/workspace.js`: navigation over existing result sections.
- `frontend/product.css`: readable notes, reader layout and result/capture controls.
- Existing lifecycle tests and product-quality browser suite extended; no new
  framework, provider, production test hook or duplicate runner.
- `frontend/tests/run_browser_regressions.py`: expects the expanded 16-check
  product-quality suite alongside the original suites.

Private evidence lives under `local-artifacts/consumer-experience-2026-10-29/` at
project root: starting Git state/source hashes, baseline and final screenshots,
actual synthetic workflow receipts, request-failure probes, unit and browser
logs, protection/cleanup receipts and final Git/CI identities.

The long image-result visual probe reuses the existing result-contract unit
fixture. It is labelled synthetic, performs no model inference, stores nothing
and asserts section navigation preserves all original displayed evidence text.
It supplements actual questionnaire/account/continuity workflows; it is not a
clinical assessment or a new model result.

## Quality review and limits

| Review dimension | Disposition in inspected scope |
| --- | --- |
| Typography | Legacy tiny notes fixed; IBM Plex retained; reader line length and wrapping checked |
| Layout | Catalogue and article separated; result destinations and Close reachable |
| Hierarchy | Guide title focused; medical warnings remain first; primary result still leads |
| Spacing | Reader sections grouped; toolbar actions align rather than stretching across the column |
| Consistency | Shared fields, buttons, type and palette retained; no external template introduced |
| Responsiveness | Four widths, both themes and enlarged reader text checked; physical touch remains unverified |
| Accessibility | Names/focus/keyboard/recovery/target checks pass in the sampled flows; actual speech and full certification unverified |

These are engineering observations; no participant study, satisfaction score or
screen-reader speech was fabricated.

A native file-chooser event pauses a Playwright CLI run-code cell before it can
emit JSON. The first attempted automation therefore produced an empty result
and is not counted as a pass. The corrected browser test intercepts the native
input's click handoff only in the test context, verifies camera/gallery intent,
and checks no assessment POST or consent occurs. Physical camera/gallery/native
picker acceptance remains governed by `consumer-device-checks.md`.

Local verification:

- **77 frontend tests pass**, including three new delayed-guide/cancellation/
  account-clearing regressions.
- **59 browser checks pass in Chrome and 59 in WebKit**: original core,
  continuity, accessibility and actual origin outage/recovery, plus the expanded
  16-check product-quality suite. This local run precedes only the final toolbar
  width correction and its extra assertion; eight final reader samples cover
  that CSS adjustment. Final-source CI below is authoritative for the whole tree.
- **56 route samples** cover seven routes at 320/390/768/1440px in both themes;
  eight additional final reader samples verify focus, readable width and 44px
  actions. No page overflow or uncaught JS errors in these successful samples.
- **200% computed-text simulation at 320px** preserves the reader without
  horizontal page overflow. This is not native zoom or OS text scaling.
- A **9022px synthetic long-result fixture** exposes all five applicable section
  destinations and preserves all evidence text after jumping through them.
- Source hashes confirm **all backend Python, `frontend/app.js` and
  `frontend/index.html` remain byte-identical** to the baseline. No normal
  database schema/migration, model, provider or deployment change occurred.
- Source lint has no failures; inherited app-pattern warnings (quiet rules,
  overlays and existing labels) are reviewed in the product context. No generic
  heuristic score is claimed as a consumer/accessibility outcome.

An early visual harness timed out on the guide catalogue while another browser
suite was active. A later direct catalogue request succeeded and the isolated
visual rerun passed; the first attempt remains recorded and is not a pass.
Interim CI runs were cancelled when their known test-harness or focus fixes
superseded them. No assertion was removed to hide a product failure.

Final [development CI 40774346102](https://github.com/Guruselva-git007/Dermamatrix-AI/actions/runs/40774346102)
**passes exact source `5f77bc58ef05491c7b010bb34b6aa0b963ac9e4f`**:
**258 backend tests, 77 frontend tests, 177 browser checks (59 each Chrome,
Firefox and WebKit)**. Synthetic migrations, source hygiene and the pinned
package audit also pass; the audited dependency environment reports no known
vulnerabilities. This is not an attestation of the unmerged default branch,
clinical validity or deployment readiness. The existing nonblocking GitHub
Actions runtime-deprecation annotation remains outside this frontend scope.

Runtime progress is committed in `7bd25c8`, `8c5181d`, `3b6969f`, `5f77bc5`.
Closing documentation follows the exact green source. Temporary local app8001,
MySQL3308, own browser and test user are closed; the normal service8000 serves
all four changed frontend assets without a restart. Final Git/remote equality,
archive refresh and sleep-hold release are recorded in the private completion
receipt. This selected batch is complete; no reproduced unresolved P0/P1 defect
was found in its affected workflows.

Remaining external checks: physical Samsung/iPhone where available, actual
VoiceOver/TalkBack speech, native Safari picker/zoom acceptance and representative
consumer sessions. Next development changes should follow demonstrated issues
from those checks. Provider activation and deployment remain deferred.
