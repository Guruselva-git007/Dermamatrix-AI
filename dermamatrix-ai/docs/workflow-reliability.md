# Assessment workflow reliability

The existing local research pathways, result contract and score calculations are
unchanged. Ordinary Skin and dermoscopy keep separate research routes; Nails
keeps its qualified research rankings; Hair has no condition classifier; Sweat
uses its transparent questionnaire rules. These remain research/education
capabilities rather than clinically validated diagnoses.

## Submission and recovery

The browser prevents duplicate entry while processing, locks the submitted
inputs, and shows an accessible processing dialog. **Stop waiting** aborts the
browser wait; it cannot retract a request already received or undo committed
server work. Interrupted and failed responses never become a ready result.
Inputs remain only in the current tab for correction or retry. Signing out,
entering guest mode or changing account clears transient health inputs, upload
URLs, result content and previous-account history.

The browser sends an `Idempotency-Key` for each assessment attempt. An unchanged
retry after an interruption reuses it. Successful completion or changed inputs
starts a new attempt. The backend accepts bounded keys and, for an authenticated
active owner, uses an account/purpose-scoped MySQL advisory lock and the existing
unique assessment identifier. A committed retry returns the original stored
metadata and canonical result rather than rerunning or saving another record.
Concurrent matching requests serialize; a busy lock returns 409 with
`ASSESSMENT_IN_PROGRESS`. Different inputs with an already-used key return 409
with `ASSESSMENT_INPUT_CHANGED`. Current request consent and notice version are
checked before replay lookup or application file-stream reading.

A server-keyed HMAC of the submitted fields and file bytes is stored alongside
the derived result solely to bind the retry to the original inputs. It contains
no raw upload or thumbnail. No new database table, schema migration, image cache,
external service or persistent browser health storage was introduced. Source
photos and overlays are not retained; a replay cannot recover them. Report,
care, scores, timestamps and model lineage come from the original record.

Guests remain non-persistent, so cross-request replay is not stored for them.
Legacy clients without a key retain the existing request contract and do not
receive this retry guarantee. A database outage can still yield a useful
assessment marked **not saved**; retry protection requires working storage.
This is not a global job queue, model-capacity limit, cancellation protocol,
consent-withdrawal service or medical-validation control.

## Results and continuity

Patient-facing completion text distinguishes research completion, questionnaire
completion, completion with unavailable components, uncertain evidence and input
correction. Technical failures and interruptions stay in the existing frontend
state machine; numerical PIRS, severity, concern and urgency are unchanged.
Storage status is independent: database failure is never labelled guest mode.
A signed-in saved-result action opens My Journey. PDFs require a saved result.

Saved reports have their own visual context and never borrow a different photo
currently selected in the form. Unreadable historical JSON is marked unavailable
without rewriting it or breaking the other history records. The detail/PDF
endpoints return an actionable 409 for unreadable evidence. Original canonical
results, dates, scores and model provenance are preserved.

## History loading and report access

Concurrent history readers share one in-flight batch. If a save requests a
forced refresh while a batch is pending, callers wait for one shared fresh batch
instead of caching the pre-save snapshot. Account/workspace generation checks
prevent an older response from restoring cleared health information or clearing
a newer account's request. Refresh failure remains retryable and cannot produce
a misleading successful Journey refresh.

My Journey starts with six reports and reveals the remaining loaded recent
results in groups of six without another API request. The existing backend
limit of 50 recent assessments remains unchanged. Expanding moves keyboard focus
to the first newly revealed result. Refreshes preserve a selected check-in
routine if it still exists. Saved image results offer distinct Download PDF and
Continue Journey actions. A just-saved result can download before its background
history refresh completes. Delayed assessment/history PDFs are discarded if the
account or workspace changes before the body arrives.

Retry-lock cleanup always closes its dedicated connection. A MySQL error while
releasing the lock is logged without private request data and cannot replace a
completed result or the original processing exception.

## Consent boundary and remaining decisions

Every new action and replay requires its applicable current acceptance. False
or obsolete request acknowledgement is refused; presentation preferences cannot
change consent. Logout removes access through that browser's signed session.
The prototype has no defined account-wide withdrawal/revocation or retention
workflow. Its legal effects, historical-record access, backups, holds and
verification of a rights request remain the explicit decisions recorded in
`audit-upgrade-decisions.md`. No new withdrawal policy is implied by stopping a
wait or unchecking a request acknowledgement.

Public hosting, independent clinical validation, an actual clinician review
service, missing source/weight permissions and formal assistive-technology
certification remain outside this local workflow repair.

## Verification

The reproducible local acceptance evidence for this work lives in the project's
ignored `local-artifacts/workflow-optimization-2026-10-25/`. It uses synthetic
accounts, inputs and a separate schema/listener, preserving real account data.
Backend retry, ownership, input and rollback regressions are in
`backend/tests/test_workflow_integrity.py`; frontend lifecycle, preference-race,
interruption and malformed-response regressions are in
`frontend/tests/workflow-integrity.test.cjs`.
