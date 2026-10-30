# Local consumer development

Deployment is deferred by the owner. These features extend the existing Flask /
MySQL app and do not establish clinical, legal or public-service readiness.

## Explicit setup and rollback

1. Preserve the current source and configure an isolated synthetic database.
2. Run `PYTHONPATH=backend .venv/bin/python backend/scripts/migrate_database.py --apply`.
   It explicitly prepares the legacy base schema and additive consumer tables.
   Normal worker startup no longer runs schema DDL. Existing rows/results are not
   rewritten. Migration DDL is idempotent if interrupted; MySQL DDL is not claimed
   to be transactionally reversible. Run with a reviewed backup/recovery plan.
3. Set `DERMAMATRIX_CONSUMER_ENABLED=true` only after the migration succeeds.
   Enabling it requires existing cookie holders to sign in again; legacy cookies
   cannot become unrevocable sessions. Keep a persistent session secret.
4. Start the existing local launcher. `/api/readiness` checks storage/schema;
   model availability must be checked separately by
   `PYTHONPATH=backend .venv/bin/python backend/scripts/smoke_installed_models.py`.
5. To roll back consumer activation, set the consumer flag false and restart the
   local worker. Preserve additive tables and all history; do not run DROP or
   delete health data as rollback. Restore a verified backup only through an
   approved recovery procedure, never over a populated database for a test.

## Account and privacy contracts

Account verification and email-change links expire after 30 minutes and are
single use, server-keyed hashes. Links carry tokens in their fragment, which the
client removes before making requests. Password reset queues the same-shaped
request for matching/nonmatching addresses; a separate worker mints tokens and
sends email so transport latency is not exposed in account lookup responses.
Queue payloads contain no raw action token. Expired work is not sent. Lost
handoff confirmation is marked uncertain, never silently redelivered. Sensitive
account actions require the current password and are rate limited.

Password reset/change revokes issued sessions and outstanding account links.
Email change is applied only after verifying the new address and revokes old
sessions. Current-session logout revokes its server record, preventing replay of
that signed cookie. Account endpoints use a CSRF token in addition to existing
origin/Fetch Metadata controls. No authentication tokens enter localStorage.

A processing pause blocks NEW signed-in assessments, history writes, routines,
scheduled-step events and review requests at the API boundary. Per-action consent
cannot override it; resumption is a separate password-confirmed action. In-flight
work may already have begun and cannot be recalled by a browser stop or pause.
Historical access/export remains available. Existing records are not erased.
A separately chosen guest workspace stays nonpersistent and has its own consent.
This is an explicit technical pause, not a final legal withdrawal/retention policy.

Correction/deletion/closure/help/content requests are deduplicated, owner-scoped
and recorded locally with `recorded_locally_pending_operator`. No operator or
monitored inbox has been appointed, so no review, notification, erasure or closure
is claimed. Destructive execution awaits the existing decision register.
The JSON export includes enabled consumer tables and excludes token/session
hashes and secrets; the recent-history PDF remains separately bounded.

## Development mailbox and workers

Default transport is `disabled`. An isolated test mailbox requires all of:

- `DERMAMATRIX_ENV=test`
- `DERMAMATRIX_MAIL_TRANSPORT=sink`
- `DERMAMATRIX_MAIL_SINK=/absolute/private/test/mailbox` (outside served folders)
- `DERMAMATRIX_APP_ORIGIN=http://127.0.0.1:8001` for the isolated test server.

The sink writes synthetic emails to mode-0600 files in a mode-0700 directory. It
is not real delivery. Never enable it for real user accounts. SMTP support uses
implicit TLS, explicit host/from/optional credentials, and HTTPS account links
outside tests. Choosing/configuring a provider remains an owner action; successful
SMTP acceptance is `provider_accepted`, not confirmed delivery. The implicit TLS
connection explicitly verifies certificate trust and hostname using the system
trust configuration; certificate failure stops delivery without a fallback.
The owner has deferred provider selection and real delivery testing to deployment.

Explicit bounded worker cycles (no scheduler/service installed automatically):

```
PYTHONPATH=backend .venv/bin/python backend/scripts/run_account_mail.py --run-once
PYTHONPATH=backend .venv/bin/python backend/scripts/run_reminders.py --run-once
```

