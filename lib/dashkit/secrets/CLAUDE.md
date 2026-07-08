<!-- Per-area overlay. Loaded automatically when Claude Code opens a file in this directory tree. Read the closest overlay first. -->

# lib/dashkit/secrets/CLAUDE.md

`dashkit.secrets` — the **only WRITE path** for `ops_secrets` / `ops_secret_rotations` / `ops_secret_alerts` / `ops_activity`. One choke-point so the NEN 7510 §9.4.3 audit trail is single-sourced. Every rotation runner writes through here. One callable per file.

Parent overlay: `lib/dashkit/CLAUDE.md`.

## File map

| File | Job |
|---|---|
| `list_secrets.py` | Full registry read with computed age + status, urgent-first. |
| `get_secret.py` | One row by name (with computed status). |
| `list_secrets_by_kind.py` | Active secrets of one `rotation_kind` (rotation CronJobs find their work). |
| `list_pending_requests.py` | Secrets with `rotation_requested_at` set (UI "Rotate Now" queue). |
| `is_rotation_due.py` | Pure age-policy decision — rotate at 80% of `max_age_days` (6-day cushion before `SecretOverdue` fires). |
| `record_rotation_start.py` | Open a rotation audit row. **Tier-1 propagate.** |
| `record_rotation_finish.py` | Close the audit row + auto-resolve alerts. **Tier-1 propagate.** |
| `open_alert.py` | Idempotent stale-credential alert (unique on secret_id+severity+source). |
| `sweep_stale_secrets.py` | Walk registry, open alerts for overdue; returns per-status counts. |
| `rows.py` | Shared `SECRET_COLUMNS` + status buckets + `row_to_dict` — single source of the SELECT shape (was 3 verbatim copies pre-split). |
| `activity.py` | `ops_activity` rotation-event logging wrapper over `dashkit.core.audit`. Best-effort (Tier-2). |
| `tests/test_rotation_due_at_80_percent.py` | Pins the 80% rotation-due policy. (Tests in `tests/` per ADR-0038.) |

## Gotchas

- Status buckets (in `rows.py`): fresh `<0.80`, warn `<1.00`, stale `<1.50`, overdue `>=1.50` (also fires `SecretCritical`), unknown = never rotated.
- Structural rotation rows **propagate**; only the `ops_activity` log is best-effort.
- `rotation_verify` is the one declared read-only exception that SELECTs `ops_secret_rotations` directly (weekly audit) instead of going through here.
