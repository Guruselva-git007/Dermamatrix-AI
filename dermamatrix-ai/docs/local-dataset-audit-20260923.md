# Local extracted-dataset audit — 2026-09-23

## Scope

All material in the ignored `research-assets/new datasets/` tree was treated as read-only. The inventory found 43 extracted dataset directories: 13 structured/non-image sources and 30 image-bearing sources. Raw data, path manifests, predictions, plots, calibration data, and checkpoints remain outside Git.

## Decisions

| Source group | Observed content | Domain | Decision |
| --- | --- | --- | --- |
| `archive (1)/dataset` | 1,403 224×224 images; train/validation/test; melanoma, nevus, seborrheic keratosis | Skin—dermoscopy | Selected for one offline experiment. The second identical `derma_disease_dataset/dataset` tree was excluded. |
| `archive (9) enhanced skin disease dataset` | 38,760 six-label clinical-style images | Skin—clinical photo | Excluded: earlier audit found 2,761 exact duplicate groups crossing supplied splits; labels are broad and provenance is unknown. |
| `archive....` | 262,874 images in 35 heterogeneous skin, hair, nail, healthy, and mixed-condition folders | Mixed | Excluded: no credible split, patient grouping, licence record, or single-modality task. |
| `archive (2)`, `archive skin disease 22 class` | 15,444 images each, `SkinDisease` train/test layout | Mixed skin | Excluded: indistinguishable layout/counts, no provenance or validation split. |
| `archive (6)` | 19,559 mixed DermNet-style clinical/hair/nail/infection images | Mixed | Excluded: mixed modality, source governance unknown. |
| `archive (10)` | 4,909 images, 31 train/test labels | Mixed skin | Excluded: unknown lineage/licence and no runtime-taxonomy parity. |
| `archive (12) dermaevolve` | 126,399 images, 13 lesion labels, no split | Dermoscopy/clinical uncertain | Excluded: no grouping, licence record, or locked test. |
| `archive (13)` | 878 images, nine labels, train/val only | Mixed skin | Excluded: no locked test or provenance. |
| `archive (11) analysis tool` | 6,304 mixed disease, skin-type, hair, and nail images | Mixed | Excluded: mixed task and unknown provenance. |
| `archive (4)`, `archive (9)` | 4,093 / 3,152 skin-type images | Skin type | Excluded: skin type is not a diagnosis target in the app. |
| `archive (12) lightweight` | 1,837 varicella/herpes/melanoma/measles/monkeypox images | Clinical photo | Excluded: mixed, out-of-runtime taxonomy and unknown provenance. |
| `archive (16)` | 1,113 bald/not-bald images | Hair/scalp | Excluded: binary appearance label without validated split or provenance. |
| `archive hair loss 3100`, `archive (21)`, `archive (24)` | 20 / 10 / 10 images with a few mask-named files | Hair / segmentation | Excluded: too small and no verified image-to-mask pairing. |
| `archive (15)`, `archive ...(12)` | 70 images/35 mask-named files; 1,660 segmented images | Segmentation | Excluded: no validated image/mask pairing manifest. |
| `archive (7)`, `archive.. (7)` | 9,770 / 5,137 artificial, SAM, and mixed skin images | Derived | Excluded: synthetic/derived lineage is leakage-prone for real-photo evidence. |
| `archive (8)`, `archive (18)`, `archive (20)`, `archive (22)`, `archive (23)`, `archive (25)`, `archive (26)`, `archive.. (11)`, `archive ..(4)`, `archive ... (12)` | Small collections (20–10,000 images), JSON/CSV sidecars, or unclear targets | Research / unsuitable | Excluded pending source, labels, split, and licence records. |
| `archive`, `archive (3)`, `archive (11)`, `archive (14)`, `archive (14) hairloss preprocessed`, `archive (17)`, `archive.. (8)`, `archive... (2)`, `archive ..(10)` | CSV-only structured sources | Structured/questionnaire | Not used for image training; no sweat model was created. |
| `archive (9) facial skin`, `archive skin condition recognition` | 4,233 / 1,457 images with incomplete or unclear labels | General photo | Excluded: insufficient class, split, and provenance evidence. |

## Leakage and labels in the selected source

The canonical three-class tree had 1,403 decodable images and zero corrupt files. SHA-256 grouping found six duplicate groups: five crossed the supplied train/test boundary and were excluded in full; one same-split duplicate was collapsed. The path manifest therefore has 1,392 records—932 train, 97 validation, and 363 locked-test. Patient/case IDs and near-duplicate control are unavailable.

Labels were preserved exactly as `melanoma`, `nevus`, and `seborrheic_keratosis`. They are not interchangeable with the current seven-class HAM10000 adapter.

## Readiness ranking

1. Skin/dermoscopy: the selected source is adequate for a compact offline research experiment only.
2. Hair/scalp: not ready; no governed source, grouped split, or clinically meaningful validated target.
3. Nail: not ready; no governed cohort or verified masks.
4. Segmentation: no confirmed image/mask pairs; no segmentation model was trained.
5. Sweat: no supervised cohort; the questionnaire route remains unchanged.
