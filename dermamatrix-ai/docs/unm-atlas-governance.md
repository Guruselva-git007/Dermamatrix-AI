# UNM Inclusive Dermatology Atlas — governance audit

**Audit date:** 2026-09-07

**Repository decision:** `BLOCKED_AWAITING_WRITTEN_ML_AUTHORIZATION`

**Images ingested:** 0
**Models trained or connected:** 0

## What was verified

The [University of New Mexico (UNM) Inclusive Dermatology Atlas](https://hsc.unm.edu/medicine/departments/dermatology/inclusive-dermatology/) is a public educational resource with an important stated aim: improving representation of dermatologic conditions across skin types. UNM describes the atlas as organised by team-estimated Fitzpatrick skin type and explicitly notes the scale's subjectivity and limitations. Its [gallery](https://hsc.unm.edu/medicine/departments/dermatology/inclusive-dermatology/gallery.html) is a condition browser, not a documented downloadable ML dataset.

The source publication is Midani L, Ridgeway G, Phillips CM, Smidt AC, *Inclusive Dermatology — Creating a Diverse Visual Atlas of Skin Conditions*, **New England Journal of Medicine** 2024;390:2037–2038. DOI: [10.1056/NEJMp2313807](https://www.nejm.org/doi/full/10.1056/NEJMp2313807).

## Permission decision

UNM's [legal notice](https://www.unm.edu/legal.html) allows reproduction of its web information, publications and images for non-commercial, personal or educational purposes under stated conditions, including no modification and preservation of copyright notices. It does **not** publish a grant for:

- automated collection or crawling of atlas images;
- ML training/evaluation or derived model weights;
- redistribution of a dataset or image manifest;
- patient-level metadata, image-level licences, or a ground-truth protocol; or
- the commerce-compatible use required by an application that offers optional product handoffs.

Public availability is not a training-data licence. Training would create derivatives and require permissions beyond the public webpage terms. The repository therefore does not fetch the gallery, enumerate image URLs, retain source metadata, create `unm_manifest.csv`, or claim any UNM image/class/skin-type count.

## Enforced repository control

`backend/dataset_registry.py` stores the source record and exposes
`training_eligibility("unm_inclusive_dermatology_atlas")`. It returns a blocked
status. `backend/scripts/prepare_dataset_manifest.py --dataset-key
unm_inclusive_dermatology_atlas ...` exits before reading or transforming a
manifest. This is a governance guard, not a licence validator.

## Conditions required to reopen the decision

1. Written permission from the rightsholder that expressly covers automated access (if needed), ML training, evaluation, derived weights, and the intended application use.
2. A documented versioned release with image-level provenance, licence/consent, condition labels, ground-truth method, and attribution requirements.
3. A clinician-led protocol with patient-level train/validation/test separation, exact/near-duplicate controls, normal/unknown policy, and external validation.
4. Adequate, measured subgroup evaluation with appropriately qualified interpretation of skin-tone fields.
5. A separate deployment decision after recorded performance, calibration, error analysis and legal review—particularly before any result could influence product discovery or care guidance.

Until all five conditions are met, this source remains educational reference material only.
