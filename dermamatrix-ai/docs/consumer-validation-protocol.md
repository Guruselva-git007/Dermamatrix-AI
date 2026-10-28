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
| Actual desktop Safari application | Complete flows, focus and downloads | Remote automation is disabled on this Mac; no system setting changed and no actual Safari verification claimed |
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
