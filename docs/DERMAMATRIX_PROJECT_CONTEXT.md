# DermaMatrix AI — permanent project context

Last reconciled: 2026-09-23

## Project identity and authority

- Canonical local repository: `/Users/gs/Chatgpt/Dermamatrix-AI`
- Runnable application root: `dermamatrix-ai/`
- Canonical GitHub remote: `https://github.com/Guruselva-git007/Dermamatrix-AI.git`
- Baseline branch and commit: `main` at `5502d6277b7104dacb3089ce2ef8b007dd91be6c` (`Add persistent local app launcher`)
- Product type: an educational, non-diagnostic integumentary-health screening prototype for a final-year presentation. It is not a medical device.

The current verified source in this repository takes priority over earlier chat claims, old working copies, and historical assistant statements. Historical records are preserved in `docs/chat-archive/` and the migration audit; they do not by themselves prove a feature is current.

## Architecture

The application is one Flask service serving a vanilla HTML/CSS/JavaScript frontend. It uses an isolated local MySQL instance for registered-account persistence and account-scoped reports/history. There is no separate JavaScript framework, frontend build system, or second application tree.

| Layer | Current implementation | Status |
| --- | --- | --- |
| Browser UI | `frontend/index.html`, `frontend/app.js`, and layered CSS files | VERIFIED |
| HTTP API and static serving | `backend/app.py` Flask application | VERIFIED |
| Authentication/session | MySQL-backed accounts, Werkzeug password hashes, HTTP-only signed session cookie | VERIFIED by test and MySQL integration test |
| Profile/preferences/history/routines | Account-scoped Flask routes and MySQL tables | VERIFIED by test; browser persistence not re-exercised in this migration |
| Reports | In-memory account-scoped PDF generation; no uploaded pixels in PDFs | VERIFIED by tests |
| Model boundary | Model registry plus modality router and normalized assessment contract | VERIFIED |
| Local launch | Gunicorn helper, macOS launch agent installer, and Finder launcher | VERIFIED by syntax/regression/live health checks |

Important API groups are health/model registry, account/session, profiles, routines/check-ins/history, saved assessments/PDFs, products/knowledge, image assessments, and sweat-questionnaire assessments. The authoritative route declarations remain in `backend/app.py`.

## Product and UX intent

Historical user requirements consistently establish one shared product—not four independent apps—with a consumer-facing, compact, presentation-ready medical interface. The intended journey is:

`entry/authentication → dashboard → health-area choice → image or questionnaire input → explicit result state → guidance → optional account-scoped history/report → external care handoff`

Shared UX requirements retained from legacy work:

- Skin, Hair/scalp, Nails, and Sweat share authentication, navigation, profile, reports, journey, products, and care-support surfaces.
- Results must keep model evidence, user-reported severity, assessment concern indicator, PIRS, urgency, and education distinct.
- Technical/model detail stays subordinate to clear patient-facing guidance.
- Product discovery is user-led or limited to non-medicinal general-care categories; it does not invent price, rating, stock, diagnosis-specific suitability, or an image-derived prescription.
- Doctor/maps and appointment handoff use external current listings; DermaMatrix does not create or confirm bookings.
- Images are not retained after assessment. Guest work is not persisted.

The current browser guest dashboard and assessment entry route were inspected during this migration. A minor reconciliation finding is open: the initial assessment label reads `STEP 1 OF 3` while four visible stage labels are listed. No UI change was made because this migration is documentation/reconciliation only.

## Assessment and clinical-safety contract

The canonical result schema is `assessment-result-v1.5`. It distinguishes `condition_detected`, `healthy`, `uncertain`, `category_mismatch`, `unsupported_image`, and `poor_quality`. These are semantic workflow states, not diagnoses.

- Input checks cover format, size, pixels, basic quality, declared route, and consent.
- `healthy` is reserved for a compatible model with independently validated normal-appearance evidence. No current general image route emits it.
- `OUT_OF_DISTRIBUTION` is reserved for a real future detector. The current runtime does not claim an OOD detector.
- PIRS and the 0–100 assessment concern indicator are transparent prototypes, not clinical risk/prognosis scores.
- A high reported concern is not overridden by model output.
- Presentation-case matching is exact SHA-256 teaching-case matching only. It is not similarity search, AI inference, probability, diagnosis, or treatment selection.

