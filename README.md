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

## Permanent project records

The canonical migration record and durable project memory are kept in the
tracked root [`docs/`](docs/) directory:

- [`DERMAMATRIX_PROJECT_CONTEXT.md`](docs/DERMAMATRIX_PROJECT_CONTEXT.md) — verified architecture, capabilities, constraints, and open work.
- [`DERMAMATRIX_MIGRATION_AUDIT.md`](docs/DERMAMATRIX_MIGRATION_AUDIT.md) — Git, legacy-workspace, artifact, and chat reconciliation evidence.
- [`DERMAMATRIX_FILE_INVENTORY.md`](docs/DERMAMATRIX_FILE_INVENTORY.md) — tracked and deliberately local-only asset inventory.
- [`chat-archive/INDEX.md`](docs/chat-archive/INDEX.md) — legacy Codex task archive status, including required manual transcript exports.

These records document local-only material without committing research data,
model weights, database files, or secret configuration values.

## Public teammate deployment

Railway is the selected deployment target: it hosts the Flask app and its
managed MySQL database together, while GitHub remains the shared source-code
repository. The deployment configuration and one-time account setup are in
[`dermamatrix-ai/docs/railway-deployment.md`](dermamatrix-ai/docs/railway-deployment.md).
