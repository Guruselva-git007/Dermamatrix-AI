# Condition intelligence boundary

Version: `dermamatrix-condition-knowledge-v1`  
Last reviewed: 2026-09-06

This is a compact, source-controlled knowledge layer for the existing
DermaMatrix assessment flow. It is separate from the image model, the
reported-concern priority engine, and commerce. It does not provide a medical
diagnosis, prescription, recovery estimate, or product selection based on a
disease label.

## Current capability matrix

| Health area | Inputs | Model-supported findings | Likelihood | Explanation | Status |
| --- | --- | --- | --- | --- | --- |
| Skin | Attested dermatoscopic single-lesion image | HAM10000 research labels only: AKIEC, BCC, BKL, DF, MEL, NV, VASC | Only if a version-matched independent-validation calibration artifact is installed | Grad-CAM only when the research model runs | Research-only |
| Hair | Declared scalp/hair image | None | Not available | Not available | No validated classifier configured |
| Nails | Declared nail image | None | Not available | Not available | No validated classifier configured |
| Sweat | Questionnaire only | None | Not available | Transparent questionnaire contribution summary, not SHAP | Rule-based prototype |

An ordinary face/body photo, a hair image, a nail image, or a sweat response
never becomes a condition label because the current application has no
compatible validated model for that task. A model-ranking score is never shown
as a real-world likelihood unless the calibration gate passes.

## Ontology contents

`backend/condition_knowledge.py` contains structured entries only for the
seven exact HAM10000 model classes. Every entry has an identifier, aliases,
health area, model status, doctor specialty, care/treatment boundary,
follow-up limitation, product boundary, monitoring note, sources, version,
and review date. The entries intentionally do not add causes, disease severity,
treatment, prognosis, or product recommendations from a research ranking.

For every assessment, the service produces a persisted `condition_intelligence`
object that distinguishes:

- model-supported calibrated research likelihood, when one is truly available;
- model-supported ranking only, when calibration is unavailable;
- no model-supported finding, for unconfigured or unsuitable pathways;
- self-reported symptoms, prior care, history availability, and saved-record
  availability as context—not diagnostic facts or CNN inputs;
- reported symptom severity and reported-concern priority as separate,
  non-clinically-validated quantities;
- care pathway, follow-up, doctor-handoff, commerce, and monitoring boundaries.

## Evidence sources

The ontology uses source links for provenance and patient-education context;
the app does not claim that these sources validate the model.

- Tschandl P, Rosendahl C, Kittler H. *The HAM10000 dataset*. Scientific
  Data (2018). [DOI](https://doi.org/10.1038/sdata.2018.161) — exact research
  label taxonomy.
- [MedlinePlus: Actinic keratosis](https://www.medlineplus.gov/ency/article/000827.htm)
  — NIH patient education used only as a linked reference for the AKIEC entry.
- [NCI: Skin cancer treatment (PDQ®)](https://www.cancer.gov/types/skin/patient/skin-treatment-pdq)
  — patient information linked for the BCC entry.
- [NCI: Melanoma treatment (PDQ®)](https://www.cancer.gov/types/skin/patient/melanoma-treatment-pdq)
  — patient information linked for the MEL entry.
- [MedlinePlus: Moles (nevus)](https://medlineplus.gov/moles.html) — NIH
  patient education linked for the NV entry.

## Boundaries retained by design

- The condition ontology is not a source of new image-model classes.
- No normal-image claim is generated without a supported normal class.
- No image is used for uncontrolled online learning or stored with a report.
- No medication, dosage, cure, prognosis percentage, or condition-specific
  affiliate recommendation is generated.
- Doctor search and appointment actions remain external Maps/clinic handoffs;
  the assessment does not create or confirm an appointment.
