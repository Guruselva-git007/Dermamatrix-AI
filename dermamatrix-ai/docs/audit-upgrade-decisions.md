# Audit upgrade: decisions, data and permissions

Source review: **22 October 2026**. This register preserves the local research
prototype. It records safe preparation and unresolved decisions; it is not a
privacy policy, binding terms, clinical approval, deployment authorization or
permission to delete data. No operator, monitored contact, eligibility age or
retention period has been invented.

## Operator decisions still required

| Finding | Decision needed | Smallest implementation after approval |
| --- | --- | --- |
| DM-03 | Identify the actual operator, approved notice/terms, service purpose, monitored privacy/rights channel and responsible responder. | Publish approved content and a functioning channel; bind server-controlled purpose/version evidence to what was actually shown. Technical processing explanations are not final legal terms. |
| DM-05 | Specify audience and markets; decide self-use, adult-on-behalf use and whether children may be assessed. | Enforce the approved eligibility/authority rule at account **and guest** API boundaries before protected processing, with the same UI explanation. |
| DM-06 | Define retention by record class, withdrawal effects, access/export scope, deletion exceptions, backup/hold handling and verification of requests. | Implement a separate authenticated rights workflow with owner isolation, complete applicable export and reviewed transactions. Do not treat the history PDF as that workflow. |
| DM-07 | Approve intended purpose, claims, populations/exclusions, qualified clinical review and any future clinician service. | Keep unsupported claims out of UI/reports; require real staff/assignment/review evidence before describing a clinical review as performed. |
| DM-08 | Select actual hosting topology and operational owners for secrets, HTTPS, CSRF, throttling, database protection, backups and incident response. | Verify configuration and synthetic abuse/restore checks on that topology. Local success does not attest a public host. |
| DM-09 | Approve the proposed distribution and use of each component with unresolved rights. | Include applicable notices and obtain missing permission/provenance; a downloadable weight or checksum does not grant commercial/clinical clearance. |

These decisions should be made separately from repairing the existing app. A
missing deployment decision need not block consent guards, accessible controls,
truthful copy, local fonts or documentation corrections.

## DM-05 — eligibility and representative-authority design

No new minimum age or identity-document collection is introduced. The uploader
and the person depicted or described are distinct. Registration eligibility
alone cannot cover guest processing or later adult-on-behalf assessments.

After approving the audience, represent only the necessary choices: self-use or
on behalf of another person, the applicable eligibility band if needed, and the
approved authority assertion for on-behalf use. Decide explicitly how unknown
eligibility, children in images, supervised demonstrations and existing accounts
are handled. Do not infer age or relationship from a photograph or silently
backfill historical authority. Do not collect an exact date of birth or identity
documents merely because a coarser decision is sufficient.

Apply the chosen server rule to registration, image assessment, Sweat
questionnaire and health-history persistence, including direct API requests.
Validate before application image reads/decoding/inference or protected writes;
retain separate image/JSON consent contracts. Rejection should explain the
permitted route without storing health input. Synthetic acceptance checks must
cover missing/malformed eligibility, each approved band, self/on-behalf cases,
unknown authority, guest/account parity, retries and withdrawal. **Eligibility
enforcement remains decision-dependent; this design is not enforcement.**

## DM-06 — stored-data inventory and rights design

### Account closure preparation — 28 October 2026

The existing password-confirmed, owner-scoped rights request and status view is
the technical entry point; its state remains `recorded_locally_pending_operator`.
It does not close an account or claim erasure. The independent account export,
session revocation and original/correction record inventory are implemented and
tested. No irreversible erasure endpoint or retention default is introduced.

Before executing closure, DM-06 must approve record-class retention, exceptions
and holds, withdrawal effects, backup expiry/restoration treatment, verification
and the responsible responder. The proposed executor must reauthenticate, show
consequences and applicable exceptions, obtain an explicit confirmation bound to
the account and request, lock/recheck the request, and record actor/time/approved
policy version and outcome. Its inventory includes assessments, routines,
check-ins, original actions and corrections, concern links/revisions, guide
bookmarks/revisions, feedback, consents, mail/reminder jobs and account/security
records. Health evidence must not be silently removed from historical exports.

Revoke sessions at the approved closure transition. A distinct, idempotent
policy-approved execution must account for failures and holds; do not treat a
queued request as successful erasure. Backups require an approved expiry/restore
plan so an old recovery copy cannot silently reactivate a closed account. Do not
invent a universal period or promise immediate deletion from immutable backups.
Use disposable synthetic accounts to test authorization, interrupted/repeated
execution, partial failure, audit readability and recovery before any approved
real-data execution. These policy-dependent execution tests remain deferred;
the existing request/reauthentication/export/isolation tests are software evidence
for the preparatory controls only.

