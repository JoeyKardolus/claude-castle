<!-- Per-area overlay. Read ../../../CLAUDE.md (notulen) and ../../../../CLAUDE.md (dashboards) first. -->

# notulen/app/entrypoints/CLAUDE.md

HTTP surface for the notulen dashboard: thin route handlers only — gates and domain logic live in `gates/` and `core/` respectively.

## File map

| File | Job |
|---|---|
| `main.py` | Dashkit factory bootstrap; mounts all routers; spawns background threads (git writer loop, stale-cleanup loop, startup recovery) |
| `spa_routes.py` | Serves `inputs/dashboard.html` + `inputs/dashboard.js` (the recorder SPA); `/{filename}` catch-all — include **last** in main.py |
| `upload_routes.py` | Chunked-upload lifecycle: `/api/upload/{start,chunk,finalize,abort,state}` |
| `jobs_routes.py` | Read/delete job rows: `GET /api/jobs*`, `DELETE /api/jobs/{id}` |
| `health_routes.py` | `/healthz` (DB-ping liveness, ADR-0013 schema) + `/api/health/notulen/full` (rich UI banner) |
| `tests/test_healthz.py` | Pins the ADR-0013 body schema and fail-open behaviour for the blackbox probe |

## Gotchas

- `/healthz` is **always HTTP 200**; `ok: false` carries bad news — the blackbox-exporter matches on the body, not status.
- `spa_routes.py` has a root catch-all: always include it last.
- The three startup background threads (`git_writer_loop`, `cleanup_stale_recordings_loop`, `recover_interrupted_jobs`) are daemon threads launched from `main.py` on the FastAPI `startup` event — not cron, not separate processes.
- `jobs_routes.py` fail-policy split: list route is fail-open (returns empty list on DB error); delete is fail-closed (S3 audio delete propagates before the row delete).
