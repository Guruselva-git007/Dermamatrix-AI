# Full-stack flow audit

This document records the existing application flow that was preserved during the
consumer UX refinement. It is an architectural map, not a claim of clinical
validation.

## Browser → service → data flow

| Consumer surface | Frontend implementation | Service contract | Stored data |
| --- | --- | --- | --- |
| Home | `dashboard` section and `renderDashboard()` | existing progress/history reads | account-scoped assessment metadata, routines, check-ins |
| Check My Health — skin/hair/nails | `home` / `screen` sections and `analyze()` | `POST /api/assessments` multipart request | assessment metadata only for a signed-in account; uploaded pixels are not retained |
| Check My Health — sweating | same screen, questionnaire mode | `POST /api/sweat-assessments` JSON request | the same account-scoped summary metadata when signed in |
| Assessment result | existing result dialog, `renderPatientResult()`, `renderAnalysisDashboard()` and `renderResultOverview()` | `assessment-result-v1` plus legacy-compatible technical fields | result can be reviewed immediately; no image storage is added |
| My Journey | `progress` section and `renderProgress()` | `GET /api/routines`, `GET /api/progress-checkins`, `GET /api/analysis-history` | routines, self-reported check-ins, assessment summaries |
| Reports | `renderReportRegister()` | `GET /api/reports/<assessment_id>/download`, `GET /api/history/download` | PDFs are generated from account-scoped stored metadata |
| Products | `products` section and `renderDiscoveryCatalog()` | backend-owned user-initiated product/ingredient discovery with neutral external links | no image-derived product recommendation, prescription, dosage, medical ranking, or claimed retailer data |
| Find a Doctor | `support` section and `openDirectorySearch()` | browser hand-off to Google Maps | location stays in browser state; doctor listings/availability are not copied into the database |
| Accounts and profile | auth and profile modals | `/api/auth/*`, `/api/profiles` | salted password hash, account/profile data, and consented history in MySQL |

## Assessment data path

```text
selected area
  → image upload (Skin/Hair/Nails) OR questionnaire (Sweat)
  → frontend validation and consent
  → Flask route
  → modality router / quality checks / configured model adapter
  → `assessment-result-v1` (condition likelihood, symptom severity, care priority, disease-risk availability, urgency, XAI, CDSS)
  → result dialog
  → optional account-scoped metadata persistence
  → My Journey and PDF export
```

Sweating remains questionnaire-only. The UI does not expose image upload for
that path. Hair and nail workflows retain their existing adapter-status notices;
the UI does not imply a trained classifier where one is not configured.

## UX refinement boundaries

The refinement changed only user-facing terminology, page hierarchy, responsive
layout, empty states, and result presentation. The result adapter additionally
persists one normalized presentation contract. It deliberately did **not** change:

- Flask routes, request formats, authentication, or MySQL schema;
- model execution, risk/PIRS calculations, uncertainty behavior, calibration,
  segmentation, Grad-CAM, or clinical-decision-support logic;
- appointment hand-off, affiliate policy, or the underlying report data policy;
- the no-image-retention policy.

The result presentation keeps estimated likelihood, self-reported symptom
severity, reported-concern care priority, disease-risk availability, urgency,
and model certainty as distinct fields. When a calibrated condition likelihood
or a validated disease-risk model is unavailable, the UI displays “Not
available” instead of presenting a raw model score or care-priority number as a
medical probability or disease risk.

## Consumer navigation

```text
Home → Check My Health → Assessment result → Products / Find a Doctor / My Journey
```

Each destination reuses the existing SPA page key (`dashboard`, `home`,
`products`, `support`, `progress`) to preserve bookmark, history, and API behavior.
Only the visible names changed: Home, Check My Health, My Journey, Products, and
Find a Doctor.
