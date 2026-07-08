<!-- Per-area overlay. Loaded automatically when Claude Code opens a file in this directory tree. Read the closest overlay first. -->

# lib/dashkit/frontend/CLAUDE.md

Static frontend assets shared by every dashkit dashboard. Served by `dashkit.core._frontend_static` at `/static/dashkit/{filename}` (wired by `make_dashboard_app`). Vanilla JS (IIFE → `global.dashkit`), no build step. Dashboards load these via `<script src="/static/dashkit/…">`.

Parent overlay: `lib/dashkit/CLAUDE.md`.

## File map

| File | Job |
|---|---|
| `api.js` | Shared `apiGet`/`apiPost` fetch helpers (`credentials: 'include'` — Caddy forward-auth cookies). |
| `audit.js` | Generic activity-feed renderer over `/api/audit-log`; `dashkit.registerActivityLabels({...})` for per-domain verbs. |
| `dashboard-common.js` | `escapeHtml()` + `formatDate()` shared utilities. |
| `toast.js` | Toast + confirm-dialog helpers (host page provides `#toast-container` / `#confirm-overlay`). |
| `view.js` | View-toggle pattern (`switchView(name)`; dispatches `dashkit:view-shown` for lazy-load). |
| `base.css` | Shared design system (navy/sky/slate palette + UI tokens). |

## Gotchas

- No bundler/transpile — these ship verbatim. Keep them browser-runnable as-is.
- `toast.js` reuses `escapeHtml` from `dashboard-common.js` when present, with a local fallback for standalone use.
