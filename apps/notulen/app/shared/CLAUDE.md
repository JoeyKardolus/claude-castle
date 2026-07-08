<!-- Per-area overlay. Read ../../../../CLAUDE.md (notulen) first. -->

# notulen/app/shared/CLAUDE.md

Cross-layer primitives: config constants, DB schema bootstrap, job-row updates, S3 client, and slug generation. No domain logic here.

## File map

| File | Job |
|---|---|
| `config.py` | Env-derived constants (template path, S3 bucket/region); re-exports S3 config from dashkit — dashkit is the single source of truth for stack-wide S3 constants |
| `jobs_table.py` | `CREATE TABLE notulen_jobs` + idempotent live-column additions + ADR-0020 backfill; Tier-1 (DDL errors propagate) |
| `update_job.py` | Parameterised `UPDATE notulen_jobs` with column allowlist (SQL-injection guardrail); Tier-1 — all callers get the exception |
| `s3.py` | boto3 client (S3_* env config, retry config); lazy import; never swallows — callers own the failure policy |
| `slug.py` | Filename-safe slug from meeting title (used by `core/publish/target_path.py` and the AI-call `doc_path` label) |

## Gotchas

- `update_job.py` uses a **column allowlist** — add new columns there before using them in any UPDATE.
- `s3.py` imports boto3 lazily — the package imports without boto3 installed (IEC 62304 gate import hygiene).
- `config.py` reads env at module scope (sanctioned single-config exception) — anything a test must vary should be read at call time in the consumer, not here.
