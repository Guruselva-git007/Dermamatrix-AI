# Presentation runbook — 26 September 2026

## Start and verify

1. Double-click `Start DermaMatrix.command`, or run it from Terminal in this
   application's folder. Open <http://127.0.0.1:8000/>.
2. Run `bash backend/scripts/check_local_stack.sh` after syncing Git. It checks
   the local API, MySQL, model registry, exact research-weight hash, listener,
   and locally supplied teaching files. It also runs one real model inference
   on the verified local dermoscopy sample and checks its Grad-CAM output.
   A failure is a reason to fix the demo setup before presenting.
3. Keep the original files in the sibling `../DERMA PRESENTATION/` folder. Exact
   teaching-file matching stops working if a file is edited, re-saved, or
   converted. The folder and model weights are deliberately outside Git.

## Reliable demo order

| Step | Select | Local file or action | What to show |
| --- | --- | --- | --- |
| 1 | Skin → body skin | `../DERMA PRESENTATION/WhatsApp Image 2026-09-06 at 19.20.50.jpeg` | Check image consent and Presentation case matching. The exact pre-labelled scaly-plaque teaching example appears beside the ordinary assessment. It is not AI diagnosis. |
| 2 | Hair & scalp → scalp | `../DERMA PRESENTATION/Dandruff.jpg` | The same assessment flow shows a scalp teaching example. No hair-condition classifier ran. |
| 3 | Nails → fingernail | `../DERMA PRESENTATION/WhatsApp Image 2026-09-06 at 19.28.35.jpeg` | The nail teaching example is matched exactly. Nail-condition ML remains unavailable. |
| 4 | Skin → dermatoscopic single lesion | `../research-assets/original-sources/DermamatrixResearchData/skin-lesion-zip-v1/presentation-samples/ISIC_0000035_downsampled.jpg` | Leave Presentation case matching off. Confirm the dermatoscope attestation only for this genuine dermoscopic sample. The installed ResNet-34 research adapter can show a ranking and Grad-CAM. No calibrated condition likelihood or diagnosis is available. |
| 5 | Sweating | Answer the questionnaire | Show the transparent rule-contribution summary; no sweat image or trained tabular diagnosis model is used. |

The first three files were checked against the actual image-quality gate:
Skin and Hair are `GOOD`; Nails is `ACCEPTABLE`. Several other small teaching
files are legitimately marked `LOW_QUALITY`. Do not bypass that gate just to
make an older reference look successful.

Five newer personal photos in `../DERMA PRESENTATION/` are not verified teaching
cases. They were tested as ordinary Skin photos and received **no** teaching
label or disease classifier. Show them only with the subject's permission; if
Presentation case matching is selected, the result explicitly says no exact
case matched. These photos are never included in Git.

## What the project can accurately claim

- The installed upstream HAM10000 ResNet-34 weight loads and ran in a local
  dermoscopy smoke check. It is a research-only seven-class ranking on an
  attested single-lesion dermoscopic image, not a general skin diagnosis.
- Skin, Hair, and Nail ordinary photos receive image quality, local frame
  measurements, reported-context guidance, and clear model-availability
  notices. They do not have deployable condition classifiers.
- Sweat uses questionnaire rules rather than trained XGBoost or SHAP.
- The twenty teaching cases are exact SHA-256 file matches with pre-authored
  educational labels. This is not image recognition or model training.

The rejected SCIN, nail, and local dermoscopy experiments remain offline. The
available records lack the provenance, grouping, external evaluation,
calibration, and out-of-domain safeguards needed to promote new medical
classifiers. Training on the five unlabelled personal photos or changing UI
labels cannot fix those gaps. Do not describe unavailable modalities as
trained, clinically validated, or diagnostic.

Core assessment works without internet. External doctor/map and shopping
handoffs depend on live third-party pages. Guest results are not saved; use an
existing registered demo account if showing History or PDFs.
