# DermaMatrix AI — migration audit

Migration date: 2026-09-23

## Safety baseline

The requested canonical root was verified as `/Users/gs/Chatgpt/Dermamatrix-AI`. Its configured `origin` is `https://github.com/Guruselva-git007/Dermamatrix-AI.git`, the `.git` form of the requested canonical URL. At baseline the worktree was clean, branch `main` was at `5502d6277b7104dacb3089ce2ef8b007dd91be6c`, and no staged or untracked tracked-scope changes existed.

`git fetch --all --prune` completed successfully. `HEAD` and `origin/main` resolved to the same commit, ahead/behind logs and diff statistics were empty, and the repository had one local branch (`main`), one corresponding remote branch, no tags, and 76 reachable commits. `git fsck --full --no-reflogs` reported no object errors.

No pull, merge, reset, rebase, force operation, deletion, code replacement, model retraining, or data movement was performed by this migration. The changes produced by this task are documentation and chat-archive files only.

## Legacy workspace discovery

The Codex project record for **Dermamatrix AI Powered Integumentary System** pointed to `/Users/gs/Documents/ChatGPT/Dermamatrix AI Powered Integumentary System`. That path is no longer present on disk, so it could not be compared as a live historical repository. Its Codex task metadata and accessible transcripts remain available.

The canonical workspace already preserves the recoverable local material, all ignored by the root `.gitignore`:

| Local root | Purpose and status |
| --- | --- |
| `legacy-recovery/chatgpt-sibling-worktree/` | Historical working copy with a local model, local MySQL data, evaluation records, older frontend utilities, and source snapshot |
| `legacy-recovery/college-working-copy/` | Older Git worktree at commits `bfdd3f6` and `14b1346`, with intentional uncommitted changes preserved intact |
| `research-assets/` | 47 GB of raw/local research data, notebooks, source archives, experiment checkpoints, training outputs, and extraction logs |
| `local-artifacts/` | Local reports and reference PDF material |

These roots are documented, not added to Git, because they can contain patient/research data, secrets, database data, locally licensed assets, and large binary files.

## Local source reconciliation

The preserved sibling worktree was compared with `dermamatrix-ai/`, excluding virtual environments, Python cache, local MySQL data, models, datasets, and Finder metadata. The canonical source had 115 comparable files; the sibling had 95.

The canonical source contains newer documentation, deploy/launcher configuration, VS Code configuration, research-audit scripts, training tests, and result-contract work. Nineteen same-path files differ, including `backend/app.py`, routing/contracts, scripts, tests, frontend app/HTML/CSS, requirements, and the ignored `.env`.

The sibling's only legacy-only source candidates are:

- `frontend/ui-utils.js`
- `frontend/tests/ui-utils.test.cjs`

They remain preserved in the sibling snapshot. They were not copied into the live app because current source does not reference them and automatic integration of older utilities would violate the preserve/compare/verify rule.

The 81 MB `ham10000_resnet34_research.ptw` weight is byte-identical between the canonical app and the sibling snapshot (SHA-256 `a800e9df…097f0250`). All 13 `results/skin-lesion-zip-v1/` artifacts are likewise byte-identical. No legacy-only result/model artifact required a copy.

The older college worktree is a distinct, dirty historical repository. It has modifications to its README, ignore/configuration, backend, frontend, and requirements, plus untracked snapshots, services, scripts, docs, and CSS. Its newer-looking files were not merged because it has only the two older reachable commits and unverified uncommitted state. It remains an archive for deliberate future comparison.

## Conversation migration

The legacy project and the local Codex session index were used to discover the five named legacy tasks. The session index also confirmed **Optimize app flow**, which was not in the initial current task listing.

