# DermaMatrix AI

An educational prototype for integumentary-health screening workflows. It covers skin-and-sweat, hair/scalp, and nail concerns with image upload, consent, usability checks, a reported-concern priority, and a narrow dermatoscopic lesion research path.

> **Safety note:** This app is not a medical device and cannot diagnose disease. It is a college-project prototype designed to support, not replace, a qualified clinician.

The India-aligned guardrails and production requirements are documented in `docs/india-compliance-guardrails.md`. The app never issues a verified diagnosis or prescription; registered medical practitioner review remains mandatory.

## What an uploaded image can do today

- **Face, hair/scalp, nail, or ordinary skin photo:** image-usability feedback and a non-diagnostic discussion-priority based on what the user reports. It does not identify a deficiency or classify a disease.
- **Single, in-focus dermatoscopic skin-lesion image:** the optional HAM10000 ResNet-34 research model can show a research-label ranking and Grad-CAM attention after the user confirms the capture type. It shows an estimated likelihood only when a version-matched calibration artifact is configured. It is not lesion segmentation, a diagnosis, or clinical decision-making.

### Presentation-case mode

For the supervised project review only, the upload form has an opt-in
**Presentation case matching** checkbox. It recognises the exact original files
provided for the viva using a SHA-256 file fingerprint, then displays a
pre-authored teaching-case label, sourced discussion topics, routine, diet and
red flags. It does **not** use an AI classifier, does not match similar,
edited, or re-encoded photos, and never creates a probability, diagnosis,
patient risk score, prescription, or personal treatment plan. Leave the
checkbox off for every ordinary/patient image. See
[the presentation-case guide](docs/presentation-case-mode.md).

See [the model card](docs/model-card.md), [research-data protocol](docs/research-data-protocol.md), and [UNM atlas governance audit](docs/unm-atlas-governance.md) before any model training or evaluation. The public UNM Inclusive Dermatology Atlas is recorded as an educational reference only; it is not downloaded, scraped, or used for model training because public pages do not grant that permission.

## Run the complete app (local MySQL included)

```bash
python3 -m venv .venv
.venv/bin/pip install -r backend/requirements.txt
# Create backend/.env from backend/.env.example, then set a local MYSQL_PASSWORD.
bash backend/scripts/run_local_mysql.sh
.venv/bin/python backend/app.py
```

Open `http://127.0.0.1:8000`.

`run_local_mysql.sh` starts an isolated MySQL 8 instance on port `3307`, creates the `dermamatrix_ai` database, and grants only the app's local database privileges. It does not modify a separately installed system MySQL service.

## Run in VS Code

Open the `dermamatrix-ai` folder itself in VS Code. The repository includes a launch profile, task shortcuts, and an extension recommendation for the Python debugger.

1. Complete the local setup above, including `backend/.env`.
2. Select the project interpreter (`.venv/bin/python`, or the existing `.ml-venv/bin/python` if that is the environment you use) when VS Code asks.
3. Press **F5** and select **DermaMatrix: Run locally (MySQL)**. The launch profile starts the isolated MySQL service first and then opens the API in VS Code's integrated terminal.

For a terminal-only start, use `bash backend/scripts/run_app.sh`. It selects `.venv` (or the existing `.ml-venv` fallback), verifies Flask/MySQL dependencies, starts the isolated database, and serves the app at `http://127.0.0.1:8000`. In VS Code, **Terminal → Run Task → DermaMatrix: Verify local stack** confirms that Flask and MySQL are connected.

## Local account access

The entry screen supports account creation, sign-in, and a non-persistent guest workspace.

- Account passwords are never stored in plaintext. MySQL holds a salted Werkzeug password hash, and the browser receives an HTTP-only signed session cookie after a successful sign-in.
- `GET /api/auth/me` is the canonical session-restoration endpoint; it returns only the current signed-in user, profile, and non-clinical preferences. The backend derives ownership for routines, check-ins, saved assessments, PDFs, and clinical-review requests from that cookie—never from a browser-supplied patient ID.
- Appearance, notification, and reduced-motion preferences are durable per account through `/api/preferences`; guest preferences stay only in the current browser. Profiles are read and updated through `/api/profile`.
- The guest path does not create an account, persist health history, or retain analysis reports.
- For a durable local login session across Flask restarts, set a long random `FLASK_SECRET_KEY` in the ignored `backend/.env`. Without it, users can still sign in again with their saved email and password after a restart.

## Assessment architecture

The application keeps four modalities behind one account, history, and reporting system:

