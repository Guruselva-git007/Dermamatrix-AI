# Assessment concern indicator

`backend/risk_engine.py` provides the single, versioned assessment-risk
boundary used by the assessment API, result contract, saved summaries, PDF
reports, and compatible progress comparisons.

## What it is

The engine is a deterministic 0–100 **assessment concern indicator**. It is a
transparent prototype method, not a diagnosis, disease probability,
prognosis, treatment recommendation, or clinically validated medical-risk
score. Its version is stored with every new saved assessment so later
comparisons can refuse incompatible methods.

It uses only evidence available for the current assessment:

- selected area and a default area profile;
- self-reported symptom severity, duration, change, discomfort, and relevant
  symptoms;
- the optional prompt-care selection;
- a compatible scoped-model label and visual extent only if that model really
  ran;
- sweat questionnaire responses for the questionnaire-only pathway.

Image quality, missing calibration, and uncertainty are recorded as
reliability context. They do not silently increase the score or get presented
as medical evidence. Educational condition guides and presentation teaching
labels are never passed into the engine. Exact-file teaching cases return no
patient-specific indicator.

## Output

The normalized result exposes distinct fields:

- `condition.estimated_likelihood` — only from a calibrated compatible
  research model;
- `severity` — self-reported symptom severity;
- `assessment_risk` — this transparent concern indicator;
- `care_priority` — the older reported-concern compatibility field;
- `urgency` — routing guidance, separate from all scores.

Each assessment indicator contains a score, band, urgency, contributing
factors, explanation, calculation inputs/missing optional evidence, method,
methodology version, timestamp, and `not_clinically_validated` status.

## Persistence and comparison

New values are stored both in `analysis_records.result_json` and additive
columns on `assessments`. Existing records remain untouched. My Journey
compares scores only if methodology versions match, and labels any numerical
change as a measurement change—not healing, cure, or disease progression.

## Boundaries

The model is deliberately not calibrated against patient outcomes. It must
not be described as clinically validated or used to prescribe medication.
Clinical validation would require an approved protocol, representative
ground-truth data, locked method, and external evaluation.