This inventory comes from source/schema review, not inspection of real user
records. Source pixels and overlays are excluded from saved assessment JSON;
derived health information and reported history can still be sensitive data.

| Store | Data/purpose in the current prototype | Coverage in the bounded history PDF |
| --- | --- | --- |
| `users` | Patient identifier, name, email/phone, account timestamps and active state. | Current name/identifier/email; not every field. |
| `auth_accounts` | Account email, salted password hash and creation timestamp. | Not a full authentication export; never export a password hash/session secret as ordinary user data. |
| `medical_histories` | Past/current reported history; updates add entries, so older history remains. | Current profile history only. |
| `consent_records` | Owner, server purpose/version and acceptance time. | Not included as a complete consent history. |
| `assessments` and `analysis_records` | Assessment IDs/area, metrics/status/timestamps and detailed versioned derived result/evidence JSON; no source pixels. | At most 50 recent assessment summaries; not all JSON/metadata. |
| `clinical_review_requests` | Owner, assessment, queued status and request time. No clinician assignment/completed consultation. | Not a complete request history. |
| `care_routines` | Owner, condition label, routine, dates, notes. | At most 50 recent routines, summarized. |
| `progress_checkins` | Routine/owner/date, self-reported trend/scores/note; no stored image. | At most 100 recent check-ins, summarized. |
| `reports` | Owner, assessment, report identifier/type and generation time. | No complete generation ledger. PDFs are generated on demand. |
| `user_preferences` | Appearance, notifications and reduced-motion preference. | Not included. |
| `schema_migrations` | Technical schema-version record. | Not account data. |

The signed-in account owns persisted health records. Guest assessments are
non-persistent. Client previews/check-in comparisons stay browser-side; optional
maps/product/pharmacy navigation goes to external sites. Existing local/server
logs and any future backups require a separate operational inventory; this
source review does not establish what an uninspected public host retains.

**Implemented safe portions:** the history PDF and README describe its
50-assessment/50-routine/100-check-in limits and omitted classes. A separate
signed-in **Download local account data (JSON)** action uses
`GET /api/account-data/download` to copy all owned rows from the eleven known
account tables (`users`, `auth_accounts`, `medical_histories`, `consent_records`,
`assessments`, `analysis_records`, `clinical_review_requests`, `care_routines`,
`progress_checkins`, `reports`, `user_preferences`) without those PDF limits.

The technical copy starts a read-only, repeatable-read consistent MySQL snapshot
before authentication reads, derives ownership from the signed-in session and
uses explicit column allowlists. It includes older health histories, the full
owned consent/request history, preferences and saved result lineage/details.
Original `*_json` values remain intact, including malformed historical JSON
marked with a field-status annotation. Counts accompany each table. The response
uses `dermamatrix-local-account-data-v1` and reports its scope/exclusions;
unsupported records fail the whole download rather than silently truncating
data. Snapshot cleanup runs on success and failure. Downloading changes no
stored record or consent state.

Password hashes, credentials/session secrets, other accounts' rows, unowned
guest results, source-image files/overlays, system logs, backups, configuration
and schema-migration records are excluded. This is a complete technical copy
of the declared account-table/column scope, **not** a complete legal
access-request service or a promise that every possible applicable record or
data right is covered. No retention, withdrawal, erasure or monitored rights
process is established by the download. Future schema work must update its
allowlist and completeness tests. Continue to approve broader rights-request
scope and operational handling separately.

Withdrawal needs defined purpose/state semantics and a check at every covered
future write; it must not falsely imply automatic deletion of earlier data.
Erasure needs an approved table/dependency order, transaction rollback, backup
and legal-hold rules, request ownership checks and recovery procedures. Do not
add a destructive endpoint before those semantics are agreed. Use synthetic
accounts exceeding all PDF limits, a second account for isolation, interrupted
transactions, concurrent exports, retries, holds and restore tests. Preserve all
real records while designing and verifying this work.

## DM-07/08 — clinical and public-hosting boundaries

The safe DM-08 browser boundary now checks unsafe API requests using exact
Origin, full-URL Referer origin as a fallback, and Fetch Metadata where supplied.
The report-PDF GET and its automatic HEAD method also reject cross-origin
browser entry because the shared handler updates
report-ledger metadata. Local Host values are restricted to `localhost`,
`127.0.0.1` and `::1`; no LAN exposure or arbitrary Host-based DNS-rebinding
origin is accepted. Headerless command-line/legacy requests remain compatible,
which is an explicit limitation rather than a full CSRF guarantee.

