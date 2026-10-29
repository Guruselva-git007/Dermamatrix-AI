# Consumer validation and accessibility — current development batch

## Native desktop acceptance continuation — 29 October 2026

Baseline `db2f2a8eaa331bce2df3ed09458fbe71139c1a7c` on
`codex/consumer-evolution`; unchanged runtime previously verified by CI
40774346102 (258 backend / 77 frontend / 177 browser checks). This continuation
uses **actual Safari 27.2**, not automated WebKit. One worker, existing synthetic
database on loopback3308/app8001, a restricted temporary database user and disabled
mail. Two disposable accounts were prepared; no normal account data was opened.

| Case | Actual observation | Disposition |
|---|---|---|
| SA-01 Account sign-in | Synthetic A signs in; Today shows its one questionnaire result and one routine. Password saving declined. | VERIFIED TESTED |
| SA-02 Saved result | Reopens correct concern, questionnaire limitations and evidence; Technical details expands; return/Close works. | VERIFIED TESTED |
| SA-03 Brief validation/preview | Missing dates produce an actionable rejection. Native keyboard date entry and explicit concern selection produce exactly one included assessment and truthful missing-photo/research notices. | VERIFIED TESTED |
| SA-04 PDF saving | Correct PDF reaches native Save panel and private project destination. Save stays disabled through the control surface; keyboard attempt does not complete it. Cancelled. | OWNER INTERACTION REQUIRED; no saved-file pass |
| SA-05 Routine/check-in | Routine shortcut selects its routine; review/Escape works; native Option-Tab/Return saves one synthetic check-in. Native UI shows self-reported trend and Saved. Notes-field preservation was not established. | VERIFIED TESTED for stated scope |
| SA-06 Correction | Visible correction dialog opens, but its fields are omitted from this native AX surface. Escape cancels and leaves the record. | OWNER INTERACTION REQUIRED; no correction/speech pass |
| SA-07 JSON saving | Correct dated account JSON reaches native Save; same disabled Save behavior as PDF. Cancelled. | OWNER INTERACTION REQUIRED; no saved-file pass |
| SA-08 Sign-out | Account entry returns with signed-out message and cleared private workspace. | VERIFIED TESTED |
| SA-09 Account switch | Synthetic B has its own identity, no Today assessments and zero Journey matches; A's concern/result/routine are absent from these views. | VERIFIED TESTED |
| SA-10 Native navigation | Safari Back returns Today, Forward returns Journey, refresh retains B and its empty Journey. | VERIFIED TESTED |
| SA-11 Zoom | Native site settings confirm 200%; responsive navigation appears. Limited screenshot/paint output prevents full reflow acceptance. Original100% restored and confirmed. | PARTIAL; full visual/keyboard acceptance remains pending |
| SA-12 Photo picker | Choose photo opens native panel. Generated PNG selected; PNG/HEIC eligible and text fixture disabled. Upload stays disabled; exposed Open action has no effect. Cancel returns to Skin with consent off and Review disabled. | PARTIAL; completed selection/replacement remains pending |

**Seven scoped scenarios verified, five partial/owner-dependent.** These are
native acceptance observations, not seven new automated regression tests. A
ScreenCaptureKit capture failure followed the check-in confirmation; subsequent
native UI and synthetic SQL both confirmed the saved record. It was not retried
as another save. Initial URL/input control failures and unavailable dialog fields
were not counted as product defects or successful input-preservation tests.

Synthetic SQL corroboration: A has exactly one assessment, one routine and one
check-in; B has zero of all three. All **130 baseline production source files**
(Python/JavaScript/CSS/HTML) remain byte-identical. No app correction was justified;
no tests/frameworks were added. Unchanged automated suites were not rerun. The
prior exact-source CI receipt above remains the regression evidence. No model,
scoring, schema, provider, retention, consent or historical-evidence change.

### Samsung interaction and owner steering

