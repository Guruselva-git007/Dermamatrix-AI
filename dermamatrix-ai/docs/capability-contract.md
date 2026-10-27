# Capability and assessment-status contract

`GET /api/model-registry` is the application’s single public capability source.
The client reads its `capabilities` array for each health area’s input mode,
runtime readiness, processing copy, and limitations. Legacy `modalities` and
the condition-knowledge matrix are derived from that same source; they are not
separately maintained declarations of model availability.

## Capability statuses

| Status | Meaning in this deployment |
| --- | --- |
| `RESEARCH_ONLY` | A component may run only inside its documented research route. It is not clinically validated or diagnostic. |
| `NOT_AVAILABLE` | No governed, deployable condition model is configured. |
| `QUESTIONNAIRE_ASSESSMENT` | A bounded questionnaire pathway is available; it is not an image or validated supervised condition model. |
| `REJECTED` | An experiment was evaluated and deliberately withheld from runtime use. |

`runtime_inference_available` is a lightweight local-weight-presence hint from
`backend/model_metadata.py`, not a successful model-load or inference test and
not a clinical-deployment claim. Skin reports this hint when either its
ordinary-photo or dermatoscopy checkpoint exists; the aggregate Skin record
retains the dermatoscopy model ID for compatibility. Per-model entries identify
the two adapters separately. Request-specific route, consent, quality and
capture checks still apply, and actual inference may fail independently.

| Path | Configured support | Local artifact checked on 22 October 2026 | Runtime boundary |
| --- | --- | --- | --- |
| Declared ordinary Skin photo | Five-class EfficientNet-B0 research adapter | `backend/models/clinical_skin_best_model.pth` present | Separate clinical-photo route; raw rankings, no calibrated disease probability or anatomy verification. |
| Attested single-lesion dermoscopy | Seven-class HAM10000 ResNet-34 research adapter | `backend/models/ham10000_resnet34_research.ptw` present | Dermatoscopic capture attestation and image gate required; Grad-CAM is attention, not segmentation or a diagnosis. |
| Declared Nail close-up | Ten-class ConvNeXt Tiny research adapter | `backend/models/nail_convnexttiny_research.pth` present | Raw rankings; upstream training transform is unpublished, so the adapter discloses its assumed ImageNet transform. “Healthy Nail” cannot rule out disease. |
| Hair/scalp photo | Quality, local image measurements and reported-context guidance | No compatible condition checkpoint configured | Hair condition classification remains unavailable. |
| Sweat | Bounded questionnaire rules | No image checkpoint required | No Sweat image classifier or clinically validated tabular classifier. |

This artifact check did not load or replace weights, retrain a model, or
establish diagnostic performance. Available dependencies, checksum checks,
request-specific inputs and successful loading must be verified separately.
Published upstream metrics and dated local pipeline checks in
[model sourcing](local-model-source-and-validation-20260925.md) are not
independent clinical validation. No configured adapter has established
clinical readiness, generalization, calibrated likelihood or OOD detection
merely because its file exists. A version-matched independent-validation
calibration artifact is required before the dermoscopy adapter can expose a
calibrated likelihood; ordinary Skin and Nail adapters currently expose none.

The rejected SCIN experiment and the separate rejected three-class nail
experiment remain excluded from runtime. They must not be confused with the
installed five-class ordinary-Skin or ten-class Nail adapters.

## Normalized assessment status

Every persisted `assessment_result` now has a `status` object, independent of
condition likelihood, reported symptom severity, assessment concern indicator,
and disease risk:

| Code | Meaning |
| --- | --- |
| `QUESTIONNAIRE_ASSESSMENT` | Sweat questionnaire completed; no image inference ran. |
| `INPUT_UNSUITABLE` | The image did not pass the quality or input gate. |
| `CATEGORY_MISMATCH` | An actual configured route/validation check reported a category mismatch; it is not automatic visual anatomy verification. |
| `UNCERTAIN` | The bounded evidence/validation path explicitly resolves to an uncertain outcome. |
| `RESEARCH_ONLY` | The scoped research image model ran. This is not a diagnosis. |
| `MODEL_UNAVAILABLE` | A valid route completed without a compatible condition model. |
| `NORMAL_APPEARANCE` | Guarded future-compatible branch requiring an explicit independently validated normal-appearance model signal; the current research adapters do not provide one. |

The contract also keeps `assessment_state` (`CONDITION`, `HEALTHY`, `UNCERTAIN`)
and `result_state` (`condition_detected`, `healthy`, `uncertain`,
`category_mismatch`, `unsupported_image`, `poor_quality`) separate from the
status code. These names describe actual pipeline evidence, not a confirmed
clinical conclusion. Neither a missing model nor a usable photo establishes
healthy appearance. Low raw model confidence remains explicit in uncertainty
fields even when a scoped research ranking is retained. No current fitted OOD
detector establishes `OUT_OF_DISTRIBUTION`, and `SUPPORTED_RESULT` is not an
emitted status. Clients should use supplied labels/notices and evidence, not
infer diagnosis or approval from an enum name.

## Compatibility notes

The current source declares `assessment-result-v1.7`; older persisted records
retain their original contract and lineage. The client adapts legacy records
at read time rather than rewriting historical evidence. Model, dataset,
pipeline and calibration versions remain distinct so longitudinal views never
treat a version change alone as a biological change. The rich consumer result,
canonical evidence, metrics, uncertainty and technical details remain part of
the assessment experience.

The checked-in Dockerfile installs only the dermatoscopy checkpoint during
build. Local presence of ordinary-Skin and Nail files does not put them in a
fresh Docker image or prove their availability on a host. See
[deployment notes](railway-deployment.md) and the
[upgrade decisions and permission register](audit-upgrade-decisions.md).
