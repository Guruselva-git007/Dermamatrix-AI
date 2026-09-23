# Production input and result contract — 2026-09-23

## Purpose

This release makes every completed Skin, Hair/scalp, and Nail image attempt
end in one explicit, non-diagnostic semantic result state.  It does not turn
an image-quality check, a user-selected context, or a broad dataset label
into a condition prediction.

The public normalized contract is now `assessment-result-v1.5`.  Its
`result_state` is exactly one of:

| Result state | Evidence required | Current use |
| --- | --- | --- |
| `condition_detected` | A compatible scoped classifier actually emitted a condition signal | Reserved for the attested dermatoscopic research route only |
| `healthy` | A compatible model emitted an explicit independently validated normal-appearance signal | No current image route emits this without that evidence |
| `uncertain` | A usable image lacks a supported confident condition/normal signal | General Skin, Hair/scalp, and Nail routes with no approved modality classifier |
| `category_mismatch` | A configured validator found a mismatch, or the submitted declared context is invalid for the selected area | Invalid declared route; never inferred from a user selection alone |
| `unsupported_image` | File validation fails or an actual model-scope/OOD check rejects the input | Unsupported, empty, corrupt/mislabelled, over-limit, or out-of-scope input |
| `poor_quality` | The image-quality gate fails | Retake flow; no classifier runs |

The detailed `status`, input-validation evidence, model lineage, and notices
remain alongside `result_state`; the semantic state is not a diagnosis.
Rejected upload responses include the same normalized contract, so a client
can complete an invalid-image attempt rather than treating an HTTP error as a
model result.  The browser maps these states to an explicit final UI state;
it does not leave the assessment in a spinner.

## Client photo coach

The upload workflow gives area-specific capture tips for Skin, Hair/scalp,
Nails, and the dermatoscopic route.  Once a person selects a file, a bounded
160-pixel on-device preview estimates only dimensions, brightness, and visible
detail.  It can suggest a retake before the upload, reducing avoidable server
requests, but it does not block submission, classify anatomy, infer health, or
replace the server's format and quality gates.  A result that is uncertain
offers a clean reassessment action that removes the previous local preview
before accepting another image.

## Current modality behavior

| Area | Accepted upload behavior | Classifier behavior | Honest terminal behavior today |
| --- | --- | --- | --- |
| Skin | Quality/context support; only an attested dermatoscopic single-lesion image enters the bundled research adapter | Existing HAM10000 research adapter is never used for general phone photos | `uncertain` unless the scoped adapter produces evidence; low-quality/unsupported paths are explicit |
| Hair/scalp | Quality and reported-context support | No approved hair/scalp disorder classifier is configured | `uncertain`, not a simulated hair-loss label |
| Nails | Quality and reported-context support | No approved nail-disorder classifier is configured | `uncertain`, not a simulated fungus/normal label |

`USER_DECLARED_CONTEXT_NOT_AUTOMATICALLY_VERIFIED` remains explicit in the
API.  It is intentionally **not** converted into `category_mismatch`: no
validated anatomical relevance model is installed, so the app cannot honestly
claim that it recognised a hand, a scalp, or an unrelated object.  Adding an
automatic wrong-body-part/object rejection requires a separately governed,
held-out evaluated category/relevance dataset and model.

## Dataset decision record

The source files remain immutable under the four registered research asset
roots.  The audit and experiment records are:

- `docs/research-asset-roots-audit-20260923.md`
- `docs/local-dataset-audit-20260923.md`
- `docs/local-modality-readiness-20260923.md`
- `docs/three-class-dermoscopy-experiment-20260923.md`
- `docs/skin-lesion-zip-experiment-20260922.md`
- `docs/nail-research-experiment-20260907.md`

They establish that the local broad Skin, Hair, and Nail folders do not supply
a deployable general-image model: known exact cross-label hair duplicates,
broad/heterogeneous labels, missing source/license/provenance information,
and absent independent patient/case-level evaluation block them.  The Hair
CSV is tabular rather than image data; the five-subject mask set is
insufficient; the balanced Hair/Nail folders contain only broad labels.  The
independent nail feasibility experiment was also rejected after weak locked
external performance.  These assets are kept for traceability and remain
blocked in `backend/dataset_registry.py`; they are not wasted by silently
training an unsafe model.

## Verification

Regression coverage verifies all six semantic states, rejected file uploads,
wrong declared context, Hair/Nail accepted-photo fallback, and no fabricated
condition likelihood.  The full backend suite and JavaScript syntax check are
the release gate for this change.