- **Skin, hair, and nails:** category selection → image preview → input/quality validation → scoped model adapter → normalised reported-concern priority → PIRS record → structured guidance → optional account-scoped history/PDF.
- **Sweat glands:** category selection → questionnaire → bounded/normalised inputs → transparent rule-contribution summary → normalised priority → PIRS record → structured guidance. It never accepts an image.

The browser uses an explicit assessment state machine (`IDLE`, `CATEGORY_SELECTED`, `INPUT_REQUIRED`, `INPUT_VALIDATING`, `PREPROCESSING`, `ANALYZING`, `RESULT_READY`, and `ERROR`). The processing panel is indeterminate until the backend returns; it does not invent a percentage or claim an unavailable model completed.

`backend/risk_service.py` provides shared `LOW`, `MODERATE`, `HIGH`, `URGENT`, and `UNCERTAIN` semantics. `backend/pirs_service.py` is a transparent, configurable prototype aggregation; it is explicitly **not clinically validated**. The model boundary stays honest: only the optional dermatoscopic HAM10000 research adapter can produce a research label/Grad-CAM, and only when its real weights and required capture attestation are present. A documented offline nail-model feasibility run exists but failed its predeclared internal and external thresholds, so it is not connected to the app. Hair, nail, segmentation, and sweat ML adapters remain unavailable until compatible validated models are configured.

## Source-linked condition guides

The Products page can load structured educational guides for common concerns including acne, eczema, psoriasis, fungal infection, seborrheic dermatitis, pattern hair loss, alopecia areata, nail fungus, nail changes that may warrant testing, blue nails, and excessive sweating. Guides are served by the backend knowledge boundary and include evidence links, general care context, medication discussion categories, red flags, and clinician-first notices. They are intentionally **not** image-model classes: opening a guide never changes an assessment result or infers a diagnosis from a photo.

## History and reports

Completed assessments are persisted only for the authenticated account. Guest assessments are returned for the current screen only; neither uploaded images nor guest assessment metadata are retained. Uploaded image pixels are never stored.

Registered users can open **My reports** and download a server-generated, account-scoped PDF discussion brief. The PDF contains stored assessment metadata and care-discussion guidance, but intentionally excludes images and overlays because the app does not retain them. **Download history PDF** exports that account's saved screening metadata, routines, self-reported check-ins, and profile history in one printable document.

The progress page is **input-driven monitoring**, not passive or continuous medical monitoring: it refreshes when the person saves a new screening or self-reported check-in. It does not claim healing, treatment effectiveness, or observation between entries.

## Doctor search and appointment handoff

For every result—and with clearer wording for `HIGH` or `URGENT` reported-concern priority—the app can open a nearby dermatologist search in Google Maps. The person may enter a city or grant browser location permission; coordinates are used only in the current browser to open Maps and are not persisted. Maps is the source of current listings, ratings, contact information, directions, and any clinic-specific appointment options. DermaMatrix does not rank, verify, create, or confirm bookings.

No prescription medicine, dosage, diagnosis-specific treatment, or product recommendation is generated from an uploaded image. The care library contains only general personal-care education with an explicit clinician/pharmacist guardrail.

## Product discovery and external shopping

The Products page and eligible general-care result cards use a backend-owned catalogue. It never uses an assessment label to select a product. Product and ingredient searches are user-initiated, while assessment-result cards remain limited to non-medicinal general-care categories. Each external handoff follows a transparent order: an explicitly configured partner URL, an explicitly configured direct product page, or a neutral exact search link. Partner status is labelled only when a partner URL is genuinely configured; price, stock, ratings, reviews, and product suitability are never claimed by DermaMatrix. High-priority or uncertain assessments defer result-linked product discovery. Configure optional local URLs only in the ignored `backend/.env` using the documented variables in `backend/.env.example`.

## Verification

Run the focused service tests with:

```bash
.venv/bin/python -m unittest discover -s backend/tests -v
```

The existing `.ml-venv` can be used in place of `.venv` in this workspace. In VS Code, run **DermaMatrix: Verify local stack** after F5 to confirm both Flask and MySQL are connected.

## Project layout

- `frontend/` – accessible, responsive web prototype with a complete assessment flow.
- `backend/` – Flask API, MySQL persistence, and a deterministic reported-concern prioritisation helper (not an image classifier).
- `backend/risk_service.py`, `backend/pirs_service.py`, `backend/report_service.py` – shared priority/PIRS/PDF-report domain boundaries.
- `backend/assessment_contract.py` – versioned patient-result contract that keeps model likelihood, symptom severity, care priority, disease risk, and urgency separate.
- `docs/` – model and safety documentation.