See `dermamatrix-ai/docs/capability-contract.md`, `assessment-risk-engine.md`, `production-input-and-result-contract-20260923.md`, `india-compliance-guardrails.md`, and `security.md` for the authoritative detailed contracts.

## ML and data inventory

| Component or dataset | Current state | Runtime connection |
| --- | --- | --- |
| HAM10000 ResNet-34 | Local 81 MB research weight present; SHA-256 `a800e9df…097f0250`; seven dermatoscopic lesion classes | RESEARCH_ONLY; available only for an attested dermatoscopic single-lesion image |
| Grad-CAM | Real attention visualization from the scoped research adapter | Available only when that adapter actually runs; not segmentation |
| Calibration | Runtime accepts only a version-matched independent-validation artifact | NOT_CONFIGURED; no likelihood claim without it |
| OOD detector | No fitted runtime detector | NOT_CONFIGURED |
| SCIN ResNet-18 two-class clinical-photo experiments | Held-out balanced accuracy 0.414980, macro-F1 0.405670, AUROC 0.437247 | REJECTED_FOR_APPLICATION_INFERENCE |
| Local seven-class ResNet-18 candidate | Balanced accuracy 0.546283, macro-F1 0.441332 in the documented comparison | Candidate not promoted; not runtime |
| Local three-class dermoscopy ResNet-18 | Locked-test macro-F1 0.728377; material melanoma weakness and governance/OOD/runtime gaps | REJECTED_FOR_APPLICATION_INFERENCE |
| Figshare nail ResNet-18 | Internal/external balanced accuracy 0.592593 / 0.513777, below thresholds | REJECTED_FOR_APPLICATION_INFERENCE |
| Hair/scalp classifier | No governed deployable training data, weight, calibration, or evaluation | NOT_AVAILABLE |
| Segmentation model | No confirmed governed image/mask pairing or deployed U-Net/other segmentation weight | NOT_AVAILABLE |
| Sweat workflow | Transparent questionnaire contribution and prioritization rules | QUESTIONNAIRE_ASSESSMENT; not XGBoost/SHAP/validated diagnosis ML |
| UNM Inclusive Dermatology Atlas | Governance reviewed | BLOCKED pending written ML authorization; not scraped, downloaded, or trained |

The current live `/api/model-registry` confirms the same boundary: Skin research inference is available; Hair and Nails are unavailable; Sweat is questionnaire-only. Current source and live checks must prevail over older prompts that requested universal disease classification, generic confidence, U-Net segmentation, XGBoost, or normal-image claims.

Raw data, experiment checkpoints, manifests containing source-sensitive data, calibration files, and heavyweight outputs are intentionally outside Git. The key immutable local roots are documented in `DERMAMATRIX_FILE_INVENTORY.md`.

## Database, configuration, and local launch

The local database is the ignored `dermamatrix-ai/backend/.local-mysql/` tree. Its database contains the account, consent, preference, medical-history, assessment, analysis-record, routine, check-in, report, clinical-review-request, and schema-migration tables. It is a local artifact, not a portable Git database dump.

`backend/.env` exists and declares every name present in `backend/.env.example`; values were deliberately neither read into this record nor exposed. The template-covered names are:

`MYSQL_HOST`, `MYSQL_PORT`, `MYSQL_USER`, `MYSQL_PASSWORD`, `MYSQL_DATABASE`, `FLASK_SECRET_KEY`, `FLASK_SESSION_DAYS`, `FLASK_SESSION_SECURE`, `SEGMENTATION_MODEL_PATH`, `AFFILIATE_MOISTURISER_URL`, `AFFILIATE_SUNSCREEN_URL`, `AFFILIATE_SCALP_CLEANSER_URL`, `AFFILIATE_NAIL_CARE_URL`, `PRODUCT_MOISTURISER_URL`, `PRODUCT_SUNSCREEN_URL`, `PRODUCT_SCALP_CLEANSER_URL`, and `PRODUCT_NAIL_CARE_URL`.

