# Dataset registry and task mapping

Raw medical data is never committed to this repository. The registry records
what was considered, selected, or excluded so a research experiment cannot be
mistaken for an application model.

| Dataset / instrument | Status in this repository | Supported task / modality | Labels / ground truth | Licence and governance | Limitations |
| --- | --- | --- | --- | --- | --- |
| HAM10000 (Tschandl, Rosendahl, Kittler, *Scientific Data*, 2018, DOI [10.1038/sdata.2018.161](https://doi.org/10.1038/sdata.2018.161)) | Optional upstream research-weight lineage only; raw data and weights are not in Git | Dermoscopic pigmented-lesion multiclass research | Seven lesion categories; source metadata must be reviewed for each study run | Obtain from the [Harvard Dataverse record](https://doi.org/10.7910/DVN/DBW86T), record version/checksum/licence before use | Dermoscopic lesions only; not face/selfie, general clinical photos, hair, nail, sweat, or a normal-image class |
| ISIC Archive | Candidate external dermoscopic validation source; not used | Collection-specific dermoscopic/clinical tasks | Collection-specific labels/ground truth | [Image licences are per image](https://www.isic-archive.com/blank-1); permission and attribution must be checked before every use | A collection can mix licences and distributions; no external evaluation is claimed |
| SCIN (Skin Condition Image Network) | Selected for one **external, rejected** offline experiment; no raw data, checkpoint, or calibration artifact is in Git or the app | Clinical-photo dermatology research, not dermoscopy transfer claims | Dermatologist weighted condition labels and available tone/demographic metadata; see the [official dataset documentation](https://github.com/google-research-datasets/scin) | SCIN Data Use License; reviewed before manifest-bound acquisition; retain attribution and never re-identify/re-link | Volunteer/self-submitted images, self-reported data, multi-condition/gradable limitations; no direct equivalence to Indian clinical population |
| UNM Inclusive Dermatology Atlas | **Blocked from ingestion and training**; source-governance record only | Educational clinical dermatology photographs arranged by team-estimated Fitzpatrick type | Public condition-gallery labels; no downloadable versioned ML label/ground-truth release identified | The public [UNM legal notice](https://www.unm.edu/legal.html) permits non-commercial personal/educational reproduction subject to conditions, but does not grant ML training, derivative-model, automated collection, or commerce-compatible permission. Written ML authorization is required. | Public accessibility is not a data licence. Image count, patient IDs, image-level consent/licence, split metadata and ground-truth protocol are not published as a usable ML dataset. |
| Hair/scalp datasets | No dataset selected | Potential scalp/hair image tasks | None selected | Provenance, patient split, label/ground-truth, access, and licence not yet established | No hair model can be trained or exposed from this repository |
| Nail-disorder datasets | No dataset selected | Potential nail image tasks | None selected | Provenance, patient split, label/ground-truth, access, and licence not yet established | No nail model can be trained or exposed from this repository |
| Hyperhidrosis Disease Severity Scale (HDSS), Kowalski et al., *JAAD* 2004, DOI [10.1016/j.jaad.2003.10.202](https://doi.org/10.1016/j.jaad.2003.10.202) | Candidate questionnaire instrument, not a training dataset | Patient-reported sweating severity | Four response categories concerning interference with daily activities | Verify instrument wording/use permissions with the rights holder before product use | Measures reported severity; it is not image data and does not supply an XGBoost-ready diagnosis dataset |
| HDSM-Ax (Kirsch et al., *J Drugs Dermatol.* 2018, PMID [30005091](https://pubmed.ncbi.nlm.nih.gov/30005091/)) | Candidate axillary-hyperhidrosis outcome instrument, not a training dataset | Patient-reported axillary sweating severity | 11-item, 0–44 patient-reported measure in its validation study | Publication/instrument terms must be reviewed before use | Axillary-focused; no public training cohort is bundled |

## Dataset-to-task decision

`DERMOSCOPIC` lesion research is the only supported optional model pathway, and only if the existing upstream HAM10000 weight is installed. It does not validate the clinical-photo pipeline.

`CLINICAL_PHOTO` skin, hair/scalp, and nail tasks remain `MODEL_NOT_CONFIGURED` in the application. `SWEAT` remains a questionnaire-only module. No dataset supports a general “normal skin” claim in the current runtime; that state is consequently not inferred.

Any future experiment must retain patient IDs only inside a governed local experiment environment, split by patient before augmentation, record duplicate/near-duplicate policy, and report `EXTERNAL_VALIDATION_NOT_AVAILABLE` until a locked external dataset is actually evaluated.

## UNM Inclusive Dermatology Atlas decision — 2026-09-07

The project investigated UNM's [Inclusive Dermatology Atlas](https://hsc.unm.edu/medicine/departments/dermatology/inclusive-dermatology/) because its educational mission includes broader skin-type representation. The site describes a gallery organised by team-estimated Fitzpatrick type and acknowledges the scale's limitations. Its public pages do not publish a dataset licence, downloadable release, image-level training consent, patient-level identifiers, or a model-training access method.

The relevant [UNM legal notice](https://www.unm.edu/legal.html) limits reproduction of site information and images to non-commercial, personal, or educational uses with conditions including no modification and preservation of copyright notice. This app's optional commerce handoffs and a trained model's derived weights create a use that is not safely covered by that webpage notice. Therefore `backend/dataset_registry.py` marks the source `BLOCKED_AWAITING_WRITTEN_ML_AUTHORIZATION`; no images or page metadata were harvested, no UNM manifest was generated, and no UNM-trained model is claimed.

## SCIN experiment 2026-09-06

The official SCIN metadata was acquired outside Git and hashed in the private
research directory. A manifest selected 212 contributions with one first image
per SCIN case, one weighted dermatologist label at least 0.7, and exactly two
labels: Eczema (127) and Urticaria (85). It was split deterministically into
148 train, 32 validation, and 32 held-out test cases. SCIN case IDs are not
verified patient identifiers, so this is **case-grouped**, not a patient-level
split claim.

The frozen-backbone ResNet-18 run is documented in
[the experiment record](scin-experiment-20260906.md). Its held-out balanced
accuracy was 0.520243 with a 32-image test set. It is therefore
`REJECTED_FOR_APPLICATION_INFERENCE`; it is neither a runtime asset nor a
clinical model. The experiment establishes the offline pipeline and a negative
baseline, not a supported Eczema/Urticaria feature.
