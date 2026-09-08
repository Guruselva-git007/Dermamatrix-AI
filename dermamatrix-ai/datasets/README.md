# Research data layout

This repository contains only this layout and the source-governance registry;
it does **not** contain medical images, source metadata, trained weights,
calibration artifacts, or predictions.

Use an external, access-controlled research root such as
`/Users/gs/DermamatrixResearchData`, then point manifest, acquisition, training,
and evaluation scripts at that root. Review the source license before any
download. Do not place raw data in the folders below.

| Folder | Status | Intended purpose |
| --- | --- | --- |
| `scin/` | Governed for offline research | SCIN clinical-photo manifests and source-bound acquisition only; no app deployment. |
| `isic/` | Not enabled | Possible dermoscopic external-validation source after per-collection license review. |
| `scin_like/` | Reserved | Future governed clinical-photo source, not a claim of SCIN equivalence. |
| `future_datasets/` | Reserved | Future sources only after provenance, consent, label, duplicate/split, and license review. |

The declarative companion record is [`../dataset_registry.json`](../dataset_registry.json).
