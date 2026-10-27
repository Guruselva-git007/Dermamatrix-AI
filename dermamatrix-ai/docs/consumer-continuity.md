# Consumer continuity development

28 October 2026. English-only development. No deployment, provider activation,
new classifier, model preprocessing change, training or source-photo retention.
The Achromatic ledger, IBM Plex and existing canonical medical result contracts
remain in place.

## Authoritative records and compatibility

No new table, DDL, migration, destructive backfill or normal-database rewrite is
needed. The reviewed schema already has owner/subject indexes on
`consumer_records`, owner indexes on assessments/routines, and owner/date indexes
on check-ins. Existing explicit migration history remains unchanged. These new
record kinds extend that existing store, rather than establish a second health
database:

- `event_correction` and `checkin_correction`: append-only effective-field
  revisions, prior revision, actor, timestamp, reason and correction-v1 contract.
- `concern_episode`: immutable label, category and selected body area. Duplicate
  create retries share one ID. Similar labels do not merge concerns.
- `episode_link`: current explicit association; `episode_link_revision` is its
  immutable audit. Saved assessment JSON and older free-text labels are untouched.
- `checkin_submission` and optional `routine_submission`: transaction/retry
  receipts. The underlying original rows remain authoritative evidence.
- `guide_bookmark` plus `bookmark_revision`: saved/removed state with original
  guide identity, content version/date and sources, separate from medical records.
- `product_feedback`: account-owned, explicitly local and unmonitored; the server
  supplies the app version. No health records or photos are attached automatically.

The correction endpoint locks the account and reads the current locked revision
after any wait, then appends or replays a bound request key. Stale revisions and
key reuse for another record/payload are rejected. It never updates or deletes
the original event/check-in. Removing a mistaken check-in marks its effective
projection voided; its original remains in exports and correction history.

`effective_checkins` / `effective_events` are shared adapters for Today, check-in
history, routine counts, search, visit briefs, recent-history PDF and account
JSON effective views. Check-in ordering uses corrected dates before applying the
recent display window. All original rows and immutable revisions remain in the
JSON `records` section. Display counts and self-reported priority semantics do
not claim image-measured healing.

New assessment concern links save in the assessment transaction. The existing
submission fingerprint binds the selected concern as well as the inputs, so an
interrupted retry cannot silently switch concern. Historical unassigned records
remain visible. Category-incompatible assessment links are rejected. Scheduled
events snapshot their explicit concern at creation; later routine reassignment
does not reclassify a past action. No label-based automatic linking occurs.

## Connected workflows

- Create a concern in Journey; explicitly select it for a new assessment or link
  a saved result. Choose it again for a follow-up. Keep free-text legacy labels.
- Create a routine, choose its concern and schedule, preview local timezone and
  quiet-hour effects, then record Done/Skip. Correct an action from Today or its
  schedule history. The original and revision trail remain readable.
- A routine shortcut supplies its current concern as a visible default. Review
  routine, concern, date, reported trend and optional note before saving a
  check-in. Back preserves input; uncertain saves reuse a tab-only request key.
  Corrections update effective displays. The unused check-in photo input is
  hidden in consumer mode; no image is submitted or scored by that workflow.
- Preview one concern/date range for a clinician visit, explicitly choose
  assessments, add personal questions, and download a metadata-only PDF.
  Assessment save times use UTC; check-ins/actions use recorded local dates.
  Counts disclose coverage; an over-1,000-record brief requires a narrower
  selection rather than silently truncating it. No original photos are available.
  The existing full assessment PDF, recent-history PDF and complete account JSON
  remain separate and available.
- The header search groups private assessments, concerns, routines, effective
  check-ins and public guides. Account/filter-bound signed cursors paginate 20
  results. A changed consumer revision invalidates continuation so the user can
  restart with current information. Owner-indexed reads use no shared private
  search cache. Guests receive public guides only. Product search remains separate.
- Save a guide from Learn, reopen it from saved topics or search, then remove its
  bookmark. Sources/version/date are preserved; no reviewer identity is invented.

Private drafts and retry keys stay in tab memory. Account clearing empties new
forms/lists/dialogs. An owner guard rechecks the account after asynchronous CSRF
preparation and before sending writes, preventing an old draft from being sent
under a newly signed-in account. Error states distinguish unconfirmed saving,
conflicts, invalid inputs, unavailable services and useful retry steps.

## Recovery without evidence loss

For a mistaken correction, read the original and revision history and submit a
new correction with the latest revision and the intended prior values. This is
tested for completed → skipped → not recorded → completed, preserving the same
original and every revision. Replaying the same request does not append twice.
Never delete a correction to recover an earlier effective state.

For an interrupted concern/routine/check-in creation, retry the unchanged input
with the same tab key. For a stale association or correction, reload the current
version before a new action. Drafts are not persisted for guests or automatically
replayed after an account switch. No schema rollback is needed for this batch.

The existing authenticated encrypted-copy and empty `*_restore_synthetic`
procedure still covers the unchanged schema, including consumer records. Do not
restore over a populated database or disable correction projection to present
uncorrected health history as current. Preserve the data and fix the reader if an
application rollback is required. This batch's recovery proof is an isolated
synthetic append-only reversal, not restoration of a real user's backup.

## Verification and limits

Synthetic integration cases cover empty, one, 56 mixed-category assessments,
105 historical check-ins, unassigned records, simultaneous corrections/retries,
stale and cross-account requests, original JSON preservation, corrected-date
ordering, filtered briefs and complete exports. Browser scripts are
`frontend/tests/browser-smoke.js` and `frontend/tests/browser-continuity.js`.
Exact final results and commit receipts belong in the sole canonical checkpoint,
`ROADMAP_EXECUTION_STATUS.md`.

Viewport, keyboard, accessible-name/status, native-dialog, large-text, dark-theme
and synthetic camera/gallery fallback checks are software evidence. Physical
iPhone/Android capture/HEIC, actual screen-reader speech and representative human
usability checks remain external. No WCAG certification, clinical review, real
delivery or deployment is claimed. Closure/erasure execution awaits DM-06 policy.

## Concern boundaries on comparisons

New comparisons use the existing scoring/lineage engine with history restricted
by the authoritative explicit concern link. Unassigned assessments compare only
with unassigned records of the same area. Distinct concerns get distinct derived
query identities. Persistence is serialized per owner after ending the initial
authentication read snapshot, so simultaneous follow-ups see a consistent saved
baseline. No score formula, classifier or historical JSON is changed.

The Today comparison key includes the current concern association as well as
model/decoder/scoring lineage. Saved-result opening refreshes owner-scoped
metadata; a comparison saved under a different assignment is suppressed in the
current consumer view with an explanation. The original comparison remains in
the original metadata/report, where query context is explicitly labelled as
original save-time context. Tests cover two separate same-area concerns,
unassigned history, several follow-ups in one concern, simultaneous follow-ups,
correct baseline identity, and reassignment without modifying saved evidence.
