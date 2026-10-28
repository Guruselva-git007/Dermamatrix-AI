# Consumer validation and accessibility — current development batch

Baseline: `codex/consumer-evolution`, documentation head
`b95fee4d11230238e02665a74f53f1f63961f52a`. Prior exact green test commit
`cf0c6a7a2a62179eed44c4793b0f914c08d74c46`, CI
[40736195397](https://github.com/Guruselva-git007/Dermamatrix-AI/actions/runs/40736195397):
256 backend, 72 frontend and 41 checks in each of Chrome/Firefox/WebKit. Completed
A–L and previous product maturity work were preserved. Existing suites were reused;
only a targeted accessibility suite was added to the existing sequential runner.

## Track A: implemented corrections

| ID / severity | Original observation and reproduction | Consumer impact / minimal correction | Verification and limit |
|---|---|---|---|
| CV-01 — P1 | `frontend/index.html:108`: chooser accepted JPEG/PNG/WEBP/AVIF only, while existing client/server support HEIC/HEIF. Inspect `#imageInput.accept` and its format hint. | Supported gallery formats could be filtered out or appear unsupported. Added HEIC/HEIF MIME types/extensions to the chooser and aligned the visible limit/format hint. Decoder, limits, consent and inference unchanged. | Targeted browser assertion; generated 490-byte HEIC selected through browser automation, reported `SERVER_DECODE_REQUIRED`, with zero assessment requests before consent; existing three HEIF decode/rejection/size tests pass. Native Safari panel listed HEIC as eligible but would not complete Upload for PNG either: owner check remains. Physical phone capture is untested. |
| CV-02 — P2 | `frontend/assessment-review.js:19`: at 390×844, review focused Confirm, `scrollTop=143`, title top −100px while dialog began at 20px. | The explanation began off-screen. Focus the review heading (`tabindex=-1`) when opening, then retain native keyboard order and explicit confirmation. No automatic submit or changed medical content. | At 390×844 and 320×600, heading top 43px, `scrollTop=0`, no dialog horizontal overflow; Back/Confirm reachable, Escape restores opener and draft. Actual Safari visibly focuses heading; Option-Tab reaches Back/Confirm and Return completes the guest questionnaire. Speech unverified. |
| CV-03 — P2 | `frontend/app.js` mobile drawer focus lifecycle: open at 320px left focus on body during visibility transition; closing could blur the drawer child when made inert before checking the return target. | Keyboard users lost their position. Focus the selected link after visibility updates, with a guarded transition callback; capture return-focus intent before inert changes. Preserve native layout/animation and account isolation. | Two source-executing regressions simulate immediate inert blur and cancelled deferred focus; browser check requires focus inside drawer, named dialog, Escape and restored trigger. No speculative redesign. |

Earlier failed local probes are retained privately. Two were harness setup issues:
reusing a same-document navigation and trying a desktop-only sidebar link at a
mobile width. The drawer checks additionally wait for actual visibility, rather
than taking a snapshot during its transition. Only completed final checks count.

## Track A: verification matrix

| Environment / scope | Actual result | Evidence status |
|---|---|---|
| Current source and ownership/privacy boundaries | Only three product frontend files changed: chooser hint/accept, review focus and drawer focus; no persistence, scoring, models, canonical contract, consent service, retention, reports or provider changes | VERIFIED TESTED by scoped diff/hash checks; final receipt in checkpoint |
| Focused frontend | 74/74 pass, including two new focus regressions | VERIFIED TESTED |
| Existing HEIF boundary tests | 3/3 pass (valid decode, malformed/mislabeled rejection, pixel limit) | VERIFIED TESTED; no physical-device inference |
| Targeted Chrome accessibility | 12 checks pass: identity/zoom allowance, auth names/errors, seven route headings/labels, upload naming/formats, consent feedback, review viewport/focus, draft preservation, drawer keyboard, reduced motion, result meaning and guest reload | VERIFIED TESTED; targeted DOM/keyboard checks, not a full automated WCAG scan |
| Actual macOS Safari 27.2 | New task tab: guest onboarding, four input choices, missing-consent error, review, Escape, keyboard questionnaire completion, truthful guest result, refresh to account entry; final heading-first focus and Option-Tab confirmation inspected | VERIFIED TESTED for these sampled guest interactions only; full signed-in Safari/report suite not claimed |
| Safari native upload panel | Generated HEIC eligible; Upload disabled under automation for HEIC and PNG control; native coordinate attempt returned `noWindowsAvailable`; cancelled cleanly | Native upload completion NOT TESTED — OWNER INTERACTION REQUIRED; no confirmed HEIC-specific app defect inferred |
| Safari zoom | Actual site popover confirmed 200% and 300%, its maximum offered; auth inspected after reload; restored original 100%. Some live layout paints/modal AX trees were inconsistent through tool | Partial observation; full zoom/keyboard acceptance and 400% NOT VERIFIED |
| VoiceOver/TalkBack | Tool can read some accessibility output, but actual speech could not be observed | NOT TESTED — OWNER INTERACTION REQUIRED; no spoken output fabricated |
| Samsung/iPhone | No phone in USB inventory; adb absent. No hardware repeatedly probed or installed for convenience | NOT TESTED — DEVICE UNAVAILABLE |
| Consumer study | Introduction/consent script, six non-leading tasks, success criteria, timing/error/hesitation notes, triage and summary templates completed | VERIFIED IMPLEMENTED protocol; NOT TESTED — HUMAN PARTICIPANTS REQUIRED |

Actual Safari is distinct from automated WebKit. The native accessibility tree
omitted review/result modal contents despite a visible operable dialog and named
DOM snapshots in automated browsers. This unresolved observation needs real
VoiceOver verification; it is neither a speech pass nor proof of an app defect.
The task Safari tab was closed, original Start Page preserved, zoom restored and
remote automation/security/extension permissions left unchanged.

## Regression receipt and protected functionality

The new 12-check suite runs in the existing isolated three-engine CI runner after
the existing 37 connected checks, with real origin-outage checks still separate.
Final exact CI/commit status is recorded in `ROADMAP_EXECUTION_STATUS.md`.
No full-suite pass is claimed until that receipt is present. Existing connected
checks exercise assessments, account switches, routines, immutable corrections,
concerns/check-ins, bookmarks/search, brief/report downloads, interrupted saves
and deduplication. Backend tests retain historical zero/one/many/unassigned cases,
privacy/consent/ownership/no-photo and canonical evidence contracts.

Protection verification: all backend files, model/scoring/contract/schema files,
service worker, IBM Plex assets and CSS layers remain unchanged. Frontend diffs
are limited to the three corrections listed above. No provider activated, new
model inferred/trained, historical evidence rewritten, personal photo used,
erasure executed, public origin exposed or deployment performed. A synthetic
fixture selection is not medical validation or native mobile capture evidence.

## Track B: exact next action

Follow [device and native speech steps](consumer-device-checks.md). Connect the
Samsung and approve its own USB prompt; ask the developer to restart the existing
isolated stack for the device session, then use Chrome USB forwarding. Complete
the short Safari chooser and VoiceOver checks. Run the six-task protocol in
[consumer validation](consumer-validation-protocol.md) when real participants can
attend. Clinical/operator/retention/erasure policy decisions remain BLOCKED —
OWNER/POLICY DECISION REQUIRED. Provider choice and deployment stay deferred.

Stop this batch after available corrections/regressions, documentation, scoped
push and owned-resource cleanup. New refinements should follow actual device or
participant findings, not cosmetic speculation.