Additional runtime/control names referenced by source include `DERMAMATRIX_PORT`, `DERMAMATRIX_WEB_CONCURRENCY`, `DERMAMATRIX_START_MYSQL`, `DERMAMATRIX_MYSQL_PORT`, `DERMAMATRIX_MYSQLX_PORT`, `DERMAMATRIX_HEALTH_URL`, `DERMAMATRIX_CALIBRATION_PATH`, `DERMAMATRIX_RUN_MYSQL_INTEGRATION_TESTS`, `MYSQL_SOCKET`, and `MYSQL_BIN`.

For the standard local application workflow:

```bash
cd /Users/gs/Chatgpt/Dermamatrix-AI/dermamatrix-ai
bash backend/scripts/run_app.sh
```

`Start DermaMatrix.command` is the macOS Finder entry point. It installs or refreshes a current-user loopback-only launch agent and opens the app at `http://127.0.0.1:8000/`. Opening `frontend/index.html` with `file://` is deliberately not a valid app workflow; the client redirects to the loopback app.

## Verified current state — 2026-09-23

- `main` and `origin/main` were identical at the baseline commit after `git fetch --all --prune`; one local and one remote branch exist, with no tags and no divergence.
- `git fsck --full --no-reflogs` completed without reported object errors.
- 86 unit/regression tests passed; the suite's one MySQL test is opt-in. The opt-in MySQL account/session/profile-preferences/isolation test was then run and passed.
- JavaScript syntax, Python compilation, both macOS launcher script syntax checks, `git diff --check`, `/api/health`, static homepage serving, and `/api/model-registry` passed.
- The live health response reported `mysql-connected`; the local HAM10000 research weight was present and the live model registry reported Skin research inference available.
- A guest dashboard and assessment-entry browser check had no console errors. No image was submitted during this migration verification, so an end-to-end current-session model inference claim is intentionally not made here.

## Known state, gaps, and historical decisions

| Item | Classification | Evidence |
| --- | --- | --- |
| Dermatoscopic Skin research path | VERIFIED RESEARCH_ONLY | Local weight + live registry + tests; no clinical validation |
| General Skin, Hair, and Nail disease classification | MISSING BY DESIGN | Capability contract and tests prevent fabricated labels |
| Hair/Nail runtime ML | NOT_AVAILABLE | No accepted compatible model; nail experiment rejected |
| Segmentation | NOT_AVAILABLE | No deployed validated segmentation weight |
| Sweat diagnosis model / XGBoost / SHAP | NOT_AVAILABLE | Questionnaire rules only |
| PIRS, concern indicator, and reported priority | VERIFIED PROTOTYPE | Explicitly non-clinical; covered by tests |
| Auth/profile/session database integration | VERIFIED | Opt-in MySQL test passed |
| Reports/history PDF generation | VERIFIED | Service tests passed |
| Doctor/maps | PARTIALLY WORKING | External Maps handoff exists; no provider verification or booking |
| Appointments | MISSING | External handoff only; no booking system |
| Password-reset email delivery | MISSING | No configured delivery service |
| Public deployment | UNVERIFIED | Railway deployment configuration exists; no live deployment verified in this migration |
| Raw legacy transcript export | OPEN | See `docs/chat-archive/INDEX.md` |

Superseded or rejected approaches must remain documented rather than be silently reintroduced: RMP-first stopping behavior, generic/general-photo disease claims, fake confidence/healthy/OOD states, ungoverned dataset ingestion, the rejected SCIN and nail candidates, and the unpromoted local ResNet-18 candidates.

## Current priorities and open questions

1. Preserve the present capability boundary unless new governed evidence supports a change.
2. Resolve the four-stage/three-count visual discrepancy in a separately authorized bug-fix task.
3. Export raw transcript data or selected attachment files for the partially archived legacy chats if a verbatim permanent archive is required.
4. Before any public deployment, supply deployment-account authority and production MySQL/environment values; do not commit them.
5. Before adding a Hair, Nail, segmentation, clinical-photo, normal-image, OOD, severity, or disease-risk model, complete the documented data-governance, split, evaluation, calibration, external-validation, and clinical-review gates.