Explicit production mode additionally requires operator-configured
`DERMAMATRIX_TRUSTED_ORIGINS` for exact verified application origins, alongside
the persistent-secret and secure-cookie prerequisites. It fails startup when
those origins are absent/malformed; no public origin is invented. Actual WSGI
scheme/host, proxy trust and health-check topology need separate verification.
No `ProxyFix`, arbitrary forwarded-header trust, shared throttling, inference
budget, transport/backup/incident control or public deployment is introduced
by this local improvement. See [security](security.md) for compatibility and
the [deployment notes](railway-deployment.md) for the required configuration.

A saved `awaiting_rmp_review` request is a queued local record. It does not
assign a doctor, schedule care, confirm review or provide medical approval.
Research rankings, uncertainty, PIRS, concern and reported severity remain
separate in detailed results/history/reports. A research disclaimer is not a
regulatory classification decision. Intended purpose, advertised claims,
population, external validation and professional governance remain open before
medical/patient-facing promotion. No classifier, scoring formula or checkpoint
is changed to manufacture compliance.

For public hosting, verify a persistent high-entropy secret shared across
workers/restarts; secure cookies over HTTPS; documented proxy trust; origin/CSRF
protection appropriate to cookie authentication; shared login/guest throttling;
bounded expensive inference/concurrency; least-privilege database access and
transport; protected backup/restore; and an accountable incident process. Keep
localhost development usable. Test with synthetic traffic/data, not intrusive
requests to a live service or production database. A fail-fast configuration
guard, where implemented, is preparation rather than a substitute for these
controls. Actual provider/topology, monitoring and recovery remain unverified
until separately tested. See [security](security.md) and
[deployment notes](railway-deployment.md).

## DM-09 — permission register

Evidence below records identity and available terms, not legal clearance.
Keep code/architecture rights distinct from weight/training-data/image rights.
No private image was opened or uploaded to compile this register; no dataset or
model was downloaded or trained.

