<!-- Per-area overlay. Loaded automatically when Claude Code opens a file in this directory tree. Read the closest overlay first. -->

# lib/dashkit/core/audit/CLAUDE.md

`dashkit.core.audit` — per-domain `{domain}_activity` log (the dashboard audit trail). Identical schema per domain; functions parameterised by table name so every dashboard shares one implementation. One callable per file (ADR-0011).

Parent overlay: `lib/dashkit/CLAUDE.md`.

## File map

| File | Job |
|---|---|
| `log_activity.py` | Insert one activity row. **Best-effort (Tier-2)** — logs at WARNING, never breaks the feature. |
| `fetch_activity.py` | Read recent rows newest-first; propagates DB errors (caller decides). |
| `table.py` | `ensure_activity_table(conn, table_name)` — lazy create, name gated through `core.identifiers.validate_table_name`. |

## Gotchas

- This is the table `dashkit.secrets.activity` wraps for `ops_activity` rotation events — that wrapper inherits this Tier-2 best-effort policy.
- Every table name passes `validate_table_name` before interpolation.
