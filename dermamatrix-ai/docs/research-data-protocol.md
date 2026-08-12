# Research-data protocol

This project does not require a raw image dataset to run the included pretrained research model. Downloading a large public image set cannot make it valid for face, hair, nail, sweat-gland, or deficiency diagnosis; it would require a separate clinician-led research and validation programme.

## Approved research source for the existing lesion component

Use HAM10000 / ISIC 2018 dermatoscopic lesion data only for education, research, and offline evaluation of the matching lesion workflow. Obtain it from the official [HAM10000 repository](https://github.com/ptschandl/HAM10000_dataset), [Harvard Dataverse record](https://doi.org/10.7910/DVN/DBW86T), or [ISIC Archive](https://www.isic-archive.com/). Review the exact licence for every downloaded file before use; ISIC states that image licences can differ.

Do not upload patient faces, hair/scalp images, nail images, or identifiable clinical photographs into public datasets or source-control. Do not train on patient images without documented consent, ethics approval where required, de-identification, and a clinician-approved data-governance plan.

## Reproducible setup

1. Download the research data manually from the official source after accepting its current terms and record the source, version, licence, date, and checksum in a private experiment log.
2. Store it outside this repository, for example `~/DermamatrixResearchData/`; raw images and model checkpoints are ignored by Git.
3. Preserve patient-level splits and evaluate only on a held-out external dataset. Never report training accuracy as clinical performance.
4. Link a run to `docs/model-card.md`, including the data version, label mapping, preprocessing, metrics, calibration, failures, and subgroup results.

The project deliberately has no bulk-downloader: automated harvesting may violate source terms and bulk datasets are several gigabytes. The current downloadable research weight is installed by `backend/scripts/download_research_model.sh` and is sufficient to run the narrowly scoped dermatoscopic research path.
