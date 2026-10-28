# Consumer validation still requiring people/devices

No participants, interviews, clinical reviews or physical-phone outcomes are
claimed by this development work. Browser mobile viewports are emulation.

## Usability sessions

Recruit 5–8 consenting representative participants after the intended audience
and appropriate research/clinical boundaries are approved. Use synthetic cases
and avoid collecting unnecessary health histories or identifiable recordings.
Explain that the session tests software usability, not diagnostic accuracy.

Ask each participant to: explain what the app can/cannot do; explore as guest;
create/recover a test account; choose the correct input route; recover from a bad
upload; review and consent; explain an uncertain/model-unavailable result; create
and pause a routine; record Done/Skip and a check-in; locate an old report; find a
sourced guide; export test data; pause new processing; and record a rights request.

Record task completion without help, mistakes, recovery time, confusing wording,
result interpretation, privacy understanding and accessibility barriers. Capture
observations verbatim without inventing results. Prioritise recurring confusion
and any falsely reassuring/diagnostic interpretation. Re-test changes. These
small sessions do not establish population performance or clinical validity.

## Device/assistive-technology matrix

| Environment | Required checks | Evidence state |
|---|---|---|
| Real Android phone / Chrome or Samsung Internet | Camera/gallery, orientation, large photos, native sharing/downloads, keyboard, interruptions, notification handoff | Not physically verified |
| Real iPhone / Safari | HEIC selection, camera permission, gallery, downloads, standalone installation and resumed sessions | Not physically verified |
| Desktop Chrome | Onboarding, security, routines, history, Learn, review dialog, mobile emulation, keyboard/zoom, offline boundary | Development browser evidence; see execution status |
| Desktop Firefox | Complete flows, deep links, focus and download behaviour | 41 Linux CI checks pass, including actual origin outage/recovery. Local Mac test runtime fails before app launch; physical network disruptions remain distinct checks |
| Desktop WebKit development browser | Same workflows plus real service-worker/offline boundary | 41 checks pass locally and in Linux CI, including worker/cache/origin-outage recovery. This is not actual Safari/iPhone verification |
| Actual desktop Safari application | Complete flows, focus and downloads | Actual Safari 27.2 guest/consent/review/result/refresh sampled; full account/exports, native picker completion and speech remain pending. See consumer-validation-results.md |
| VoiceOver/TalkBack and keyboard only | Names, roles, announcements, focus restoration, dialogs, input errors and reading order | Keyboard/focus sampled in browser; actual speech/phone assistive technology not verified |

Test 320px reflow, actual 200%/400% browser zoom, light/dark, reduced motion,
landscape/portrait, slow/lost network, offline navigation, cold models, account
switching during requests and server/storage failures. Automated geometry or
emulation alone does not establish WCAG conformance or real-device success.

## Clinical/model validation remains separate

Choose governed data, patient-level separation, external prospective evaluation,
representative populations/skin tones/capture devices and clinically meaningful
error/abstention criteria with qualified reviewers. Obtain relevant component
permissions and review intended purpose/claims. Never use software test counts,
synthetic-image inference or model-file checks as clinical performance evidence.

## Observer-ready first-use study

**NOT TESTED — HUMAN PARTICIPANTS REQUIRED.** No real sessions or numerical
usability outcomes have been collected. Recruit approximately 5–8 consenting
representative intended consumers, including varied technical confidence and
access needs when feasible. Agree the audience and clinical/research boundaries
first. Do not substitute the developer or browser automation for participants.

### Introduction and consent script

“Thank you for helping us test this development app. We are testing the software,
not you. It provides educational screening support, not a diagnosis or a treatment
service. Use only the fictional details and sample files provided. Please say
what you are looking for, expecting or finding confusing. You may skip a task,
take a break or stop at any time. We will record task outcomes and brief anonymous
notes. We will not collect personal medical photos or health histories. Recording
is off by default; any optional recording requires separate informed permission.”

Explain who can read notes and agree a limited retention/deletion date before
sessions. Store anonymous notes in the project's ignored local artifacts with
restricted access; do not upload them or commit them to Git. Separate scheduling
contact details from observations. For accessibility tasks, offer the person's
usual device/assistive technology and let them control its settings.