Routines have immutable schedule revisions and completion/skip event snapshots.
Today submits the schedule version and reuses its request key after a failed
response. Under the schedule lock, one occurrence (owner, routine, date, time,
step and schedule version) has one event even across tabs with different request
keys. A different action for that occurrence or a stale submitted version returns
a conflict and requires refreshing Today.
Editing steps never rewrites events. Archiving preserves routines, check-ins and completion events; paused/archived routines are excluded from active totals. Schedules record IANA timezone, days,
local times and quiet hours. DST gaps are skipped; repeated local times use the
first occurrence once. Quiet-hour occurrences are skipped, not silently shifted.
Email reminders require opt-in, active routine, active account, verified email,
enabled reminder preference and no processing pause at handoff. New schedules
cancel superseded jobs. Jobs are bounded/leased/deduplicated, late jobs cancel,
recoverable test-transport failure retries at most three times, and ambiguous
SMTP or crash-after-handoff states require review. Queueing is not delivery.
No source photos or condition-specific notification text enter any job.

## UI and records

Today uses actual schedules/events; no healing or completion is inferred.
Journey adds an owner/filter-bound signed keyset cursor, snapshot bound, search
and area/episode/body-area filters beyond the old 50-row listing. User labels are stored separately from original result evidence, with their own revisions. Original result contracts/PDFs
are retained. Model-version changes are not clinical progress. Existing links
and routes remain, with Today/Check/Journey/Profile aliases and a Learn route.
Learn uses the existing sourced content and versions, explicitly disclosing the
unrecorded clinical reviewer; no new medical translations were generated.

Photo input now accepts genuine HEIC/HEIF through pillow-heif 1.8.1. Thumbnails,
depth and auxiliary images are disabled, decoder threads bounded, and the same
10-MB/16-MP and filename/actual-format checks apply before RGB/model processing.
Large photos are rejected with export instructions, never silently resized.
Unsupported browser HEIC previews are disclosed; server inference still reads
real bytes. Source pixels stay in memory. The final review dialog preserves the
current-tab draft and uses the existing backend consent checks on confirmation.

The optional PWA caches only the static offline explanation. Authenticated API,
PDFs, photos, account pages and health data are never stored in its cache. Offline
installation does not enable offline assessment or notification delivery.

## Verification and operations

- Backend: `DERMAMATRIX_CONSUMER_ENABLED=false DERMAMATRIX_RUN_MYSQL_INTEGRATION_TESTS=1 PYTHONPATH=backend:backend/tests .venv/bin/python -m unittest discover -s backend/tests -v`
- Frontend: `node --test frontend/tests/*.test.cjs`
- Browser smoke: `playwright-cli -s=smoke run-code --filename=frontend/tests/browser-smoke.js`
- Readiness: `.venv/bin/python backend/scripts/check_readiness.py --url http://127.0.0.1:8001`
- Source hygiene: `.venv/bin/python backend/scripts/check_tracked_secrets.py`
- Dependency environment: `.venv/bin/python -m pip check`

### Isolated desktop browser regressions

Reuse the existing `playwright-cli@0.1.22`. Install the optional test runtimes
explicitly with `playwright-cli install-browser firefox` and
`playwright-cli install-browser webkit` (`--with-deps` on the Linux CI runner).
These are test-browser caches, not changes to a personal browser/profile or
Safari remote-automation settings. The runner installs nothing automatically.

With the existing isolated `*_synthetic` database/server on loopback port 8001,
`DERMAMATRIX_ENV=test` and `DERMAMATRIX_MAIL_TRANSPORT=disabled`, run:

```
.venv/bin/python frontend/tests/run_browser_regressions.py --browsers chrome firefox webkit --reset-synthetic-budgets
```

Each engine runs the same 15 core, 12 continuity, 21 quality and 12 targeted
accessibility/keyboard checks. A
separate context runs four real service-worker/origin-outage checks. Per-engine logs,
screenshots and strict JSON receipts go into a fresh ignored project artifact
directory. With `--reset-synthetic-budgets`, each engine starts with fresh technical request
budgets in the explicitly isolated `*_synthetic` database. No accounts, health
records or history are cleared, and application limits remain enabled. This
prevents several engines sharing one loopback IP from consuming each other's
five-minute test quota. The flag refuses a non-test database or enabled mail.
The runner refuses missing/incomplete/error JSON even if the CLI
returns exit zero, and closes only its named browser sessions.

