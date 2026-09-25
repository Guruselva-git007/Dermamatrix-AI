# DermaMatrix AI viva guide (current code)

This guide describes the running local project after the Skin and Nail research adapters were integrated. Use the live `/api/model-registry` endpoint as the final capability check. Some older research notes and the September presentation runbook describe earlier builds.

## A 60-second introduction to say aloud

"DermaMatrix AI is a local educational screening-support web app for skin, hair/scalp, nail, and sweating concerns. It has a plain HTML/CSS/JavaScript frontend, a Flask Python API served by Gunicorn, and MySQL for consented account history. Image uploads are decoded and quality checked locally. Category routing sends ordinary Skin photos to a five-class EfficientNet-B0 research checkpoint, attested dermoscopy to a seven-class ResNet-34 checkpoint, and declared Nail close-ups to a ten-class ConvNeXt Tiny checkpoint. Hair has no deployable condition classifier, and Sweat uses a transparent questionnaire. The backend preserves raw logits, top-five rankings, image measurements, reported symptoms, PIRS, and an assessment concern indicator as separate evidence. Results are research support, not medical diagnoses or calibrated disease probabilities. Guest results are temporary; signed-in users can save metadata, track check-ins, and download reports without storing uploaded image pixels."

## Architecture at a glance

```text
Browser: HTML + CSS + JavaScript, fetch/FormData, result and progress UI
    ↓ HTTP on 127.0.0.1:8000
Gunicorn → Flask app.py → validation + assessment_router.py
    ├─ local PyTorch/TorchVision model adapter by category, when available
    ├─ Pillow/NumPy image measurements and optional dermoscopy Grad-CAM
    ├─ reported priority + symptom severity + PIRS + concern indicator
    ├─ canonical_evidence.py → assessment_contract.py → result JSON
    ├─ recommendations/condition knowledge + ReportLab PDF
    └─ PyMySQL → local MySQL 8 for signed-in metadata only
```

| Part | Current implementation | Where to point in code |
| --- | --- | --- |
| Frontend | Responsive HTML, CSS, vanilla JavaScript; no React framework | `frontend/index.html`, `frontend/app.js`, `frontend/reference.css` |
| API/server | Flask routes, Gunicorn local server | `backend/app.py`, `backend/scripts/run_app.sh` |
| Database | MySQL 8, PyMySQL, InnoDB tables and additive migrations | `backend/app.py`, `backend/scripts/run_local_mysql.sh` |
| Image/ML | Pillow, PyTorch, TorchVision, local checkpoint files | `backend/*classifier.py`, `backend/assessment_router.py` |
| Assessment contracts | Versioned canonical evidence and presentation object | `backend/canonical_evidence.py`, `backend/assessment_contract.py` |
| Reports | Server-generated PDFs from saved metadata | `backend/report_service.py` |
| Tests | Python `unittest`, Flask test client, opt-in MySQL integration test | `backend/tests/` |

## Actual image and questionnaire routes

| Selected area | Local processing | Honest limit |
| --- | --- | --- |
| Ordinary Skin photo | EfficientNet-B0, five broad classes, 224×224 RGB and ImageNet normalization | Research ranking. Publisher reports 0.67 balanced accuracy overall and lower SCIN smartphone-subset results. No normal class, calibration, OOD detector, or clinical validation. |
| Attested single-lesion dermoscopy | HAM10000 ResNet-34, seven lesion classes, short-edge resize 280, center crop 224, tensor in [0,1]; Grad-CAM | Only for genuinely dermoscopic images. No installed calibration or OOD detector. Grad-CAM is model attention, not lesion proof. |
| Declared Nail close-up | ConvNeXt Tiny, ten nail classes; adapter assumes short-edge resize 236, center crop 224 and ImageNet normalization | Research ranking. Upstream training transform and external validation are unpublished. "Healthy Nail" is not a verified normal-health result. |
| Hair/scalp | Image quality, local frame measurements, reported concern and guidance | No deployable Hair disorder checkpoint/class map. Does not name a disease from the photo. |
| Sweat | Questionnaire with explicit rule contributions | No sweat image model, no trained XGBoost, no SHAP. |