### Six non-leading tasks

Provide a clean guest tab and a disposable synthetic account with fictional saved
records. Show the task text, not instructions naming UI controls. Use a generated
photo only for upload mechanics; choose a fictional sweating case for completing
a result without interpreting generated pixels clinically.

| Task read to participant | Observable success (observer only) |
|---|---|
| 1. “You have just found this app. Find out what it can help you do and what it cannot tell you. Explore without saving personal details.” | Explains educational/research limitations in their own words; enters guest; finds appropriate input route without coaching |
| 2. “Use this fictional sweating example to get a summary. Before you send anything, check what information will be used. Change an answer before continuing.” | Understands consent/save boundary; reviews, goes back, changes answer and completes once; can recover from a missing-consent attempt |
| 3. “Explain this summary to a friend. What is known, what is uncertain, and what would you do next?” | Distinguishes questionnaire/report from diagnosis or calibrated probability; finds next step and detailed explanation; no false reassurance |
| 4. “In this test account, record following the provided routine. Then imagine you tapped the wrong action: make the record accurate and find it later.” | Completes/corrects action, records check-in, finds effective history and understands original evidence remains |
| 5. “Prepare something to take to an appointment about this fictional concern, covering these dates. Also find useful background reading you could revisit.” | Chooses correct concern/range, checks coverage, downloads accurate brief; saves/finds/reopens guide and can remove bookmark |
| 6. “Find what this test account keeps, obtain your copy, then leave the workspace safe for another person to explore.” | Finds privacy/JSON export, understands photos/provider limits, signs out and verifies guest has no private records |

Use the same fictional case, task wording and starting state for comparable
sessions. Record actual workflow problems; do not lead with “does it look
professional?” or explain the intended solution while timing a task.

### Observation method and blank template

Start timing when the participant finishes reading the task; stop at its observable
success, withdrawal or the agreed cap (suggested five minutes per task). Note any
interruption separately. If asked for help, first say “What would you expect to do?”;
record the request. If coaching is necessary, mark completion **with assistance**.
Stop a task that causes distress or invites real medical decisions. Do not count
an assisted completion as an independent success.

Use one row per attempt:

`Participant code | Task | Device/browser/access needs volunteered | Start/end |
Elapsed seconds (observed) | Independent / Assisted / Failed / Stopped / Not run |
Errors and recovery | Hesitation location and observed duration | Exact quotation
(if consented) | Result meaning / uncertainty / intended next step | Issue ID`

Leave unobserved fields blank. Hesitation is an observed pause/search/backtrack,
not a guessed feeling. Separate participant quotations from observer inference.
After tasks ask: “What information did you trust?”, “What was uncertain?”, “What
would you do next?”, and “Was anything missing or difficult?” Do not supply the
answers. Confirm whether diagnosis, probability or healing was mistakenly inferred.

### Issue triage and study summary

Issue template: `ID | P0/P1/P2/P3 | Observed trigger | Expected | Actual |
Consumer impact | Reproduction | Affected participants/task (actual denominator) |
Evidence | Minimal candidate fix | Owner | Retest | Status`.

Use the existing severity definitions: P0 privacy/evidence corruption/unsafe
behavior; P1 blocked main task or serious accessibility/navigation barrier; P2
recoverable friction/confusing feedback/focus; P3 optional preference. Frequency
alone does not downgrade a serious privacy or evidence problem. Mark findings
NOT REPRODUCED when independent reproduction fails; preserve the original note.

Summary template: `Session dates; actual participant count; devices and exclusions;
tasks attempted; independent/assisted/failed outcomes with denominators; raw elapsed
times and interruptions; recurring confusion; result misconceptions; ranked
reproduced issues; changes selected; retest evidence; limitations and next decision`.
Small-sample findings do not establish population usability, clinical accuracy or
accessibility certification. Do not publish empty templates as completed research.

Connection/test steps and the blank device result sheet are in
[physical device and native accessibility checks](consumer-device-checks.md).
