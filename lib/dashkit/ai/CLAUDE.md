<!-- Per-area overlay. Loaded automatically when Claude Code opens a file in this directory tree. Read the closest overlay first. -->

# lib/dashkit/ai/CLAUDE.md

`dashkit.ai` — THE single LLM metering seam for the dashboards. Every Claude call goes through `call_claude` so every token lands in a `{domain}_ai_calls` row (cost accounting). Bypassing it = no cost log, no dashboard prediction. One callable per file (ADR-0011).

Parent overlay: `lib/dashkit/CLAUDE.md`.

## File map

| File | Job |
|---|---|
| `call_claude.py` | The metered Claude API call. API errors → `{"error", "detail"}` return value (caller branches; the miss is still logged). |
| `log_ai_call.py` | Insert one `{domain}_ai_calls` accounting row. **Best-effort (Tier-2)** — logs at WARNING, never breaks the feature. |
| `ensure_ai_calls_table.py` | Lazy `{domain}_ai_calls` table create. Tier-2. |
| `_config.py` | Reads `dashkit_ai_config` (model / max_tokens / temperature). Fail-open to documented defaults. |
| `_extract_json.py` | Fence-tolerant JSON extraction — internal, only `call_claude(expect_json=True)` uses it. |

## Gotchas

- Model defaults live in the `dashkit_ai_config` table (read at call time), not in `core/constants.py` — those name constants were deleted in the 2026-06-12 reset.
- Accounting is best-effort by doctrine; the Claude call must never fail because the cost row couldn't be written.