| Component | Version/source evidence | License evidence and remaining restriction |
| --- | --- | --- |
| DM Sans; IBM Plex Sans; IBM Plex Mono | Same requested families/weights and all 23 original WOFF2 subsets; [local source/hash manifest](../frontend/assets/fonts/sources.json). | Unmodified self-hosted files. OFL 1.1 notices [DM Sans](../frontend/assets/fonts/OFL-DM-Sans.txt) and [IBM Plex](../frontend/assets/fonts/OFL-IBM-Plex.txt) retained from official `google/fonts` revision `45e3d5269e4a17d823f6d84470bc084dc5ae46f6`. Include notices with distribution; retain reserved-name restrictions. |
| Ordinary-Skin EfficientNet weight | [Pinned model card](https://huggingface.co/RevelaCap/clinical-skin-condition-v1/blob/a614ae0c12e8590f06d4f25b529b6b568a517903/README.md); installer pins revision and SHA-256 `eba9a581505c60cee98152c790c4113a1549c691248d518cc5d1e7097feb20bc`. | Model card declares MIT; root inventory has no standalone LICENSE/copyright grant. Card says educational, not patient-facing without independent validation; mixed SCIN/Fitzpatrick17k provenance. Obtain adequate notice/weight/data-use clarification before broader redistribution/use; code licensing alone does not clear data rights. |
| Nail ConvNeXt Tiny weight | [Pinned model card](https://huggingface.co/shibarashii/nail-disease-detection/blob/661603d35bab2904055d4d4a943bf305b03a59f9/README.md); installer pins revision and SHA-256 `6c58cd98c9368268115d00f6acd6d1f03dba73132eaacd15cbfa9cf9dfb5bf19`. | Card declares MIT but provides no standalone license/copyright text, training-source provenance, patient split or published training transform. Do not infer clinical/commercial data permission; require clarification for the proposed use. |
| Dermatoscopy ResNet-34 weight/repository | [Upstream repository](https://github.com/ptschandl/dermatoscopy_resnet34_nmed_2020); Docker pins artifact SHA-256 `a800e9df6330d377ed4a37b32e2cbd78821da5e9c3980a30bd42155d097f0250`. | Repository [MIT license](https://github.com/ptschandl/dermatoscopy_resnet34_nmed_2020/blob/main/LICENSE) and [retained notice](third-party-notices/dermatoscopy-MIT.txt); README restricts its described purpose to education/research, not medical advice. Underlying HAM10000/ISIC data rights and proposed weight use need their own review. |
| Model architecture/code | ResNet/EfficientNet/ConvNeXt from installed torchvision 0.29.0 and torch 2.14.0. | Installed distributions include BSD/project and third-party notices. Architecture/code licenses do not license every training image or certify resulting weights. |
| SCIN, rejected local nail experiment and local research archives | Existing [research-data protocol](research-data-protocol.md), [dataset registry](dataset-registry.md) and source-specific dated records. | SCIN Data Use License; Han Figshare release records CC BY 4.0; local mixed archives retain unresolved provenance. Rejected experimental checkpoints are not runtime models. No new download, training or permission expansion. |
| UNM atlas | [Existing governance audit](unm-atlas-governance.md). | Blocked pending written ML authorization. No crawling, dataset extraction or model training is authorized by public availability. |
| Teaching-case fingerprints/content and private presentation files | `backend/presentation_case_service.py`, [presentation guide](presentation-case-mode.md), retained local originals. | A hash is not image permission or a verified diagnosis. Keep private images out of Git/distribution; obtain source-image/content permission and any necessary consent before sharing. Reference links do not grant rights to reproduce an atlas or article. |
| Icons/illustrations/external destinations | Current Unicode/CSS illustrations; explicit maps, shopping/pharmacy and source links. | Preserve the generated/local illustration provenance; do not assume external logos, images, medical text or retailer media are licensed. Linked sites keep their own terms; navigation is not a partnership or asset license. |

The existing `.venv` was also inventoried using `importlib.metadata` without
application/ML imports, installation or downloads. The reproducible
[inventory script](../../local-artifacts/audit-upgrade-2026-10-22/dependency_inventory.py)
and [local JSON evidence](../../local-artifacts/audit-upgrade-2026-10-22/runtime-dependency-inventory.json)
record actual versions, metadata-declared source URLs, license expressions or
license hints, active dependencies and notice paths/SHA-256 values. Reproduce
from `dermamatrix-ai/` with
`.venv/bin/python ../local-artifacts/audit-upgrade-2026-10-22/dependency_inventory.py`.
These local evidence files remain ignored project records, not a public package
or license-clearance certificate.

For this **Darwin arm64 / CPython 3.14.3** environment, ten direct requirements
expand to **37 installed runtime distributions**: ten direct plus 27 transitive.
All 40 active `Requires-Dist` edges satisfy their installed-version constraints;
399 edges are excluded by environment markers or unselected extras. The sole
other installed distribution, `pip`, is not reachable from the declared runtime
roots; that is an environment-tooling distinction, not an assertion that all
unreachable packages are development dependencies. No runtime dependency or
declared notice file was missing/unreadable.

The 37 runtime distributions expose **188 notice/license files**, with hashes
covering 918,797 bytes; 19 are declared outside `.dist-info` and add bundled
component evidence. Seventeen packages omit a machine-readable
`License-Expression`; their available license text/hints/classifiers and notices
are retained rather than inventing an SPDX expression. Bundled notices under
NumPy, SciPy, torch, setuptools and other distributions are evidence, not proof
that every embedded binary/OS component is fully licensed for every use. Direct
packages are summarized below; the JSON covers the transitive closure and
inactive-marker evidence.

| Package | Installed version | Installed license evidence |
| --- | --- | --- |
| Flask | 3.1.3 | BSD-3-Clause; `flask-3.1.3.dist-info/licenses/LICENSE.txt` |
| gunicorn | 23.0.0 | MIT; `gunicorn-23.0.0.dist-info/LICENSE` |
| Pillow | 11.3.0 | MIT-CMU; `pillow-11.3.0.dist-info/licenses/LICENSE` |
| NumPy | 2.5.3 | BSD-3-Clause plus bundled licenses; `numpy-2.5.3.dist-info/licenses/LICENSE.txt` and subcomponent notices |
| matplotlib | 3.11.2 | Project license agreement; `matplotlib-3.11.2.dist-info/LICENSE` |
| PyMySQL | 1.2.3 | MIT; `pymysql-1.2.3.dist-info/licenses/LICENSE` |
| torch | 2.14.0 | BSD and multiple bundled license expressions; `torch-2.14.0.dist-info/licenses/LICENSE` and third-party notices |
| torchvision | 0.29.0 | BSD; `torchvision-0.29.0.dist-info/LICENSE` |
| scikit-learn | 1.9.1 | BSD-3-Clause; `scikit_learn-1.9.1.dist-info/licenses/COPYING` |
| reportlab | 4.5.1 | BSD; `reportlab-4.5.1.dist-info/licenses/LICENSE` |

For any release, retain applicable notices from the actual built distributions
and include font/model notices. This local closure is neither a dependency lock
nor a vulnerability scan. Different platforms/Python versions, Docker, optional
extras, undeclared/dynamic imports, OS libraries and embedded binaries need
their own inventory. The remaining permission work concerns exact proposed
distribution and unresolved rightsholder/weight/training-data/teaching-image
terms; no private presentation image or patient data is cleared for sharing.
Public clinical/commercial deployment remains deferred. The prototype and its
dependencies are not fully cleared for every proposed use by this register.
