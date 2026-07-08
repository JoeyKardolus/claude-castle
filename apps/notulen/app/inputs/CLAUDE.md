<!-- Per-area overlay. Loaded automatically when Claude Code opens a file in this directory tree. Read the closest overlay first. -->

# apps/notulen/app/inputs/CLAUDE.md

Committed static SPA assets (frozen `inputs/` layer) for the notulen recorder. Served by `entrypoints/spa_routes.py` with `no-store` (the 2026-05-13 stale-cache defence). No build step — edit directly.

| File | Job |
|---|---|
| `dashboard.html` | SPA shell: markup + inline `<style>` (dark-theme CSS vars), Dutch (`lang="nl"`). The recorder page itself. |
| `dashboard.js` | Recorder SPA: MediaRecorder chunking, IndexedDB chunk queue (survives iOS tab eviction), chunked-upload session state, wake-lock + watchdog, job polling. Extracted from the inline `<script>` block 2026-06-12. |

## Gotchas

- `dashboard.js` writes chunks to IndexedDB *before* POSTing — the recovery banner drains anything left behind after a tab eviction. Don't break the write-before-POST order.
- No bundler: the file is shipped as-is, so it must run as plain browser JS (no imports/JSX).
