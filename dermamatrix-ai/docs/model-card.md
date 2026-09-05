# DermaMatrix model card

## Current runnable components

| Component | Intended input | Output | Clinical status |
| --- | --- | --- | --- |
| Reported-concern prioritisation | User-selected duration, discomfort, recent change, and image usability | A discussion-priority label | Demonstration logic; not trained, not a diagnosis or risk prediction model |
| HAM10000 ResNet-34 | One in-focus **dermatoscopic** image of one skin lesion | Research label ranking, Grad-CAM attention, and a calibrated likelihood only when an independent-validation artifact is configured | Research-only; not validated or deployed as a medical device |

The HAM10000 component does **not** run on a face/selfie, hair/scalp image, nail image, sweat-gland concern, or a normal camera image. The user must choose dermatoscopic lesion mode, confirm the capture method, and pass the usability gate before it is called. Grad-CAM is an attention visualisation, not lesion segmentation and not a medical finding.

## Known limitations

- HAM10000 represents dermatoscopic pigmented-lesion images; it is not a representative clinical population or a general dermatology, hair, nail, or deficiency dataset.
- The app has no prospective clinical validation, subgroup performance study, calibration study, clinician review workflow, or regulatory clearance.
- Raw softmax scores are relative model rankings and are never shown as calibrated medical probabilities. The runtime only exposes an estimated likelihood when a version-matched temperature-scaling artifact with independent validation provenance is present.
- The app has no fitted out-of-distribution detector. It reports `OOD_NOT_EVALUATED` instead of calling an image known, normal, or out-of-distribution.
- A user-selected prompt-care concern is escalated without being overridden by the model.

## Required work before clinical deployment

1. Clinician-led intended-use specification and RMP governance.
2. Ethics approval, informed consent, de-identification, and data-governance review for any new patient data.
3. Dataset licence review, patient-level train/validation/test separation, external validation, calibration, and subgroup/fairness evaluation.
4. Independent clinical validation, human-factors testing, cybersecurity/privacy controls, audit logging, incident monitoring, and applicable regulatory review.
5. An RMP workflow that independently reviews every case before diagnosis, counselling, prescription, or product recommendation.

## References

- Tschandl P, Rosendahl C, Kittler H. *The HAM10000 dataset*. Scientific Data 5, 180161 (2018). DOI: 10.1038/sdata.2018.161.
- Tschandl P et al. *Human–computer collaboration for skin cancer recognition*. Nature Medicine 26, 1229–1234 (2020). DOI: 10.1038/s41591-020-0942-0.