| Legacy task | Task ID | Transcript status | Archive |
| --- | --- | --- | --- |
| Build medical diagnosis app | `019fe9e1-2ab8-7c93-9d71-c73551dd90b0` | PARTIALLY ACCESSIBLE: a paginated, very long transcript; preserved initial request and recent evidence, but raw full export was not returned | `docs/chat-archive/01-build-medical-diagnosis-app.md` |
| Optimize app flow | `01a082aa-fa15-7123-adb3-b502595fef3a` | ACCESSIBLE | `docs/chat-archive/02-optimize-app-flow.md` |
| Stabilize Dermamatrix AI | `01a0c950-5171-7aa2-bf17-3bcba5bc2c0d` | PARTIALLY ACCESSIBLE: meaningful latest records retrieved, but reader output was truncated | `docs/chat-archive/03-stabilize-dermamatrix-ai.md` |
| Recover Dermamatrix project | `01a0cad2-2d53-7dc2-b8e0-4994cb6f70ba` | ACCESSIBLE; the task itself was interrupted after initial recovery/install work | `docs/chat-archive/04-recover-dermamatrix-project.md` |
| Extract datasets sequentially | `01a0ccee-f443-7e73-bb66-0058ac798793` | PARTIALLY ACCESSIBLE: extraction record and latest task evidence retrieved; raw output exceeds transcript transport limits | `docs/chat-archive/05-extract-datasets-sequentially.md` |

`docs/chat-archive/INDEX.md` is the authoritative archive index. It explicitly identifies the raw transcript exports that remain manual actions. No missing chat content was fabricated.

The later task **Recover and run Dermamatrix AI** belongs to the new canonical project rather than the old project. It is not presented as a legacy chat, but its verified consolidation history explains why the above ignored recovery roots already exist.

## Dataset, model, and configuration status

- The application repository tracks source, declarative registry, scripts, tests, selected compact reports, and documentation. It does not track raw datasets, local checkpoints, local MySQL data, environment values, or virtual environments.
- `research-assets/new datasets/` is read-only local research material. Its prior sequential-extraction task is preserved in the archive and extraction logs; no extraction occurred in this migration.
- The only installed runtime image model is the local HAM10000 ResNet-34 research adapter for attested dermatoscopic single-lesion input. Calibration and OOD artifacts are not configured.
- SCIN, local ResNet-18, and nail ResNet-18 experiment records remain rejected/not-promoted and are not connected to Flask inference.
- Hair, Nail, segmentation, and validated sweat ML weights are missing by design, not silently substituted.
- `backend/.env` exists. Only variable names and presence were audited; no secret value is in this audit or chat archive.
- The ignored local MySQL tree exists and the live health endpoint reported `mysql-connected`.

## Application-state verification

Current migration verification passed 86 tests with one intentionally opt-in MySQL integration test skipped by default. The opt-in test was subsequently run with `DERMAMATRIX_RUN_MYSQL_INTEGRATION_TESTS=1` and passed. JavaScript/Python/static checks, launcher syntax checks, live `/api/health`, live model registry, static serving, and a guest-browser dashboard/assessment-entry check also passed.

The current live registry reports:

- Skin: `RESEARCH_ONLY`, runtime inference available only for attested dermatoscopic single-lesion input.
- Hair: `NOT_AVAILABLE`.
- Nails: `NOT_AVAILABLE`.
- Sweat: `QUESTIONNAIRE_ASSESSMENT`.

One visual discrepancy was observed: the assessment header says `STEP 1 OF 3` while four stage labels are visible. It is recorded in the project context as OPEN; no feature/UX modification was made during migration.

## Conflicts and resolutions

| Finding | Resolution |
| --- | --- |
| Stale legacy project path is missing | Recorded as inaccessible on disk; preserved copies and Codex metadata were used instead |
| Canonical app differs from preserved sibling source | Current canonical source retained; old source preserved untouched |
| Older college worktree has dirty changes | Preserved in ignored archive; no automatic merge |
| Legacy chats exceed accessible raw transcript output | Archived useful technical records, marked partial, and listed for manual export |
| Historical claims of broad image diagnosis/segmentation conflict with current evidence | Current capability contract prevails; unsupported capabilities remain unavailable |
| Large/local/sensitive data cannot enter Git | Retained in ignored local roots and inventoried rather than committed |

## Manual actions still required

1. Export/copy full raw text and any selected attachment binaries for the three partially archived legacy tasks if a verbatim permanent transcript archive is required.
2. Review the preserved `frontend/ui-utils.js` and `frontend/tests/ui-utils.test.cjs` only in a separately authorized change task; do not automatically revive them.
3. Resolve the open assessment-step copy mismatch in a targeted UI bug-fix task.
4. Provide a deployment account and production configuration only if public hosting is desired. A Railway configuration is present, but no public deployment was verified here.
