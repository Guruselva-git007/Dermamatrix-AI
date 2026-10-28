# Consumer UI refinement — 29 October 2026

Scope: development only, English only. This batch extends the existing Achromatic
ledger (seed 1478287822) and self-hosted IBM Plex type. It adds no feature,
provider, deployment, model, migration, source-photo storage or new dependency.
The screen's first question remains: Today — what next; Check — what input is
needed; Learn — which guide; Profile — which preference or account control.
The four concern pathways and truthful account/guest records remain the product's
identity. No visual direction was redrawn and no sample data was added to the UI.

## Observed problems and verified corrections

All selected findings are P2 usability/accessibility refinements. No new P0/P1
workflow defect was reproduced in the changed flows. These observations are
engineering/browser evidence, not findings from a participant study.

| Finding / reproduction | Consumer impact | Minimal correction | Final observation |
| --- | --- | --- | --- |
| Empty account/guest Today at 1440px: two short follow-ups each span 1144px | Sparse content takes two broad stacked rows | Pair next step and recent activity only while the existing latest-overview panel is hidden | Both follow-ups start on the same row, 562px each with a 20px gap; populated-account layout stays on its existing path |
| Today at 390px: inherited mobile `.consumer-panel button { width:100% }` squeezes the adjacent heading | “Your next step” wraps while its text action occupies 231px | Content-size this heading action, allow wrapping for enlarged text, align it centrally and retain a 44px target | Heading uses one 22px line instead of two lines/44px; help remains available |
| Guest Profile: account panel touches Preferences; mobile Health notes precedes the title | Sections appear merged; screen hierarchy is reversed | Add the existing 20px section gap; replace heading floats with an explicit grid | 20px gap at 320/390/768/1440px; title and description precede the mobile action |
| Learn: wrapping topic titles stretch Read guide buttons from 47px to as much as 91px | Identical actions have inconsistent placement and size | Centre actions within their rows; put category and submit on one mobile row beneath search | All normal-text guide actions are 44px; first guide moves from y=460 to y=400 at 390px, and y=490 to y=430 at 320px |
| Selected concern chooser at 390px remains 180px high with repeated descriptions | Photo/questionnaire input is unnecessarily far down the screen | Keep detailed choices before selection; compact labels after selection | Selected chooser is 98px, 82px shorter, with at least 44px targets |
| 200% computed-text stress at 320px: Today content reaches 330px; Check step count reaches 371px | Enlarged labels escape the viewport or their controls | Let narrow concern grids become one column, allow word wrapping and wrap assessment metadata | Four changed routes have no page overflow or clipped action content in the simulation; at normal 320px the selected chooser is deliberately 206px rather than 198px to preserve readable labels |

To reproduce normal layouts: enter Guest, open Today / Check / Learn / Profile,
select Skin for the selected-state sample, and resize to 320, 390, 768 and 1440px.
The local evidence folder retains exact baseline/final geometry and screenshots.
Enlarged-text evidence uses a documented browser test that doubles each displayed
text element's computed font size; it is not actual OS text scaling, browser zoom,
a screen-reader speech test or a physical-device result.

## Implementation and protection

The only runtime file changed is `frontend/product.css`. Changes are scoped to
existing headings, lists and concern controls. No persistence or schema change
was necessary. All backend Python files, frontend JavaScript and `index.html`
match the preserved task baseline. Consent, canonical evidence, model limits,
account ownership, check-in corrections, episodes, histories, reports and exports
therefore retain their existing implementations, with workflow regression below.
The isolated test instance reused an existing synthetic database on loopback
3308; the normal database/service on 3307/8000 were not restarted or migrated.
Email stayed disabled. No personal account or health photo was used.

No speed-up, clinical result or consumer satisfaction improvement is claimed.
There are no new scripts, API calls, dependencies or background processing jobs.

## Test evidence

- Local frontend regression: **74/74 pass**, no failures/skips.
- Local Chrome: **53/53** connected and actual origin-outage/recovery checks pass.
- Local WebKit: **53/53** of the same workflows pass. This is automated WebKit,
  not native Safari or a physical iPhone result.
- Local Firefox did not launch: its installed engine reported “Could not find
  profile folder.” No application test ran in that engine locally. Use the
  exact-source Linux CI receipt below for Firefox coverage; no framework or
  browser was reinstalled merely to work around the local launcher.
- Targeted geometry: **56 samples**, seven routes × four widths × two themes,
  without page overflow or uncaught JavaScript errors. Final changed-route
  screenshots/geometry also cover the last 44px help-target adjustment.
- Four changed routes pass the **200% computed-text simulation at 320px**;
  final checks also reject content that escapes action boundaries.
- Simulated availability of the existing Install workspace action preserves
  separate placement from Health notes. This is a layout fixture, not an
  installation test or a newly enabled installation feature.
- Design source lint: **0 failures, 33 warnings**. Runtime design heuristics were
  also inspected; they are not a blanket acceptance score. Their first-h1 lookup
  chooses hidden authentication markup; their text walk includes hidden option
  labels/legacy panels, reporting nonexistent visible 10px text and Manrope.
  DOM visibility checks find the correct active h1 and IBM Plex, with no visible
  10px text in those samples. Floating toast/dialog shadows are intentional;
  darker concern-control borders provide control contrast. Short recent activity
  keeps its natural height beside a longer next-step panel instead of inventing
  content or padding an empty card to force equal height.
- `git diff --check` passes. Existing suites were reused; no duplicate framework
  or production test hook was added.

Final [Linux development CI 40762096112](https://github.com/Guruselva-git007/Dermamatrix-AI/actions/runs/40762096112)
**passes exact runtime source `c0b9d545559df8f9b1802dcc1e1d74cf4a6a57a0`**:
**258 backend tests, 74 frontend tests and 159 browser checks (53 each in
Chrome, Firefox and WebKit)**. Explicit synthetic migrations, tracked-source
hygiene and the pinned dependency audit pass, with no known vulnerabilities in
the audited dependency environment. This receipt covers full workflow continuity,
corrections, episodes, save/search/bookmark/export, account isolation, recovery
and origin outage. It does not establish default-branch, clinical or deployment
readiness. The workflow retains a nonblocking GitHub Actions runtime-deprecation
annotation; it did not fail a gate and no workflow/dependency source changed here.

Source is saved in three scoped commits: `36b5177`, `a9c6e93`, `c0b9d54`.
Closing Markdown follows the tested source. Task test services and browsers are
closed; normal 8000 serves the updated CSS without a restart. Final remote
synchronization and sleep-hold release are recorded in the private completion
receipt. No additional visual changes are selected for this batch.

Private evidence: `local-artifacts/ui-refinement-2026-10-29/` at project root.
Early harness failures (onboarding timing, ambiguous hidden install button) and
failed enlarged-text attempts are retained, not counted as passes. Two interim
CI runs were superseded/cancelled after the enlarged-text fixes; only the final
source run is the closing regression receipt.

## Remaining external checks and next step

Physical Samsung camera/gallery, touch/keyboard, actual TalkBack/VoiceOver speech,
full native Safari picker/zoom acceptance, optional physical iPhone and the
representative consumer study remain external. Follow `consumer-device-checks.md`
and `consumer-validation-protocol.md`; their instructions remain current. There
is no need for a new device connection probe or another speculative redesign in
this batch. Next development work should follow those actual observations.
Deployment and provider activation remain deferred until explicitly requested.
