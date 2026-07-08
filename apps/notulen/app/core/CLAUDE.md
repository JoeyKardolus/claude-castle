<!-- Per-area overlay. Read ../CLAUDE.md (notulen app) and ../../CLAUDE.md (notulen) first. -->

# apps/notulen/app/core/CLAUDE.md

Notulen domain logic (the `core/` layer), grouped into role subdirs. The seam re-exports what `entrypoints/` consumes (`process_job`, `git_writer_loop`, `session_files`, the recovery/cleanup loops); pipeline steps stay subpackage-internal — callers want the state machine, not its steps.

## Role subdirs

- `minutes/` — audio → Dutch notulen: `transcribe.py`, `notulen_writer.py` (Claude), `gpu_dispatch.py`, the per-upload state machine (`process_job.py`). See [`minutes/CLAUDE.md`](minutes/CLAUDE.md).
- `publish/` — git publication; `complete` means committed (ADR-0020). `github/` writer + `retry/git_writer_loop`. See [`publish/CLAUDE.md`](publish/CLAUDE.md).
- `sessions/` — recording-session lifecycle: tempfiles (`files.py`), S3 upload (`upload_audio.py`), stale retirement (`stale_cleanup.py`), startup crash recovery (`recovery.py`). See [`sessions/CLAUDE.md`](sessions/CLAUDE.md).

## Don't

- Don't import FastAPI here — HTTP routing lives in `entrypoints/`, env/S3/config in `shared/`.
- Don't mark a job `complete` without a GitHub commit URL (ADR-0020 invariant, owned by `publish/`).
