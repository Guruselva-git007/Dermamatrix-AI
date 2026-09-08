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

`runtime_inference_available` is intentionally narrower than a capability
status. It can be true only when the dermatoscopic Skin research adapter has
its local weights and the request later passes the capture-attestation route.
It does not claim clinical deployment. Hair and Nail model adapters remain
unavailable; Sweat remains questionnaire-only. Rejected SCIN and nail
experiments remain excluded from this field.

## Normalized assessment status

Every persisted `assessment_result` now has a `status` object, independent of
condition likelihood, reported symptom severity, assessment concern indicator,
and disease risk:

| Code | Meaning |
| --- | --- |
| `QUESTIONNAIRE_ASSESSMENT` | Sweat questionnaire completed; no image inference ran. |
| `INPUT_UNSUITABLE` | The image did not pass the quality or input gate. |
| `OUT_OF_DISTRIBUTION` | A future configured detector explicitly rejected the image. No current model fabricates this state. |
| `UNCERTAIN` | A compatible research output did not meet its certainty threshold. |
| `RESEARCH_ONLY` | The scoped research image model ran. This is not a diagnosis. |
| `MODEL_UNAVAILABLE` | A valid route completed without a compatible condition model. |

`SUPPORTED_RESULT` is reserved for a future model with documented deployment
approval and evaluation; this repository does not emit it. The client should
show the supplied label and notice, not infer a medical conclusion from the
code.

## Compatibility notes

The additive status object advances the result schema to
`assessment-result-v1.3`. Existing result fields are unchanged. History and
PDF records retain their own model, dataset, pipeline, and calibration lineage
so longitudinal views never treat different model versions as a biological
change.
