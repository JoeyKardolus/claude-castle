<!-- Per-area overlay. Read ../../../CLAUDE.md (notulen) first. -->

# notulen/app/gates/CLAUDE.md

Upload validation gates — all raise `HTTPException` with Dutch user copy on violation (module-standard §5.4 dashboard gate convention). Nothing is swallowed here.

## File map

| File | Job |
|---|---|
| `assembled_size.py` | Assembled tempfile size: ≥10 KB (rejects silence), ≤100 MB (~3h opus); called at `/api/upload/finalize` |
| `chunk_seq.py` | Chunk sequence gate: in-order check; 409 on a gap (browser re-sends from `last_seq+1`); 400 on non-positive seq |
| `chunk_size.py` | Single-chunk size: rejects empty or >10 MB; called at `/api/upload/chunk` |
| `meeting_date.py` | Parses `YYYY-MM-DD` from the upload-start form; 400 on bad format |
| `queue_capacity.py` | Concurrent-job cap (`MAX_QUEUED_JOBS = 2`, VM memory ceiling); 429 when at cap; DB errors **propagate** (Tier-1 — an unreachable DB must 5xx, not admit unlimited jobs) |
| `tests/test_upload_gates.py` | Pins all gate invariants (the 2026-05-12 iOS-eviction fix contract) |

## Gotchas

- `chunk_seq.py` returns a verdict string for in-order and duplicate chunks but **raises** on gaps/protocol violations — callers must branch on the return value.
- `queue_capacity.py` is the only gate with a Tier-1 (propagating) failure; all others are pure-raise gates.
