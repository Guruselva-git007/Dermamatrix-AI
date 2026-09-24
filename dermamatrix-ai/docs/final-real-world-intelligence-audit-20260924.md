# Real-world local inference gate — 2026-09-24

Starting point: `d0db66a`, `main`, clean worktree. This review preserves the
existing application. The detailed read-only inventory of 43 extracted
directories and four separately governed sources is stored outside Git at
`research-assets/training-runs/final-local-source-gates-20260924.json`.
Unknown counts or quality fields in that record are marked **not audited**;
a directory listing is never treated as training eligibility. The earlier
[source inventory](local-dataset-audit-20260923.md) and
[root audit](research-asset-roots-audit-20260923.md) remain the source-level
decision history.

## Targeted integrity checks

| Source | Decodable images | Exact unique | Classes/labels | Exact duplicate groups | Contradictory exact-label groups | Gate |
| --- | ---: | ---: | --- | ---: | ---: | --- |
| Facial-photo folders (`archive (9) facial skin`) | 4,233 | 4,101 | Eight appearance folders; 300–619 images each | 113 | 5 | Blocked: no provenance/licence, patient IDs, validated labels, or locked independent test; conflicting labels include the same melasma photo in different folders. |
| Bald/not-bald folders (`archive (16)`) | 1,113 | 1,103 | 553 `notbald`, 560 `bald` | 10 | 7 | Blocked: identical images have opposing labels; no provenance, case IDs, or external test. |
| Mixed Nail-related folder in `archive (11) analysis tool` | 261 | 259 | Flat filenames, no verified class manifest | 2 | Not assessable without ground-truth labels | Blocked: filenames are not clinical ground truth; no patient IDs or locked test. |

All three targeted collections decoded without a corrupt image. This does
not establish gradability or label correctness. The facial collection has
augmentation-style filenames and exact duplicates; no split from it can be
accepted before source-family grouping, provenance review, and a separate
held-out cohort. The Hair contradictions cannot be repaired by choosing a
folder label arbitrarily. Near duplicates across all 43 extracted directories
were **not** exhaustively measured, so no new training run was authorized.

## Existing model evaluation and decision

| Model | Domain / split | Held-out behavior | Decision |
| --- | --- | --- | --- |
| HAM10000 ResNet-34 research adapter | Attested single-lesion dermoscopy; existing 2,475-image local comparison | Balanced accuracy **0.560303**, macro F1 **0.506399**; melanoma recall **0.423841** (453 examples), actinic/intraepithelial class recall **0.136364** (88). No accepted calibration or OOD detector. | Retain the existing **research ranking only** route. Do not promote it to diagnosis or ordinary-photo classification. |
| SCIN ResNet-18 experiment | 212 selected clinical photos; case-grouped 148/32/32 train/validation/test | Balanced accuracy **0.414980**, macro F1 **0.405670**; eczema recall **0.368421** (19), urticaria recall **0.461538** (13). Validation temperature scaling worsened ECE. | Reject for runtime. |
| Han Figshare Nail ResNet-18 experiment | Contact-sheet-grouped internal split; locked 1,358-image external cohort | Internal balanced accuracy **0.592593**, external **0.513777**, external macro F1 **0.344603**. No normal class in the external cohort. | Retain rejection under the original predeclared promotion thresholds. |
| Local three-class ResNet-18 dermoscopy experiment | Exact-hash cleaned 932/97/363 train/validation/test | Balanced accuracy **0.722637**, macro F1 **0.728377**; melanoma recall **0.601695** (118). Out-of-domain hair image received 0.884297 raw softmax for a lesion class. | Reject: missing deployment provenance, patient grouping, near-duplicate and external controls, and a usable OOD gate. |

No checkpoint was repaired, fine-tuned, newly trained, or promoted in this
upgrade. Training again on the same blocked material would not resolve these
integrity or generalization failures. The ImageNet-initiated ResNet-18 cache
is a generic feature extractor, not an evaluated Skin/Hair/Nail classifier.

## Condition-evidence boundary

The current local photo features describe frame tone, color, contrast, and
pixel detail. They do not localize verified skin, scalp, hair, or nail anatomy.
No governed category-specific profile can defensibly turn those values into
an acne, pigmentation, alopecia, or nail-disorder compatibility score. The
canonical record therefore explicitly reports **insufficient measured
evidence** with no Possible Concerns or invented score. This is a Level 3
image-findings assessment for ordinary photos, including unseen photos.

The ordinary-photo category is user-declared; it is not automatically
anatomy-verified. A reliable unrelated-object/OOD rejection gate is still
unavailable. The app does not claim one. A low-quality image can produce
limited frame measurements and a retake recommendation without a disease
label. A normal-looking photo also remains findings-only because no validated
normal-appearance signal exists.

## Capability matrix

| Category | Input domain | Local model | Supported output | Confidence | Condition evidence | Fallback |
| --- | --- | --- | --- | --- | --- | --- |
| Skin | Attested dermoscopy | HAM10000 ResNet-34 research adapter | Uncalibrated research ranking, if image passes quality | No medical likelihood | No scored profiles | Image findings |
| Skin | Ordinary photo/selfie | None eligible | Image-specific frame measurements and reported-context guidance | None | Insufficient | Image findings |
| Hair | Ordinary hair/scalp photo | None eligible | Image-specific frame measurements and reported-context guidance | None | Insufficient | Image findings |
| Nails | Ordinary nail photo | Rejected ResNet-18 remains offline | Image-specific frame measurements and reported-context guidance | None | Insufficient | Image findings |

This is the strongest currently justified local runtime capability. It is
**not** a condition-level intelligence upgrade. A future promotion requires
source rights, verified semantic labels, patient/group-safe splits, a locked
external evaluation with acceptable per-class behavior, calibration and
abstention, OOD handling, real upload tests, and independent review.

## Final local verification

The application was restarted from `backend/scripts/run_app.sh` on a separate
local port after the final inference changes. The test suite ran 100 tests:
99 passed and one was skipped. Six injected component failures plus an
image-processing failure preserved the remaining canonical findings without
inventing the failed output.

Real uploads through the running application passed Skin, Hair, and Nail
**A→B→A**: the decoded image dimensions and abbreviated SHA-256 fingerprints
were recorded privately; each B image changed measured values, and each
repeated A reproduced its measurements. The three categories were also
uploaded through the browser interface, where each showed actual frame
findings. An attested dermoscopy upload invoked the retained local research
model and produced three rankings, while calibrated condition confidence
remained unavailable. A live Sweat questionnaire completed separately.

Additional running-app checks covered a close-up skin image, a folder-labelled
normal-looking image, a hairline image, existing blurred, underexposed, and
overexposed relevant images, and unrelated screenshots/documents. No ordinary
upload received a condition label or fabricated affected-area measurement.
The clear unrelated document still passed the pixel-quality check because
anatomical/OOD rejection is not available; its result was explicitly scoped
to user-declared frame findings and reported context. This remains a release
limitation for clinical use, not a passed OOD detector test. The folder-labelled
normal image was too small for a strong normal-appearance conclusion.

An authenticated local run saved two real Skin assessments. Each saved History
record and assessment detail matched the original canonical evidence; the
Journey evidence snapshot matched visible findings, PIRS, and severity. Both
assessment and history PDFs generated from the saved metadata and were
rendered for visual inspection. Contrast-selected frame regions no longer
contribute to the medical-looking concern indicator or appear as measured
affected anatomy; only validated segmented extent could do so. The concern
methodology was versioned to `dermamatrix-assessment-risk-v1.3`. The synthetic
verification account and its records were removed after the check.
