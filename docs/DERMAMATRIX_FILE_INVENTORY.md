# DermaMatrix AI — file and artifact inventory

Inventory date: 2026-09-23

## Tracked canonical repository

At migration baseline, Git tracked 121 files totaling 7,080,466 bytes. The runnable product is intentionally nested at `dermamatrix-ai/`.

| Area | Important paths | Status |
| --- | --- | --- |
| Root identity | `README.md`, `.gitignore`, `dermamatrix-ai/` | Tracked canonical entry point |
| Frontend | `dermamatrix-ai/frontend/index.html`, `app.js`, CSS layers | Tracked runtime UI |
| Backend/API | `dermamatrix-ai/backend/app.py`, domain services, router, contracts | Tracked runtime server |
| Auth/database support | `backend/app.py`, `backend/.env.example`, `backend/scripts/run_local_mysql.sh` | Code/template tracked; real credentials/data local only |
| ML/inference code | `lesion_classifier.py`, `model_service.py`, `model_metadata.py`, `segmentation_service.py`, `dataset_registry.py`, evaluation/training scripts | Tracked code; capability varies by model |
| Tests | `backend/tests/test_*.py` | Tracked regression/integration coverage |
| Documentation | `dermamatrix-ai/docs/`, root `docs/` | Tracked technical/project memory |
| Results | `dermamatrix-ai/results/skin-lesion-zip-v1/` | Tracked compact experiment reports, predictions, plots, and manifest |
| Launch/deployment | `Start DermaMatrix.command`, `scripts/install_macos_local_service.sh`, `Dockerfile`, `.vscode/`, Railway guide | Tracked |
| Dataset declaration | `DATASETS.md`, `dataset_registry.json`, dataset placeholders | Tracked declarative layout only |

## Local-only and Git-ignored material

| Path | Approximate size | Why it is local-only |
| --- | ---: | --- |
| `research-assets/` | 47 GB | Raw/local research data, notebooks, archives, experiment checkpoints, source metadata, extraction records |
| `legacy-recovery/` | 1.1 GB | Historical sibling and college worktrees; older uncommitted material is preserved, not live |
| `local-artifacts/` | 2.4 MB | Local reports and reference PDF material |
| `dermamatrix-ai/.venv/` | 1.0 GB | Machine-specific Python environment |
| `dermamatrix-ai/backend/.local-mysql/` | 199 MB | Local MySQL service/data files; no database dump is tracked |
| `dermamatrix-ai/backend/models/` | 81 MB | Local research model weight |
| `dermamatrix-ai/backend/.env` | 4 KB | Secrets and machine-specific configuration |

The root ignore policy excludes `research-assets/`, `legacy-recovery/`, and `local-artifacts/`. The application ignore policy excludes environments, Python cache, `dermamatrix.db`, `.env`, local MySQL data, model weights, datasets, raw research data, and similar machine-specific outputs.

## Models and weights

| Local artifact | Status | Notes |
| --- | --- | --- |
| `backend/models/ham10000_resnet34_research.ptw` | PRESENT, 81 MB, ignored | SHA-256 `a800e9df6330d377ed4a37b32e2cbd78821da5e9c3980a30bd42155d097f0250`; exact byte match with sibling snapshot; research-only dermoscopy adapter |
| `research-assets/original-sources/DermamatrixResearchData/skin-lesion-zip-v1/final-run/model.pt` | PRESENT, local only | Offline experiment artifact; not automatically runtime-connected |
| `research-assets/original-sources/DermamatrixResearchData/scin-v1/**/model.pt` | PRESENT, local only | SCIN rejected experiments; not runtime-connected |
| `research-assets/training-runs/three-class-dermoscopy-20260923/model.pt` | PRESENT, local only | Rejected/not-promoted local research candidate |
| Hair/scalp runtime weight | MISSING | No accepted governed model |
| Nail runtime weight | MISSING | Research checkpoint deliberately not loaded after failed thresholds |
| Segmentation runtime weight | MISSING | No validated image/mask model deployment |
| Calibration/OOD runtime artifact | MISSING | Runtime correctly reports unavailable/not configured |

## Dataset and experiment roots

| Path | Status |
| --- | --- |
| `dermamatrix-ai/datasets/` | Tracked placeholder layout only (`scin`, `isic`, `scin_like`, `future_datasets`) |
| `dermamatrix-ai/dataset_registry.json` | Tracked governance declaration; does not enable runtime deployment |
| `research-assets/new datasets/` | 43 extracted local dataset directories; read-only. Local audit documents decisions and exclusions |
| `research-assets/original-sources/` | Preserved source archives, notebooks, reference images, original datasets, and local research roots |
| `research-assets/training-runs/` | Local experiment outputs, including the three-class dermoscopy candidate |
| `dermamatrix-ai/results/skin-lesion-zip-v1/` | Tracked compact record. All 13 files hash-match the sibling worktree's corresponding results |

Important rejection evidence is tracked in the application documentation: SCIN, nail feasibility, local source intake, three-class dermoscopy, and the seven-class comparison. Do not treat a local archive or a checkpoint as permission to connect it to inference.

## Database and configuration

`backend/.local-mysql/data/dermamatrix_ai/` contains local tables for users, auth accounts, consent records, preferences, medical histories, assessments, analysis records, routines, progress check-ins, reports, clinical-review requests, and schema migrations. It is present and ignored.

`backend/.env` is present and has the same variable-name set as `backend/.env.example`. Values are not recorded. See `DERMAMATRIX_PROJECT_CONTEXT.md` for the name-only environment inventory.

## Legacy preservation and differences

| Historical asset | Disposition |
| --- | --- |
| Missing former Documents workspace | Its registered path no longer exists; recorded in migration audit |
| `legacy-recovery/chatgpt-sibling-worktree/` | Preserved intact, ignored, no automatic merge |
| `legacy-recovery/college-working-copy/` | Preserved intact, ignored, dirty historical Git worktree |
| Legacy-only `frontend/ui-utils.js` and `frontend/tests/ui-utils.test.cjs` | Preserved in sibling snapshot; not copied into live source |
| Local model and 13 experiment artifacts shared by sibling/current source | Hash-compared; identical |
| Original research assets/reports/reference PDFs | Located under ignored canonical roots; documented, not duplicated into Git |

## Missing expected artifacts

- No tracked or configured calibration artifact for the installed research classifier.
- No fitted runtime OOD detector.
- No Hair/scalp, Nail, or segmentation model weight approved for runtime.
- No raw research dataset, patient/case split data, source-sensitive manifest, or database dump in Git by design.
- No configured password-reset email provider.
- No verified public deployment URL or managed production database credentials.
- Complete verbatim raw exports for the partially accessible legacy conversations are not in the repository; see `docs/chat-archive/INDEX.md`.
