# DermaMatrix AI — canonical workspace

This repository's active application is in [`dermamatrix-ai/`](dermamatrix-ai/).
That folder contains the Flask backend, browser frontend, tests, evaluation
records, and the detailed project README.

## Local run

```bash
cd dermamatrix-ai
python3 -m venv .venv
.venv/bin/pip install -r backend/requirements.txt
# Copy backend/.env.example to backend/.env and set local values.
DERMAMATRIX_PORT=8001 bash backend/scripts/run_app.sh
```

Open `http://127.0.0.1:8001`. The optional `DERMAMATRIX_PORT` override avoids
conflicting with another local development server; omit it when port 8000 is
available.

## Local-only recovery material

The canonical workspace may also contain ignored `research-assets/`,
`legacy-recovery/`, and `local-artifacts/` directories. They are deliberately
excluded from Git because they can include raw research data, local models,
generated reports, previous working copies, or secrets. They are not required
for a teammate to clone, test, or run the tracked application.

For the complete project guide and capability boundaries, see
[`dermamatrix-ai/README.md`](dermamatrix-ai/README.md).
