# Stabilize Dermamatrix AI

- Legacy task ID: `01a0c950-5171-7aa2-bf17-3bcba5bc2c0d`
- Legacy workspace recorded by Codex: `/Users/gs/Documents/ChatGPT/Dermamatrix AI Powered Integumentary System`
- Archive status: PARTIALLY ACCESSIBLE / PARTIALLY ARCHIVED

## Preserved request

The attached production/stability brief required a real, evidence-based presentation flow while preserving the existing architecture. It required audit before change, real supported inference rather than a dummy result, no unsafe model replacement, no fabricated classification/confidence/segmentation, and end-to-end verification of login, input, result, report, and journey.

## Recovered outcomes

- The task verified an attested dermatoscopic path with the existing ResNet-34 research model and Grad-CAM, rather than promoting a new candidate without evidence.
- A local seven-class archive comparison was documented and committed as `d49c727`. The active ResNet-34 was retained; the ResNet-18 candidate was not promoted after lower recorded metrics.
- The chat records scoped MySQL persistence, report PDF, routine, and check-in checks using disposable test data followed by cleanup.
- It records 77 historical tests passing at that point, plus selected browser and API checks. These are historical evidence, not a substitute for this migration's current 86-test verification.
- It explicitly retained the boundary that a candidate visual region/Grad-CAM is not lesion segmentation and that research inference is non-diagnostic.

## Current reconciliation

`d49c727` and the tracked `results/skin-lesion-zip-v1/` experiment record are present in canonical Git history. The live registry still reports the HAM10000 ResNet-34 route as `RESEARCH_ONLY`; rejected SCIN, nail, and local ResNet-18 artifacts are not runtime models. The current migration did not resubmit a research image, so it verifies model availability/configuration but does not restate an end-to-end inference claim from historical chat alone.

The task-reader response containing the long conversation was transport-truncated. A full raw export remains a manual migration action.