The ordinary Skin model's five labels are Eczema / dermatitis, Urticaria / allergic reaction, Folliculitis / acne-like, Psoriasis / papulosquamous, and Lesion — dermoscopic review recommended. The last is a referral prompt, not a cancer diagnosis. Dermoscopy class codes are `akiec`, `bcc`, `bkl`, `df`, `mel`, `nv`, `vasc`, with human-readable labels in `lesion_classifier.py`. Nail's ten labels are Melanonychia, Beau's Lines, Blue Nail, Clubbing, Healthy Nail, Koilonychia, Muehrcke's Lines, Onychogryphosis, Pitting, and Terry's Nails.

The clinical Skin and Nail checkpoints were sourced publicly and pinned by revision and SHA-256; they are **not claimed to have been trained by this project**. They are installed into local DermaMatrix adapters. Assessment inference has no provider/API-key call. See `local-model-source-and-validation-20260925.md` for source, mapping, and local checks.

## End-to-end flow to draw on a board

1. User selects an area, supplies a photo and image context, gives upload consent, and may enter duration, discomfort, change, and symptoms. Sweat uses a questionnaire instead of an image.
2. `POST /api/assessments` checks extension and decoded format, file size (10 MB), pixels (16 million), nonempty content, EXIF orientation, and RGB conversion.
3. Image quality checks resolution, brightness, and edge variance. Truly low-quality inputs skip classification; moderate imperfections are advisory.
4. `assessment_router.py` selects only a compatible local model. User-declared anatomy is **not** automatic anatomy verification. Dermoscopy additionally needs an explicit capture attestation.
5. The adapter loads verified local weights, preprocesses the image, computes raw logits, softmax ranking and top five. It records class order, preprocessing, margin/entropy and model lineage. No unavailable calibration or OOD value is invented.
6. Independent services calculate local pixel observations, reported symptom severity, reported-concern priority, PIRS, and the assessment concern indicator. A candidate contrast region is not trained lesion segmentation.
7. `canonical_evidence.py` records each component's real status. `assessment_contract.py` builds the versioned result, including model match, alternatives, evidence strength, technical details, guidance, and explicit limits.
8. Flask returns JSON to the frontend. The frontend renders the same result contract. If signed in, MySQL stores assessment metadata and report inputs under the session's user ID. Raw uploaded pixels and overlays are not saved. PDF generation reads the saved metadata.

## Data model and endpoints

| MySQL table | Purpose |
| --- | --- |
| `users`, `auth_accounts` | Identity and salted password hash; account-linked by `user_id` |
| `medical_histories`, `consent_records`, `user_preferences` | Consented profile context, consent audit, appearance preferences |
| `assessments`, `analysis_records` | Assessment summary fields and versioned result JSON; `image_stored=FALSE` |
| `care_routines`, `progress_checkins` | User-entered routines and periodic self-reported changes |
| `reports`, `clinical_review_requests` | Report metadata and review requests |
| `schema_migrations` | Recorded additive schema changes |

Useful endpoints: `GET /api/health`, `GET /api/model-registry`, `POST /api/auth/register`, `POST /api/auth/login`, `GET /api/auth/me`, `POST /api/auth/logout`, `GET/PATCH /api/profile`, `GET/PUT /api/preferences`, `POST /api/assessments`, `POST /api/sweat-assessments`, `GET /api/analysis-history`, `GET /api/assessments/<id>`, `GET /api/reports/<id>/download`, `GET /api/history/download`, and the routine/check-in/product/knowledge routes in `app.py`.

## Viva questions and answers

### Project purpose and design

