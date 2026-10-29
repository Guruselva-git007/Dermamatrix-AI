# Physical device and native assistive-technology checks

**Owner steering — 29 October 2026:** the Samsung was connected over USB, but
Chrome remained Pending authentication. Guruselva explicitly asked to leave
phone testing and finish available Mac work. Physical tests are deferred; do not
restart connection probes or debugging setup without a new request. A suggested
USB-authorization reset was not confirmed completed. See the newest native
acceptance section in `consumer-validation-results.md` for available Safari
results and the remaining native Save/Upload/dialog/zoom/speech checks.

When an interactive device session is requested again, prepare the existing
isolated environment first, give one action at a time, wait for actual owner
observations, record outcomes and fix/retest demonstrated app defects in the
same task. Resume from the first unfinished check; do not repeat verified work
or substitute browser emulation for physical acceptance.

Development only. Use the isolated synthetic stack on loopback port 8001, never
personal health records or the normal account database. The temporary stack is
closed after each development batch. Tell the developer **“Phone connected;
start the isolated device session”** before opening the test URL. Existing local
launcher, synthetic database and fixtures are reused; no public tunnel is needed.

## Samsung Galaxy S26 Ultra: minimum connection steps

1. Unlock the phone and connect it to the Mac with a data-capable USB cable.
2. If Developer options are absent: Settings → About phone → Software information
   → tap Build number seven times; enter the phone PIN yourself if requested.
3. Settings → Developer options → USB debugging: enable it for this test. Open
   Chrome on the phone. Approve the Mac's USB-debugging prompt on the phone only
   when you recognise this Mac. Do not share your PIN or debug credentials.
4. In the Mac's existing primary Chrome profile, open `chrome://inspect/#devices`.
   Check **Discover USB devices**. Once the phone is listed, choose **Port
   forwarding**, enable it and map device `8001` to `127.0.0.1:8001`.
5. Open `http://127.0.0.1:8001/` in phone Chrome. Confirm that it is the synthetic
   test session; choose guest first. This USB mapping keeps the server on loopback.
   Do not bind the app to `0.0.0.0`, use the Mac's LAN address or create a tunnel.
6. After testing, remove the port-forward mapping, disconnect the cable and turn
   off USB debugging if you do not otherwise need it. The developer closes the
   owned test stack. No new background scheduler is installed.

