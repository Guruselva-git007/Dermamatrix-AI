# Local model sourcing and verification (2026-09-25)

Assessment inference runs inside DermaMatrix with PyTorch on the local machine. No provider, account, API key, or network request is used during an upload. Public model downloads occur only through the explicit one-time installer scripts; checkpoint SHA-256 values and model class mappings are pinned in the adapters.

| Route | Local model | Evidence and scope |
| --- | --- | --- |
| Attested single-lesion dermoscopy | Existing HAM10000 ResNet-34 | Seven dermoscopy labels. Training transform and Grad-CAM run locally. No version-matched calibration, external clinical validation, or OOD detector is installed. Ordinary photos never enter this adapter. |
| Declared ordinary Skin photo | [RevelaCap clinical Skin v1](https://huggingface.co/RevelaCap/clinical-skin-condition-v1), MIT, revision `a614ae0c12e8590f06d4f25b529b6b568a517903`; SHA-256 `eba9a581505c60cee98152c790c4113a1549c691248d518cc5d1e7097feb20bc` | Five broad classes; EfficientNet-B0. Published transform and class mapping are checked against the checkpoint. Publisher reports balanced accuracy 0.67 on 1,515 mixed-source test photos, and SCIN smartphone subset macro F1 0.43. Research ranking only. |
| Declared Nail close-up | [shibarashii Nail model](https://huggingface.co/shibarashii/nail-disease-detection), MIT, revision `661603d35bab2904055d4d4a943bf305b03a59f9`; SHA-256 `6c58cd98c9368268115d00f6acd6d1f03dba73132eaacd15cbfa9cf9dfb5bf19` | Ten classes; ConvNeXt Tiny. [Publisher metrics](https://huggingface.co/shibarashii/nail-disease-detection/blob/main/best_models/convnexttiny/evaluation/metrics.json) report 88.9% accuracy on 307 internal test images. Training preprocessing, patient split, and external validation are unpublished; the adapter explicitly marks its conventional ImageNet transform as an assumption. Research ranking only. |
| Hair/scalp | No deployable checkpoint | Public candidates found lacked a verified class map and evaluation, a usable license, or safe weights-only loading. Existing local broad Hair folders have conflicting labels/provenance. The route retains image measurements and reported-concern guidance; no disease label is invented. |

## Local checks

- The clinical Skin checkpoint loaded strictly, and its embedded class order matched the published mapping. On 32 local SCIN Eczema/Urticaria photos, it matched 23 labels. These photos may overlap the publisher's training/evaluation sources, so this is a pipeline check, **not independent validation**.
- The Nail checkpoint loaded strictly as a ten-class ConvNeXt Tiny. On 17 locally available web-photo files with filename labels covering Beau's lines, clubbing, koilonychia, and onychogryphosis, the assumed transform matched 6. The files lack governed ground truth and may overlap upstream data. This check cannot establish accuracy and reinforces the low-evidence display rule.
- Full Flask assessment requests generated logits, top-five rankings, metadata, and separate PIRS/severity/concern outputs for Skin and Nails. Repeating the same image after another upload reproduced the same result. No source pixels or maps enter saved history or PDF reports.

Raw softmax numbers compare only a model's trained classes. They are never presented as calibrated likelihoods or clinical confidence. The Nail "Healthy Nail" class and the clinical Skin "lesion review" class remain research rankings, not normal-health or cancer findings. No class label selects medication or products. These research adapters are not validated for diagnosis or treatment decisions.