1. **What problem does the project address?** It puts a transparent, local screening-support workflow around image uploads and reported concerns, with history and next steps. It does not replace professional diagnosis.
2. **Why these four areas?** Skin, hair/scalp, and nails accept photos but need separate taxonomies and models; sweating is currently better represented by a questionnaire. One generic classifier would confuse distinct inputs.
3. **What is your technology stack?** HTML/CSS/vanilla JavaScript, Flask/Python, Gunicorn, PyMySQL/MySQL 8, Pillow, PyTorch/TorchVision, and ReportLab.
4. **Why Flask?** It provides simple HTTP routing, request parsing, sessions, JSON responses, and easy Python integration with local inference and MySQL.
5. **Why not React?** The current UI is a single-page experience and vanilla JavaScript was enough for its state transitions and rendering. This reduced build tooling for a local demo.
6. **What is the difference between frontend and backend here?** The frontend collects inputs and renders results. The backend validates input, runs local inference and assessment services, enforces account ownership, persists metadata, and generates PDFs.
7. **What does the frontend state machine do?** It tracks `IDLE`, category selection, required input, validation, preprocessing, analysis, ready result, and error; it prevents stale requests or a false progress percentage from misrepresenting work.
8. **Describe a request in one sentence.** Browser `FormData` → Flask validation/router → local model and independent evidence services → versioned JSON → result UI and optional MySQL history.
9. **Why a model registry endpoint?** `/api/model-registry` exposes actual runtime capability per area, so the UI can describe what is installed and avoid claiming every category has ML.
10. **What happens without internet?** Core assessment, local models, MySQL history, and PDF work locally after one-time checkpoint installation. Maps and shopping handoffs use external websites only when the user initiates them.

### AI and image processing

11. **Are all category models trained by you?** No. The bundled dermoscopy checkpoint and the newly integrated ordinary Skin and Nail checkpoints are external research weights run locally. The project's own SCIN and nail experiments did not meet promotion criteria. Hair has no deployable disease checkpoint.
12. **What does "local AI" mean here?** Uploaded image inference happens in the DermaMatrix Python process using local checkpoint files; no cloud vision API or API key is used during assessment.
13. **Why three different image models?** Their training domains and class labels differ: ordinary clinical skin photos, dermoscopic lesion photos, and nail close-ups are not interchangeable.
14. **What is transfer learning?** Starting from a pretrained network and adapting its final classifier to a task-specific set of labels. The imported research checkpoints use this general pattern.
15. **What are ResNet, EfficientNet and ConvNeXt?** Convolutional image-classification architectures. ResNet uses residual connections; EfficientNet balances depth, width and input resolution; ConvNeXt modernizes convolutional blocks.
16. **What does the model output first?** One logit per trained class. Softmax converts logits to a relative distribution across that model's class list; sorting yields top one and top five.
17. **Is a 70% softmax score a 70% chance the patient has the disease?** No. It is an uncalibrated ranking among that checkpoint's labels and excludes untrained conditions. We label it raw model score.
18. **What is calibration?** Checking whether predicted scores match observed frequencies on suitable independent data. The project only permits a version-matched temperature-scaling artifact; none is installed for these live research adapters.
19. **What is OOD?** Out-of-distribution means an image differs from the training domain. No fitted OOD detector is installed, so the app reports `OOD_NOT_EVALUATED` rather than claiming it verified the image is in-domain.
20. **How do you express uncertainty?** The code retains raw top-five scores, top-one/top-two margin and normalized entropy, and marks source-model limitations. These do not equal clinical uncertainty or calibration.
21. **What is Grad-CAM?** A gradient-based visualization of image regions influencing the dermoscopy network's selected class. It is not a segmentation mask or proof of a clinical feature.
22. **Does the app segment lesions?** A TorchScript segmentation provider exists but needs separately configured trained weights. Without them, segmentation is unavailable. Otsu-based contrast region extraction is clearly labeled a non-diagnostic candidate region.
23. **Why resize and normalize?** The tensor must match the checkpoint's expected input size and value distribution. The ordinary Skin transform is published; the Nail transform is an explicitly disclosed assumption because its publisher did not document one.
24. **Why handle EXIF orientation?** Smartphone files may store rotation as metadata. `ImageOps.exif_transpose` makes the pixels upright before measurement and model preprocessing.
25. **Why convert to RGB?** It gives the image models a consistent three-channel input, including when the source has alpha, palette, or another mode.
26. **How is image quality measured?** Basic size, average brightness and edge variance. A short side below 224 pixels, extreme darkness/brightness, or extreme blur blocks model inference; softer issues prompt better capture advice.
27. **Can a random non-skin photo receive a Skin label?** Yes, if it passes basic file/quality checks and the user declares Skin, because anatomy verification and OOD detection are not installed. That is a known limitation, so the output is a research ranking, not a diagnosis.
28. **Why not reject every low-confidence image?** Low confidence should affect wording and evidence, while retaining the model's actual ranking for a valid usable image. Rejection is for unusable input or incompatible scope.
29. **Why is a "Healthy Nail" top class not a healthy result?** That upstream class has not been validated as a rule-out test. The UI may show it as a model ranking but the normalized assessment stays uncertain.
30. **Can the lesion-review Skin class mean melanoma?** No. It is a broad referral/review class in the ordinary-photo model. Melanoma appears only as one research label in the separate dermoscopy taxonomy.
31. **What is the Hair model status?** The app has Hair image measurements and reported-context guidance, but no defensible disease classifier with usable weights/class mapping/evaluation. It does not make up an alopecia prediction.
32. **How strong is the Nail evidence?** The publisher reports good internal test accuracy, but transform/provenance/external validation are missing. A small local web-photo check was poor (6/17 filename-label matches), so deployment labels the result low evidence and research-only.
33. **What is the difference between internal and external validation?** Internal tests use data drawn from the development source; external validation evaluates a distinct source, acquisition setting, or patient population. Neither external clinical validation nor calibrated likelihood is established here.
34. **What is data leakage?** Train/test overlap or shared patient/source information that inflates apparent performance. Offline dataset scripts audit hashes and grouping where metadata permits; a published metric alone does not rule out leakage.
35. **What if a model file is corrupted or swapped?** The new Skin and Nail loaders compare SHA-256 before loading and load strict state dictionaries with `weights_only=True`; the API treats load failures as unavailable rather than fabricating a label.

