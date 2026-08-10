# DermaMatrix AI

An educational prototype for integumentary-health screening workflows. It covers skin, hair, nail, and sweat-gland assessments with image upload, lesion-region preview, explainability placeholders, and a Personalized Integumentary Risk Score (PIRS).

> **Safety note:** This app is not a medical device and cannot diagnose disease. It is a college-project prototype designed to support, not replace, a qualified clinician.

The India-aligned guardrails and production requirements are documented in `docs/india-compliance-guardrails.md`. The app never issues a verified diagnosis or prescription; registered medical practitioner review remains mandatory.

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
