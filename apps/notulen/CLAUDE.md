# apps/notulen/CLAUDE.md

Meeting-minutes (notulen) app, served at `notulen.{CASTLE_DOMAIN}`. The browser records audio in chunks, the backend transcribes it (CPU whisper by default, GPU worker if a cluster is configured), and Claude turns the transcript into structured minutes using the template. Minutes language is `MINUTES_LANGUAGE` (ISO 639-1, default `nl` = Dutch). Optionally, finished minutes are committed to a GitHub repo (`NOTULEN_GITHUB_REPO`; unset = publishing skipped, jobs still complete).

## What lives where

```
apps/notulen/
  app/          FastAPI dashboard, 5 layers:
    entrypoints/  routes + main.py bootstrap (the only FastAPI-importing layer)
    gates/        input validation on chunked uploads (one check per file)
    core/         domain logic: minutes/ (transcribe + write), publish/ (GitHub
                  commit loop), sessions/ (recording lifecycle)
    shared/       config, slug grammar, S3 client, notulen_jobs table helpers
    inputs/       the SPA (dashboard.html/js, no build step — edit directly)
  entrypoints/  worker.py — the GPU worker (self-contained twin, see below)
  inputs/       notulen_template.md (the minutes template; also baked into
                the worker image)
  shared/       worker_constraints.txt (pinned deps for the worker image)
```

Related pieces elsewhere in the repo:

- `lib/dashkit/` — shared dashboard library (app factory, DB access, Claude
  call + cost accounting). The app imports it as `dashkit`.
- `infra/gpu-jobs/` — optional K8s GPU Job dispatch (`gpu_jobs` package).
  Without it (or without `KUBECONFIG_DATA`), the app transcribes on CPU —
  that fail-open fallback is the default working path.
- `infra/docker/notulen/Dockerfile` — dashboard image (build context = repo root).
- `infra/docker/notulen-worker/Dockerfile` — GPU worker image (optional tier).

## The dashboard/worker twin rule

`entrypoints/worker.py` is deliberately self-contained: the worker image
copies ONLY that file plus the template, with no import path back to `app/`.
It therefore duplicates three things from the dashboard side:

- the transcript block grammar of `app/core/minutes/transcribe.py`,
- the Claude prompt of `app/core/minutes/notulen_writer.py`,
- the job-update column allowlist of `app/shared/update_job.py`.

Keep the twins in sync by hand — the duplication IS the design, not drift.
Never import `app/` modules from `entrypoints/worker.py`.

## Running locally

```bash
uv sync --extra whisper           # base deps + CPU transcription
export DB_URL=postgresql://user:pass@localhost:5432/castle   # required at import
uv run uvicorn apps.notulen.app.entrypoints.main:app --reload
```

Run from the repo root — imports are package-absolute (`apps.notulen.*`,
`dashkit`, `gpu_jobs`) and resolve because the root is on `sys.path`.

Key env vars (all optional unless noted):

| Var | Meaning |
|---|---|
| `DB_URL` (required) | PostgreSQL DSN (`DB_URL_OPS` overrides if set) |
| `ANTHROPIC_API_KEY` | Claude API key for minutes generation |
| `S3_BUCKET` / `S3_REGION` / `S3_ENDPOINT` / `S3_ACCESS_KEY` / `S3_SECRET_KEY` | audio storage; endpoint unset = AWS, creds unset = boto3 default chain |
| `MINUTES_LANGUAGE` | transcription + minutes language (default `nl`) |
| `NOTULEN_TEMPLATE` | path to a custom minutes template |
| `NOTULEN_GITHUB_REPO` / `NOTULEN_GITHUB_PAT` / `NOTULEN_GITHUB_BRANCH` / `NOTULEN_TARGET_DIR` | optional publishing of finished minutes to GitHub |
| `KUBECONFIG_DATA` + `NOTULEN_WORKER_IMAGE` + `CASTLE_K8S_NAMESPACE` | optional GPU tier (see `infra/gpu-jobs/`) |

Tests: `uv run pytest apps/notulen` (unit tests need no DB or network; the
GitHub integration test is env-gated behind `NOTULEN_INTEGRATION_TESTS=1`).

## Don't

- Don't store audio on disk permanently; S3 key is `notulen/audio/<job_id>.webm`, tempfiles live in `/tmp/notulen/`.
- Don't mark a job `complete` inline in the pipeline — `core/publish/` owns the complete-means-committed invariant (with publishing unset, the writer completes jobs with a sentinel URL).
- Don't add `sys.path` tricks; the Docker images mirror the repo layout instead.