### Scores and result logic

36. **What is PIRS?** A versioned prototype Personalized Individual Risk Score record that reuses normalized reported-concern priority, logs factors, and is explicitly not a clinically validated risk probability.
37. **Does model confidence set PIRS?** No. PIRS is based on the reported-priority score; image quality and any supplied model confidence are context, not extra risk points in `calculate_pirs`.
38. **What is reported symptom severity?** A transparent score from self-reported discomfort, recent change and selected symptoms. It is labeled mild/moderate/high and is not disease severity inferred from pixels.
39. **What is the concern indicator?** A separate versioned 0–100 heuristic in `risk_engine.py` using reported context, severity and only allowed model evidence. It is not a disease probability or clinically validated prognosis.
40. **Could model score be high while concern is low?** Yes. A classifier ranking, symptom severity, PIRS and assessment concern answer different questions and are stored separately.
41. **How is urgent input handled?** A user's prompt-care selection raises priority and urgency; it is not overridden by a low model score. The UI directs the user toward timely professional evaluation.
42. **What is the canonical evidence record?** A single versioned object of quality, validation, component statuses, classifier output, image findings and reported inputs. It preserves provenance and unavailable states.
43. **What are the main result states?** `HEALTHY`, `CONDITION`, `UNCERTAIN` as assessment states, plus terminal states such as `condition_detected`, `uncertain`, `poor_quality`, `unsupported_image` and `category_mismatch`. They describe contract flow, not a verified diagnosis.
44. **When does the app say healthy?** Only if a future compatible model supplies an explicit validated normal-appearance signal. The current research Healthy Nail label does not satisfy that rule.
45. **Why have a versioned assessment contract?** It keeps browser, saved history and PDF aligned as fields evolve, while keeping score meanings and missing evidence explicit.
46. **Does a model label choose medicines/products?** No. Research labels do not authorize prescriptions or condition-specific products. The recommendation service offers general education and directs uncertain/high-concern cases to professional review.
47. **Where does condition knowledge come from?** `condition_knowledge.py` and `recommendation_service.py` hold structured educational content and source links. The user can also browse guides independently; that does not change a photo's model output.
48. **How do you prevent fabricated visual explanations?** Pixel observations are restricted to measurements actually computed by `native_image_findings.py`; generic color/brightness statistics are not described as proven hair density, lesions or pathology.

### Frontend, API, database and security

