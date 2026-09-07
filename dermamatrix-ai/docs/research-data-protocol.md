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

The SCIN adapter is intentionally **manifest-bound**, not a general-purpose
bulk downloader. It requires explicit licence acknowledgement and downloads
only images already selected by `prepare_scin_clinical_manifest.py`; its output
must remain outside Git. The current downloadable research weight is installed
by `backend/scripts/download_research_model.sh` and is sufficient to run the
narrowly scoped dermatoscopic research path.

## Nail feasibility data run (rejected; reproducible offline only)

The project also records one licensed, task-matched nail experiment without
turning it into application capability. The source is Han SS (2017),
[*Model Onychomycosis Training Datasets (JPG thumbnails) and Validation
Datasets*](https://doi.org/10.6084/m9.figshare.5398573.v2), CC BY 4.0. It
contains labelled thumbnail/contact-sheet data plus validation cohorts; review
the current Figshare record and attribution terms before download.

Keep the downloaded ZIP files and all outputs in a private research-data
directory outside the repository. After source integrity checking, a reproducible
offline preparation run is:

```bash
.ml-venv/bin/python backend/scripts/prepare_onychomycosis_dataset.py \
  --a1-zip /absolute/research-data/train_a1.zip \
  --external-zip /absolute/research-data/external_validation.zip \
  --output-dir /absolute/research-data/prepared-run \
  --max-per-class 3000
```

The utility derives normal-appearing nail, nail dystrophy, and onychomycosis
crops from A1 contact sheets; source-contact-sheet grouping prevents tile
leakage but **does not** establish patient-level separation. It extracts the
B1/B2/C/D cohort as a locked external set. The source external cohort has no
normal-appearing nail class.

Train only after retaining the generated `dataset_summary.json` and
`manifest.csv` with the run:

```bash
.ml-venv/bin/python backend/scripts/train_onychomycosis_classifier.py \
  --dataset-dir /absolute/research-data/prepared-run \
  --output-dir /absolute/research-data/experiment-run \
  --epochs 5 --batch-size 64 --device mps
```

The training script calibrates with the independent validation split, evaluates
the internal and locked external sets, saves a versioned model/calibration/OOD
record, and rejects the result unless its preconfigured thresholds pass. The
recorded 2026-09-07 experiment failed those thresholds and must not be copied
into `backend/models/` or connected to Flask inference. See the model card and
dataset registry for its measured result and limitations.
