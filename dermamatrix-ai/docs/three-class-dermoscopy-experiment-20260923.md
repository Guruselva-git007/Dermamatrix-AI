# Three-class local dermoscopy experiment — 2026-09-23

## Scope and leakage control

One offline, MPS-accelerated ResNet-18 experiment used the read-only canonical `archive (1)/dataset` tree. The duplicated parallel tree was excluded. All 1,403 source images decoded; SHA-256 grouping excluded five train/test collision groups and collapsed one same-split duplicate. The manifest has 932 train, 97 validation, and 363 locked-test records. Patient/case IDs, near-duplicate control, source provenance, and a deployment licence record are unavailable.

## Training and selection

A smoke check passed decoding, tensor shape `[32, 3, 224, 224]`, forward/backward pass, optimizer step, checkpoint round-trip, and validation metrics. Epoch one trained only the head; epochs two through four fine-tuned the model. The test split was evaluated once, after validation selected epoch three by Macro F1 and then balanced accuracy.

| Checkpoint | Validation Macro F1 | Validation balanced accuracy |
| --- | ---: | ---: |
| Head-only baseline, epoch 1 | 0.392025 | 0.434644 |
| Selected fine-tuned checkpoint, epoch 3 | 0.754568 | 0.745291 |

## Locked test and decision

The locked test returned 0.738292 accuracy, 0.722637 balanced accuracy, 0.728377 Macro F1, 0.896076 macro AUROC, and 0.824233 macro AUPRC. Per-class recall was melanoma 0.601695, nevus 0.921986, and seborrheic keratosis 0.644231; the melanoma weakness is material. Temperature scaling used validation only (temperature 1.1): it improved validation log loss slightly but did not establish clinical calibration.

The OOD probe is not an OOD detector: a flat-grey synthetic image reached 0.555609 maximum softmax confidence and an out-of-scope local hair image reached 0.884297 for a dermoscopy label. Therefore the candidate is **REJECTED_FOR_APPLICATION_INFERENCE**. It is incompatible with the current seven-class runtime contract and lacks patient grouping, near-duplicate control, deployment provenance/licensing, external/prospective validation, and clinical validation. No runtime model, API contract, PIRS, risk, or severity code changed.
