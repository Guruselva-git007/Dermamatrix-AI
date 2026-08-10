# DermaMatrix AI API (MySQL + runnable screening model)

The local Flask service serves the frontend and provides a prototype assessment endpoint.

```bash
cd /path/to/Dermamatrix-AI
python3 -m venv .venv
.venv/bin/pip install -r backend/requirements.txt
mysql -u root -e "CREATE DATABASE IF NOT EXISTS dermamatrix_ai CHARACTER SET utf8mb4"
MYSQL_SOCKET=/tmp/mysql.sock MYSQL_USER=root .venv/bin/python backend/app.py
```

Open `http://127.0.0.1:8000`.

## Endpoints

- `GET /api/health` – local service, MySQL, and model health check
- `POST /api/assessments` – accepts `image`, `area`, `duration`, `discomfort`, and `change` as multipart form data

The runnable `screening-triage-v1-demo` engine combines symptom inputs with image-quality reliability. It is demonstrative only, not trained on patient data, and is not a disease classifier. The response explicitly flags future integrations for validated EfficientNetV2 classification, U-Net lesion segmentation, Grad-CAM, and XGBoost risk prediction. Do not use it for clinical decisions.
