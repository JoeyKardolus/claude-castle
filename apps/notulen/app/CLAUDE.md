<!-- Per-area overlay. Loaded automatically when Claude Code opens a file in this directory tree. Read the closest overlay first. -->

# apps/notulen/app/CLAUDE.md

FastAPI 5-layer app for the notulen dashboard (served at `notulen.{CASTLE_DOMAIN}`). uvicorn target: `apps.notulen.app.entrypoints.main:app`. Read [`apps/notulen/CLAUDE.md`](../CLAUDE.md) for the twin rule and image layout.

## Layer orientation

| Layer | Lives in | Job |
|---|---|---|
| `entrypoints/` | `entrypoints/` | The only FastAPI-importing layer. `main.py` is the thin bootstrap (DashkitConfig + factory + routers + startup hooks); route modules: spa / upload / jobs / health. |
| `gates/` | `gates/` | Input validation on chunked-upload requests (one check per file: meeting date, chunk size/seq, assembled size, queue capacity). Auth is NOT here — it's Caddy SSO. |
| `core/` | `core/` | Domain logic in role subdirs: `minutes/` (download → transcribe → write), `publish/` (ADR-0020 GitHub commit loop), `sessions/` (recording lifecycle). |
| `shared/` | `shared/` | Config, slug grammar, S3 client, `notulen_jobs` table bootstrap + allowlisted update. No route or routing code. |
| `inputs/` | `inputs/` | Committed SPA assets (`dashboard.html` + `dashboard.js`) served with no-store. |

## Carve-out (ADR-0012)

Framework-required loose files only: `__init__.py`, `conftest.py`, `Dockerfile`. The `Dockerfile` builds the notulen-dashboard image.

## Gotchas

- The GPU worker is NOT in this tree — it ships from `apps/notulen/entrypoints/worker.py` as its own image (the declared twin; see the parent overlay).
- `conftest.py` sets the placeholder `DB_URL` that dashkit's import-time fail-fast requires.
- Package-absolute imports only; no `sys.path` tricks (the Dockerfile mirrors the repo path inside the container).
