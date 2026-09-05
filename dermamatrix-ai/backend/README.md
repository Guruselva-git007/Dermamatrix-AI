# DermaMatrix AI API (MySQL + runnable screening model)

The local Flask service serves the frontend and provides a prototype assessment endpoint.

```bash
cd /path/to/Dermamatrix-AI
python3 -m venv .venv
.venv/bin/pip install -r backend/requirements.txt
mysql -u root -e "CREATE DATABASE IF NOT EXISTS dermamatrix_ai CHARACTER SET utf8mb4"
./backend/scripts/download_research_model.sh
MYSQL_SOCKET=/tmp/mysql.sock MYSQL_USER=root .venv/bin/python backend/app.py
```

Open `http://127.0.0.1:8000`.

For the project-standard local flow, use `bash backend/scripts/run_app.sh` from the repository root. It starts the isolated MySQL service, uses the project virtual environment, and then runs this Flask service. VS Code also provides **DermaMatrix: Run locally (MySQL)** through F5 after a project Python interpreter and `backend/.env` are set up. The **DermaMatrix: Verify local stack** task checks the final Flask/MySQL connection without changing data.

If MySQL credentials are unavailable on demo day, the screening, CNN research classification, Grad-CAM attention map, care guidance, clinic search, and affiliate-ready catalogue remain available; only profile/assessment persistence is disabled. To re-enable it, start with `MYSQL_USER`, `MYSQL_PASSWORD`, and (when required) `MYSQL_SOCKET` set for your local MySQL account.

For local configuration, copy `backend/.env.example` to `backend/.env`, then add your MySQL credentials and genuine partner affiliate URLs. `.env` is automatically loaded and remains excluded from Git.

## Endpoints

- `GET /api/health` – local service, MySQL, and model health check
- `POST /api/auth/register` – creates a local account; only a salted password hash is stored
- `POST /api/auth/login` / `POST /api/auth/logout` – local account session controls
- `GET /api/auth/session` – restores the signed local browser session
- `POST /api/assessments` – accepts `image`, `area`, `duration`, `discomfort`, and `change` as multipart form data

The runnable `screening-triage-v1-demo` engine combines symptom inputs with image-quality reliability. A separate HAM10000 ResNet-34 research classifier can return seven lesion-class probabilities for a dermatoscopic lesion photo. It is **not for face photos, selfies, hair, nails, sweat glands, deficiency detection, medical advice, or diagnosis**. It is research-only and is not a medical device. The response explicitly flags future integrations for validated segmentation, Grad-CAM, and clinical risk models.