49. **How are images sent?** The browser submits multipart `FormData` to `POST /api/assessments`; the server reads bytes for this request and returns JSON.
50. **What validation happens before inference?** Consent, supported extension and actual decoded format, nonempty bytes, size/pixel limits, successful decode, selected category/context, quality gate and dermoscopy attestation where required.
51. **What is REST in this project?** Resource-style HTTP routes use GET for reading and POST/PATCH/PUT/DELETE for appropriate changes; JSON is used for most API payloads, multipart form data for images.
52. **Why MySQL?** It provides durable, relational, account-scoped records for users, assessments, consent, routines and check-ins. InnoDB foreign keys and transactions preserve relationships.
53. **What is stored after an assessment?** For signed-in users: assessment fields and a JSON metadata summary including model ranking and provenance. Original image pixels, masks and overlays are not stored. Guests receive only an ephemeral response.
54. **How do you link tables?** `user_id` foreign keys join account-owned records. `assessment_id` associates assessment metadata, analysis records and reports. Queries filter by the user resolved from the signed session.
55. **How do you avoid SQL injection?** Values go through PyMySQL parameter placeholders such as `%s`, rather than string-concatenated SQL values. The migration code interpolates only fixed, internal column definitions.
56. **How are passwords handled?** Werkzeug creates salted password hashes and checks them at login; plaintext passwords are not saved or sent back to the browser.
57. **How is access controlled?** Flask's signed session identifies the user. The server derives account ownership from that session, not a submitted patient ID. Account-specific routes check the current user.
58. **What about guests?** They can assess without registering, but results and health history are not persisted. Registered accounts are needed for saved reports and journey records.
59. **What happens if MySQL is unavailable?** `/api/health` indicates no persistence; guest assessment can still compute and return a result. Account-dependent history, reports and saved routines need MySQL.
60. **What is a migration?** A recorded additive schema change. `schema_migrations` prevents reapplying changes, and `initialise_database` creates missing tables without discarding existing data.
61. **How are PDFs produced?** `report_service.py` uses ReportLab on stored assessment metadata for the authenticated account. PDFs intentionally omit uploaded photos because pixels were never retained.
62. **How does My Journey work?** It compares saved assessment metadata and user-entered routine/check-in records. It is input-driven tracking, not continuous monitoring or proof of improvement.
63. **Is "Find a Doctor" a booking system?** No. It opens user-initiated Maps searches and lets the person verify and contact clinics externally; DermaMatrix does not confirm appointments.
64. **Do product links affect the AI output?** No. The backend owns a general-care catalogue, and product discovery/links are separate from image classification.
65. **Why bind the server to `127.0.0.1`?** The local demo is reachable only on the same computer by default, reducing accidental network exposure.
66. **Why one Gunicorn worker by default?** Each worker could load large model checkpoints into memory. One worker is simpler and lighter for a laptop demo.
67. **Is local storage the database?** No. Browser `localStorage` holds nonclinical appearance preferences; consented account and assessment records live in MySQL.

### Testing, evaluation and challenge questions

