# Local skin, hair, and nail modality readiness — 2026-09-23

> Historical snapshot. See [local model sourcing and verification](local-model-source-and-validation-20260925.md) for the later ordinary Skin and Nail research adapters and their evidence limits.

## Decision

The application continues to accept image uploads for Skin, Hair & scalp, and
Nail health. A result must describe only what the available evidence supports:
image quality, declared-image context, reported concern, urgency guidance, and
the one compatible research classifier where it genuinely ran. A usable image
is not silently converted into a disease label.

The supplied data have been used where the task, labels, and evaluation support
offline research. They are not pooled across body areas: dermoscopy, clinical
skin, scalp/hair, nails, segmentation masks, and tabular rows describe
different inputs and targets.

| Area | Source decision | Current upload result |
| --- | --- | --- |
| Skin | The retained HAM10000 dermoscopy route and two local dermoscopy research experiments were trained and tested separately. The local three-class candidate achieved 0.728377 macro F1 on its locked test but was rejected for app inference because provenance/licensing, patient/case grouping, near-duplicate control, external validation, and runtime compatibility are missing. | An attested dermatoscopic single-lesion upload may run the existing research-only seven-class adapter. Other skin images receive quality/context and reported-concern results only. |
| Hair & scalp | `archive (16)/data0330` has 560 `bald` and 554 `notbald` files but seven exact image hashes occur under both labels; filenames and missing source material also establish no usable provenance. `archive (6)` has only one broad hair-disease label (239 train / 60 test, with eight duplicate groups); the 2,000-row CSV has no images; the mask sample has five subjects. | Quality, image-context, reported-concern, and next-step results work. No hair-condition label, normal-appearance claim, or likelihood is emitted. |
| Nail health | The governed Figshare three-class feasibility run used a locked 1,358-image external cohort and failed its predefined promotion thresholds (0.592593 internal and 0.513777 external balanced accuracy). Other local nail folders use broad/duplicated labels without governed provenance or an independent evaluation split. | Quality, image-context, reported-concern, and next-step results work. No nail-condition label, normal-appearance claim, or likelihood is emitted. |

## Enforced data intake

`backend/dataset_registry.py` now gives precise hard-block reasons for the
known local hair/nail candidates. A future manifest tool can therefore refuse
them before training rather than wasting compute or generating a misleading
model artifact. This does not remove or alter any supplied source files.

The existing Figshare nail source remains a valid **offline research** record,
but its measured failure prevents inference promotion. The local sources above
need a documented source licence/provenance, image-level condition labels,
patient or case grouping, duplicate/near-duplicate controls, independent
validation and test cohorts, and clinical review before a new image classifier
can be trained and considered for the app.