If the phone is absent or says unauthorised, unlock it and check the cable and
on-phone prompt once. Stop after that bounded check and record the actual state;
do not keep trying unattended. Android Debug Bridge is not required for Chrome's
built-in USB workflow. The menu path follows [Samsung's Developer options guide](https://www.samsung.com/ca/support/mobile-devices/galaxy-phone-developer-options/).
See [Google's connection guide](https://developer.chrome.com/docs/devtools/remote-debugging/)
and [USB port forwarding](https://developer.chrome.com/docs/devtools/remote-debugging/local-server).

## Device test card

Use generated image fixtures, or take a non-sensitive photo of a plain object
solely to test capture/selection. Do not interpret such an image as a medical
case. Do not submit personal medical photos. No source image should enter saved
account evidence, an export or a worker cache.

| Check | Action | Expected observable outcome |
|---|---|---|
| First use | Guest → Check → each concern | Four separate input routes; no saved guest history |
| Native camera | Skin → image chooser → camera; cancel once, then capture a non-sensitive object | Cancellation is recoverable; selection/preview or honest format/quality feedback appears; no assessment before consent |
| Gallery | Select a generated JPG/PNG and real device-produced HEIC/HEIF if available; replace and cancel | Selected file/type is clear; HEIC preview limitations honest; old consent clears on replacement |
| Permission recovery | Deny camera in the browser/OS, reopen chooser and use gallery; restore permission yourself if desired | Useful recovery without trapping the form; permission UI may belong to browser/OS |
| Limits | Try an unsupported file and a photo above the existing 10 MB or 16 MP limits | Local/server rejection with next steps; no silent resizing |
| Routing | Ordinary Skin, Hair, Nails; choose dermoscopy only with a genuine dermoscopy fixture and attestation | Separate routes/limits preserved; no invented Hair condition classifier |
| Touch/keyboard | Type into bottom fields with keyboard visible; scroll; double-tap Save once in a synthetic account | Primary controls reachable; no unintended duplicate records |
| Layout | Portrait/landscape, large system text, browser zoom, light/dark | Content and focus usable; note exact browser/font/zoom setting and any overlap |
| Navigation | Android Back, refresh, interruption during review and reconnection | No hidden submission; useful recovery; guest evidence not restored as account history |
| Follow-up | Synthetic account: routine → Done → correct to Skip → check-in → Journey | Effective view updates; original action and revisions preserved |
| Exports | Select concern/date → visit brief; account JSON → sign out → guest | Correct saved metadata, no original photos; no previous account data in guest |
| Installation/offline | Install if offered; disconnect, navigate, reconnect | Only static offline explanation; no offline health processing or cached account data |

Run Chrome first. Repeat core camera/gallery, input/keyboard, Back and download
checks in Samsung Internet if the same loopback URL is reachable through the
active USB mapping. If it is not reachable, record that limitation; do not expose
the app to the LAN to make it work. Physical iPhone checks remain optional until
a device is actually available. Follow [Apple's iOS inspection procedure](https://developer.apple.com/documentation/safari-developer-tools/inspecting-ios);
USB forwarding instructions for Android do not establish iPhone reachability.

## Mac Safari: short owner check

The developer exercised the actual Safari application with a guest questionnaire,
consent rejection, review/keyboard confirmation/Escape, result and refresh. This
is separate from automated WebKit evidence. The native upload panel listed both
generated HEIC and PNG as eligible, but its Upload action stayed disabled under
this automation. It was cancelled; no native image upload success is claimed.

During the isolated session, open `http://127.0.0.1:8001/` in Safari → guest →
Skin → choose the generated `synthetic-colour.heic` or `.png` from the task's
private `fixtures/` directory. Click Upload yourself and report whether the
button enables. Also cancel/reopen once. Use no personal photo. This distinguishes
a native-panel/tooling limitation from an actual Safari selection defect.

Safari website settings exposed 200% and 300% page zoom (300% was the maximum
listed), and zoom was restored to its original 100%. Enlarged auth content was
inspected after reload, but complete zoom/focus acceptance was not established:
some live zoom/navigation paints and modal AX snapshots were inconsistent through
the tool. Check 200%/300%, keyboard reachability and the review heading yourself;
record what you see. Safari may require Option-Tab to traverse all controls; that
reached Back/Confirm in this session without a settings change. Do not claim
400% Safari testing or native speech from those
partial observations. Remote automation was not enabled or security changed.

## VoiceOver and TalkBack: genuine spoken-output checks

Actual speech could not be observed in the current tool session. These checks
remain **NOT TESTED — OWNER INTERACTION REQUIRED**. Accessible names/DOM snapshots
and focus tests are supplementary evidence, not speech verification.

- **Mac:** Open the synthetic Safari page. Toggle VoiceOver with Command-F5
  (or Fn-Command-F5 where required); handle any first-use tutorial yourself.
  Use Control-Option-Right/Left to move, Control-Option-Space to activate, and
  Control-Option-U for the rotor. Check headings/landmarks, file chooser, consent
  error, review title/Back/Confirm, result limits, search and sign-out. Listen for
  names, role/state, status announcements, reading order and restored focus.
  Toggle VoiceOver off when finished if it was originally off. See [Apple's
  VoiceOver guide](https://support.apple.com/guide/voiceover/welcome/mac).
- **Samsung:** Settings → Accessibility → TalkBack → enable, then use right/left
  swipes to move and double-tap to activate. Two-finger scrolling is normally
  needed while TalkBack is on. Repeat consent/error/review/result/navigation
  checks and listen for dynamic feedback. Turn it off afterward if originally
  off. Use the device's shown shortcut/instructions if gestures differ. See [Google's
  TalkBack setup](https://support.google.com/accessibility/android/answer/6007100)
  and [gesture guide](https://support.google.com/accessibility/android/answer/6151827).

Record exact spoken words only when actually heard. A silent, unnamed or missing
modal is a finding to investigate, not something to mark passed from the DOM.
Do not record personal audio or participant health content by default.

## Result sheet (one row per actual attempt)

`Date | Device/OS/browser version | Synthetic task | Setting | Pass/Fail/Blocked |
Observed behaviour/words | Reproduction | Severity | Evidence reference |
Retest result`

Status labels: VERIFIED TESTED; VERIFIED IMPLEMENTED; NOT REPRODUCED;
NOT TESTED — DEVICE UNAVAILABLE; NOT TESTED — HUMAN PARTICIPANTS REQUIRED;
BLOCKED — OWNER/POLICY DECISION REQUIRED. Use a participant code instead of a
name. Leave unrun results blank. Do not convert expected outcomes into observations.