68. **How did you test the app?** Python `unittest` and Flask test-client checks cover routing, contract states, capability claims, auth/service behavior, and model outputs. A local browser upload and HTTP smoke checks verified the live flow. MySQL integration tests are opt-in.
69. **How do you test that results are not hard-coded?** Feed distinct real images through the local checkpoints and inspect logits/top-five changes; repeat image A after other images to check deterministic inference and stale-state leakage.
70. **Why can the same image produce the same result?** Models are loaded in evaluation mode, preprocessing is deterministic, and no random augmentation is applied during inference.
71. **What is the biggest limitation?** Clinical validity: the live image models are research checkpoints with incomplete external validation, no deployed calibration/OOD detector, and no automatic anatomy verification. Hair classification is absent.
72. **Why use the Nail model if local checks were weak?** It is exposed only as a low-evidence research ranking with explicit caveats, not a diagnostic decision. Its failure modes are recorded rather than hidden.
73. **What would you improve next?** Governed, patient/source-separated data; published preprocessing for each checkpoint; representative external smartphone validation; calibration; anatomy/OOD checks; a defensible Hair checkpoint; usability testing; and clinical oversight before any real medical use.
74. **Is this a medical device or clinically deployable?** No. It is an educational prototype. It cannot diagnose, prescribe, rule out disease, or replace a qualified clinician.
75. **What is presentation-case matching?** An optional exact SHA-256 match to supplied teaching files with preauthored labels. It is not AI inference and does not recognize edited or unseen variants. Keep it off when demonstrating actual model predictions.
76. **What would you say if an examiner asks whether every uploaded photo gets a condition?** Only usable photos routed to a compatible installed local model get a research ranking. Hair, severe quality failures and unsupported contexts never receive invented condition labels.
77. **Why keep both relational columns and `result_json`?** Columns make ownership, date and common filters easy to query; the versioned JSON retains the richer assessment without forcing every nested field into a separate table. A production design may normalize more fields and add JSON indexes.
78. **Why use a transaction when saving an assessment?** The summary row and analysis record should commit together. On a database error the code rolls back, avoiding a half-saved assessment.
79. **What are primary and foreign keys here?** Primary keys uniquely identify rows. Foreign keys such as `user_id` tie account-owned records to `users` and help preserve relational integrity.
80. **What does softmax calculate?** For logit \(z_i\), softmax is \(e^{z_i}/\sum_j e^{z_j}\). It gives relative class scores summing to one; that mathematical normalization does not establish calibration.
81. **What is top-K?** The K classes with the highest scores. DermaMatrix stores the top five and normally shows the strongest alternatives in a compact UI.
82. **What is a confusion matrix?** A table of true classes versus predicted classes. It reveals which classes are confused; accuracy alone can hide those errors.
83. **Why use macro F1 or balanced accuracy?** They give more weight to performance across classes when a dataset is imbalanced. Macro F1 averages class F1 scores; balanced accuracy averages class recall.
84. **What is precision versus recall?** Precision is the fraction of predicted positives that were true positives; recall is the fraction of true positives found. Their trade-off matters especially when false reassurance or false alarms have different consequences.
85. **Why separate patients or sources across splits?** Photos from one person or acquisition source can be correlated. Separating them reduces leakage and gives a more realistic generalization estimate.
86. **Does the project encrypt the database?** The repository uses password hashes, signed sessions and local-only binding, but it does not implement encrypted MySQL backups or a production secret-management system. See `docs/security.md`.
87. **Is the local app production secure?** No. Production needs HTTPS, managed secrets, rate limiting, CSRF review, retention/deletion workflows, audit logging, monitoring, and independent security testing.
88. **What security headers exist?** The API sets no-store caching, nosniff, frame denial and restricted permissions, among others. The local HTTP demo itself does not provide HTTPS.
89. **Why not retain user photos?** Data minimization reduces stored sensitive material and keeps reports focused on metadata. The trade-off is that a historical PDF cannot reproduce or re-run an old image.
90. **What does the system do if one analysis component fails?** It records that component as failed or unavailable and preserves other completed evidence. It does not silently fill the missing field with a fabricated result.

## Demonstration and commands

Start from the project directory with `bash backend/scripts/run_app.sh`, then open `http://127.0.0.1:8000`. Before presenting, check `/api/health` and `/api/model-registry`. For a model demonstration, use an ordinary Skin photo, a genuinely dermoscopic lesion with the attestation selected, and a Nail close-up; keep presentation-case matching **off**. Show the raw-score caveat, top alternatives, separate PIRS/severity/concern, technical details, then a signed-in history/PDF if an appropriate account is ready. Do not claim a Hair disease prediction or a Sweat image model.

Run the test suite from `dermamatrix-ai/`:

```bash
PYTHONPATH=backend .venv/bin/python -m unittest discover -s backend/tests -q
node --check frontend/app.js
```

Check the authoritative files: `backend/app.py`, `backend/assessment_router.py`, `backend/model_metadata.py`, `backend/clinical_skin_classifier.py`, `backend/lesion_classifier.py`, `backend/nail_classifier.py`, `backend/canonical_evidence.py`, `backend/assessment_contract.py`, `backend/pirs_service.py`, `backend/risk_engine.py`, `backend/report_service.py`, and `frontend/app.js`.