Network-failure tests block service workers so requests remain controllable by
Playwright routing, as its [network documentation](https://playwright.dev/docs/network#missing-network-events-and-service-workers)
recommends. The outage suite enables the real service worker on an owned,
loopback relay for reads and guest sign-out only. It verifies cache scope, closes the relay's listening
socket, requires the cached explanation and failed health API access, then
restarts that same origin and verifies reconnection. This avoids a Firefox
network-emulation limitation consistent with [Mozilla bug 2081131](https://bugzilla.mozilla.org/show_bug.cgi?id=2081131),
where worker fetches can ignore an offline flag. Origin unavailability is not a
claim that every physical network disruption is identical. The upstream synthetic
app and normal services stay running; relay sockets close in cleanup. No test
origin is exposed outside loopback. Production service-worker behavior is unchanged. Browser-engine
automation does not establish physical iPhone/Android, actual Safari application,
screen-reader speech, participant or clinical validation. The authoritative
checkpoint records exactly which local/CI engines passed and platform failures.

`requirements-local.lock` records the verified Darwin arm64 CPython 3.14 runtime.
The development CI successfully executed the pinned Linux install, migration,
regression, advisory and browser-smoke checks on implementation commit 524c6b2. It has no deployment job. Neither
an existing Dockerfile nor this workflow establishes a staging deployment.

`encrypted_database_copy.py` streams a consistent MySQL dump into standard CMS
AES-256-GCM with a chosen recipient certificate. Credentials use a private
short-lived option file; plaintext dumps are not retained for backup. The
synthetic restore path authenticates/decrypts completely before executing SQL,
refuses nonempty targets and restricts restores to a distinct
`*_restore_synthetic` database. It is a recovery exercise tool, not an unrestricted
production erasure/restore endpoint. Keep actual recipient private keys separate
from backups, test restore/key recovery, set access/retention/rotation ownership
and choose storage before operational use. Synthetic restore verification does
not prove recovery of any untested real backup.

The launcher log format omits paths, query strings, identifiers, headers and
request bodies; it records method/status/duration. No analytics or session replay
was added. Existing old log files are preserved. Production monitoring, alert
recipients, support service, retention and deployment remain decisions.

## Dependency patch and evidence lineage

The first remote CI run installed dependencies and passed regression tests, then
correctly failed the advisory gate: Pillow 11.3.0, Werkzeug 3.1.8 and filelock
4.0.1 had known advisories. Requirements now pin Pillow 13.0.0, Werkzeug 3.1.9 and
filelock 4.2.1, the fixed versions identified by the dependency audit. No advisory
was suppressed. Actual-format allowlisting precedes image decoding.

Six PNG/JPEG/WEBP/AVIF/HEIC/orientation fixtures decode to identical RGB pixels
across Pillow 11.3/13. All six ordinary/rotated adapter rank orders match. One
rotated ordinary-Skin fixture has changed bilinear-resize output and maximum
raw-logit difference 0.033935; other five fixture adapter outputs match exactly.
This is bounded synthetic compatibility evidence, not medical equivalence.
Image pipeline versions were advanced, decoder runtime is included in saved
metadata, and the dashboard disallows numerical trends across decoder versions
or missing decoder evidence. Original historical results remain unchanged.

The local MySQL launcher also verifies the recorded process executable, data and
socket paths; a PID reused after reboot cannot establish database readiness.
It preserves occupied ports/live sockets and removes only a verified stale
project socket lock. A fake-binary test covers an unrelated live process, and
the existing local app/database were recovered through this path.

### Sky restoration and request-bound scanner (30 October 2026)

The restored white/sky-blue and navy/cyan tokens live in `frontend/product.css`;
IBM Plex and the established layouts remain. `frontend/scanner.js` supplies only
original decorative SVG art. `app.js` starts it at actual request preparation and
removes all graphics on completion, failure, Stop waiting or workspace clearing.
The processing status is indeterminate; the task list describes scope rather than
live server milestones. No canvas/photo, timer, network or storage API is used by
the scanner. CSS supplies two animations, paused on hidden-document signals and
disabled by both motion preferences. The existing canonical result is shown
without a minimum animation duration. Starting a retry clears the prior toast so
an earlier failure cannot obscure the result.

`browser-sky-scanner.js` adds 13 focused checks to the existing sequential runner,
including computed colors/contrast and five-width reflow across seven destinations,
four actual-request variants, interruption/error/success, focus, reduced motion
and stale-work disposal. Its PNG is synthetic; image requests are held before
inference and cancelled. A real synthetic questionnaire response verifies the
result handoff. This does not measure image-model speed or physical-device input.
