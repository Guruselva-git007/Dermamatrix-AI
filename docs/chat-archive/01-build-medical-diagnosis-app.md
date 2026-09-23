# Build medical diagnosis app

- Legacy task ID: `019fe9e1-2ab8-7c93-9d71-c73551dd90b0`
- Legacy workspace recorded by Codex: `/Users/gs/Documents/ChatGPT/Dermamatrix AI Powered Integumentary System`
- Created: 2026-08-10
- Archive status: PARTIALLY ACCESSIBLE / PARTIALLY ARCHIVED

## Preserved user requirements

The initial request asked for an academic dermatology application covering Skin, Hair, Nails, Sweat, image upload/analysis, risk score, explainability, lesion segmentation, classification, and a clean medical UI. Subsequent requirements clarified that it must remain one product with shared authentication, dashboard, navigation, profile, reports/history, recommendation/CDSS, risk/severity/PIRS framework, and storage—not four independent applications.

Later prompts also required that reference screens guide the real workflow and information architecture, not merely the color theme. They requested a presentation-ready path covering login, image input, real supported analysis where available, result evidence, guidance, saved reports, journey, profile, and sign-out. The historical request repeatedly prohibited fake doctors/products/ratings, fabricated confidence/results, unsupported normal-image claims, and unverified model promotion.

## Recovered technical record

- The transcript records the creation and refinement of the Flask/frontend/MySQL application, shared modality routing, auth, journey/report behavior, product discovery, doctor Maps handoff, and research-model boundary.
- Historical task evidence reports UI/auth/product refinements associated with commits including `84a5c2c`, `6d70fb6`, and `1e94598`.
- It records a later QA pass where the backend suite, MySQL account isolation, local stack, products API, browser guest flow, and live endpoints were exercised.
- It also records that broad general-photo diagnosis, generic confidence, and unexplained RMP-first behavior were challenged by user requirements. The current repository resolves this safely by exposing the dermatoscopic research route only when eligible and keeping other modalities honest about unavailable classifiers.

## Current reconciliation

The current canonical source contains one shared application with Skin, Hair, Nails, and Sweat routes, auth, profile/preferences, history, routines/check-ins, reports, knowledge guides, product discovery, and doctor handoff. It does **not** support a general diagnosis/segmentation/healthy/OOD pipeline for arbitrary images. The current model contract is the authoritative interpretation of the historical aspiration.

The task reader showed a very large paginated transcript. This archive preserves the initial request and accessible later evidence, but not a raw full export. Any verbatim archival requirement remains a manual action.
