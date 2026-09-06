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
| Assessment result | existing result dialog, `renderAnalysisDashboard()` and `renderResultOverview()` | normalized assessment response | result can be reviewed immediately; no image storage is added |
| My Journey | `progress` section and `renderProgress()` | `GET /api/routines`, `GET /api/progress-checkins`, `GET /api/analysis-history` | routines, self-reported check-ins, assessment summaries |
| Reports | `renderReportRegister()` | `GET /api/reports/<assessment_id>/download`, `GET /api/history/download` | PDFs are generated from account-scoped stored metadata |
| Care Hub | `products` section and `renderDiscoveryCatalog()` | static, educational catalogue; `/api/products` remains available | no medical ranking or diagnosis-specific product recommendation |
| Find a Doctor | `support` section and `openDirectorySearch()` | browser hand-off to Google Maps | location stays in browser state; doctor listings/availability are not copied into the database |
| Accounts and profile | auth and profile modals | `/api/auth/*`, `/api/profiles` | salted password hash, account/profile data, and consented history in MySQL |

## Assessment data path

```text
selected area
  → image upload (Skin/Hair/Nails) OR questionnaire (Sweat)
  → frontend validation and consent
  → Flask route
  → modality router / quality checks / configured model adapter
  → normalized ML, uncertainty, reported-priority, PIRS, CDSS, and recommendation payload
  → result dialog
  → optional account-scoped metadata persistence
  → My Journey and PDF export
```

Sweating remains questionnaire-only. The UI does not expose image upload for
that path. Hair and nail workflows retain their existing adapter-status notices;
the UI does not imply a trained classifier where one is not configured.

## UX refinement boundaries

The refinement changed only user-facing terminology, page hierarchy, responsive
layout, empty states, and result presentation. It deliberately did **not** change:

- Flask routes, request formats, authentication, or MySQL schema;
- model execution, risk/PIRS calculations, uncertainty behavior, calibration,
  segmentation, Grad-CAM, or clinical-decision-support logic;
- report-generation, appointment hand-off, or affiliate policy;
- the no-image-retention policy.

The result presentation keeps estimated likelihood, reported symptom severity,
reported-concern priority, and model certainty as distinct fields. When a
calibrated condition likelihood is unavailable, the UI displays “Not available”
instead of presenting a raw model score as a medical probability.

## Consumer navigation

```text
Home → Check My Health → Assessment result → Care Hub / Find a Doctor / My Journey
```

Each destination reuses the existing SPA page key (`dashboard`, `home`,
`products`, `support`, `progress`) to preserve bookmark, history, and API behavior.
Only the visible names changed: Home, Check My Health, My Journey, Care Hub, and
Find a Doctor.
