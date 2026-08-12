# DermaMatrix AI

An educational prototype for integumentary-health screening workflows. It covers skin-and-sweat, hair/scalp, and nail concerns with image upload, consent, usability checks, a reported-concern priority, and a narrow dermatoscopic lesion research path.

> **Safety note:** This app is not a medical device and cannot diagnose disease. It is a college-project prototype designed to support, not replace, a qualified clinician.

The India-aligned guardrails and production requirements are documented in `docs/india-compliance-guardrails.md`. The app never issues a verified diagnosis or prescription; registered medical practitioner review remains mandatory.

## What an uploaded image can do today

- **Face, hair/scalp, nail, or ordinary skin photo:** image-usability feedback and a non-diagnostic discussion-priority based on what the user reports. It does not identify a deficiency or classify a disease.
- **Single, in-focus dermatoscopic skin-lesion image:** the optional HAM10000 ResNet-34 research model can show research label probabilities and Grad-CAM attention after the user confirms the capture type. It is not lesion segmentation, a diagnosis, or clinical decision-making.

See [the model card](docs/model-card.md) and [research-data protocol](docs/research-data-protocol.md) before any model training or evaluation.

## Run the complete app (MySQL required)

```bash
python3 -m venv .venv
.venv/bin/pip install -r backend/requirements.txt
mysql -u root -e "CREATE DATABASE IF NOT EXISTS dermamatrix_ai CHARACTER SET utf8mb4"
MYSQL_SOCKET=/tmp/mysql.sock MYSQL_USER=root .venv/bin/python backend/app.py
```

Open `http://127.0.0.1:8000`.

## Project layout

- `frontend/` – accessible, responsive web prototype with a complete assessment flow.
- `backend/` – Flask API, MySQL persistence, and the runnable screening-triage engine.
- `docs/` – model and safety documentation.