USB inventory identified `SAMSUNG_Android`. Owner enabled USB debugging; Chrome's
owner-supplied screenshots showed Offline / Pending authentication. Reconnection
did not establish authorization. The browser policy rejected agent access to
`chrome://inspect`; no alternate surface/raw CDP workaround or ADB installation
was used. The owner supplied observations instead. Consulted the official
[Chrome troubleshooting procedure](https://developer.chrome.com/docs/devtools/remote-debugging/)
for the missing approval prompt. A suggested authorization reset was **not
confirmed performed**.

The owner then explicitly requested **leave the phone test and finish remaining
work without the phone**. Stop phone setup/testing and do not restart it on
continuation unless requested. No USB port forwarding was configured by this
task, no phone app journey was completed and no physical acceptance is claimed.
No unattended hardware probes continue. Owner-controlled USB debugging settings
were not silently changed back.

### Resume boundary and closure

No confirmed application P0/P1 defect was reproduced in the independently
completed observations. Disabled native Save/Upload and omitted dialog AX fields
remain unresolved acceptance/tooling observations, not proven clean behavior.
Next owner-assisted native checks: complete picker selection/replacement, PDF
and JSON Save, correction dialog, notes preservation, full zoom and actual
VoiceOver speech. Existing TalkBack/physical iPhone/consumer-study checks remain
pending; phone testing is expressly deferred. Reuse the existing protocol rather
than creating another study or repeating verified cases.

Private evidence: `local-artifacts/device-acceptance-2026-10-29/` at project root.
Normal8000 readiness and four current frontend assets verified. The normal app
was opened in primary Chrome at account entry for desktop use. Synthetic B was
signed out; task Safari tab closed and original Start Page preserved. Owned test
app/database/user and sleep hold are closed at final receipt; synthetic fixture
rows remain available for a later explicitly requested session. No deployment,
public tunnel, provider activation or physical/speech certification.

This is a documentation-only batch. Task-owned documentation is committed and
pushed separately; final identities/cleanup are recorded in the canonical
checkpoint and ignored completion receipt. CI need not repeat unchanged runtime
suites for these Markdown-only changes.

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
| CV-02 — P2 | `frontend/assessment-review.js:19`: at 390×844, review focused Confirm, `scrollTop=143`, title top −100px while dialog began at 20px. | The explanation began off-screen. Focus the review heading (`tabindex=-1`) when opening; explicitly return to the review button after cancellation because a Mac mouse click need not focus it. Clear the return target on workspace reset; preserve native keyboard order and explicit confirmation. No automatic submit or changed medical content. | At 390×844 and 320×600, heading top 43px, `scrollTop=0`, no dialog horizontal overflow; Back/Confirm reachable, Escape restores opener and draft. Actual Safari visibly focuses heading; Option-Tab reaches Back/Confirm and Return completes the guest questionnaire. Final actual Safari Escape visibly restores Review questionnaire; speech unverified. |
| CV-03 — P2 | `frontend/app.js` mobile drawer focus lifecycle: open at 320px left focus on body during visibility transition; closing could blur the drawer child when made inert before checking the return target. | Keyboard users lost their position. Focus the selected link after visibility updates, with a guarded transition callback; capture return-focus intent before inert changes. Preserve native layout/animation and account isolation. | Two source-executing regressions simulate immediate inert blur and cancelled deferred focus; browser check requires focus inside drawer, named dialog, Escape and restored trigger. No speculative redesign. |

The first CI `40746936098` passed 256 backend/74 frontend, all 53 checks each
in Chrome/Firefox and the existing 37 WebKit workflows, then failed the new
WebKit result wait. Focused local WebKit reproduced differing native traversal
and Escape returning to the workspace heading. The test accepts Safari's native
Option-Tab path (still requiring Back then Confirm); the product now explicitly
restores the invoking review button after cancellation. Final local WebKit12/12
passes; complete CI was rerun on that source. No failed result assertion
was skipped or counted as passed.

Second CI `40748488611` supplied the actual result-wait cause: the new WebKit
assessment reached the shared loopback IP's unchanged 20-attempt/300-second
quota. It had already passed the first ten accessibility checks. Added explicit
synthetic technical-budget fixture resets between engines in the existing runner:
only `request_budgets` is cleared, guarded by test environment, `*_synthetic`
database and disabled mail; application limits and medical history remain intact.
Two reset guard/scope tests pass (12 focused runner tests total). Final CI with fixture isolation passes all 159 browser checks; no production
throttle was raised or disabled.

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
Final exact source `e8fd5852301c150bd96d39bfc4af378d2f8de9fc` passed
[CI 40749855922](https://github.com/Guruselva-git007/Dermamatrix-AI/actions/runs/40749855922):
258 backend, 74 frontend and 159 browser checks (53 each Chrome/Firefox/WebKit),
explicit synthetic migrations, source hygiene and the pinned advisory gate.
No advisory or failed check was suppressed. Existing connected
checks exercise assessments, account switches, routines, immutable corrections,
concerns/check-ins, bookmarks/search, brief/report downloads, interrupted saves
and deduplication. Backend tests retain historical zero/one/many/unassigned cases,
privacy/consent/ownership/no-photo and canonical evidence contracts.

Protection verification: all production backend files, model/scoring/contract/schema files,
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
