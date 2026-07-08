<!-- Per-area overlay. Read ../../../../CLAUDE.md (notulen) first. -->

# notulen/app/core/sessions/CLAUDE.md

Recording-session lifecycle: tempfile management, S3 upload, stale cleanup, and startup recovery. The design survives iOS tab eviction (2026-05-12 incident) by streaming chunks to disk during recording.

## File map

| File | Job |
|---|---|
| `files.py` | Tempfile store: `/tmp/notulen/<job_id>/audio.webm`, append-written per chunk; `cleanup()` is best-effort (`ignore_errors=True`) |
| `upload_audio.py` | Assembles tempfile → S3 (`notulen/audio/<job_id>.webm`) → updates job row with S3 key; Tier-1 throughout |
| `recovery.py` | Startup: resets jobs stuck in `processing` after a dashboard restart; GPU-path jobs checked against K8s before being marked `failed` (2026-05-21 incident) |
| `stale_cleanup.py` | Daemon loop: retires `recording` rows older than 6h; Tier-2 loop (tick swallows + retries) |
| `tests/test_session_files.py` | Pins the tempfile append/cleanup contract |

## Gotchas

- `recovery.py` deliberately leaves `recording` rows alone — the browser holds chunks in IndexedDB and can resume. `stale_cleanup.py` is what finally retires them (after 6h).
- `recovery.py` K8s liveness probe is fail-open: an unreachable cluster returns "all live" to avoid mass-failing GPU-path rows on a kubeconfig flap.
- `upload_audio.py` is Tier-1 at both seams (S3 upload + job-row update) — a silent loss here is the 2026-05-12 failure mode.
