<!-- Per-area overlay. Read ../../../../CLAUDE.md (notulen) first. -->

# notulen/app/core/minutes/CLAUDE.md

Per-job pipeline state machine: download audio → transcribe → write notulen. CPU-path only (GPU path runs as a twin in `notulen/entrypoints/worker.py`).

## File map

| File | Job |
|---|---|
| `process_job.py` | Pipeline spine: S3 download → GPU dispatch attempt → CPU fallback → notulen write → mark `committing` (ADR-0020) |
| `gpu_dispatch.py` | Try-dispatch K8s GPU job; fails OPEN (returns `False`) so CPU fallback always works; alerts ops on failure (Tier-2 swallow) |
| `transcribe.py` | CPU whisper-medium fallback (no speaker labels); lazy `faster_whisper` import |
| `notulen_writer.py` | Claude API call: template + strict invul-rules → structured Dutch notulen markdown |

## Gotchas

- `process_job.py` is the Tier-1 spine: any unhandled error marks the job `failed` and propagates.
- `gpu_dispatch.py` is deliberately fail-open — CPU speed regression is preferable to dropping a recording. The alert path inside it is itself a Tier-2 swallow (throttled).
- `notulen_writer.py` is a declared twin with `entrypoints/worker.py` — the prompt and template path are intentionally duplicated. Edit both when the notulen format changes.
- `process_job.py` persists markdown as `committing` BEFORE `core/publish` commits to git (ADR-0020 invariant — never set `complete` inline).
