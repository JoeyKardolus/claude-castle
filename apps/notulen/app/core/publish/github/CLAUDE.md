<!-- Per-area overlay. Loaded automatically when Claude Code opens a file in this directory tree. Read the closest overlay first. -->

# apps/notulen/app/core/publish/github/CLAUDE.md

The GitHub write-path: commits notulen markdown to the repo configured in `NOTULEN_GITHUB_REPO` (`owner/name`) via the GitHub Contents API. Unset = publishing is skipped and jobs complete with a sentinel URL. Read [`core/publish/CLAUDE.md`](../CLAUDE.md) first.

| File | Job |
|---|---|
| `github_writer.py` | Commits notulen markdown to `NOTULEN_GITHUB_REPO` via the GitHub Contents API. Idempotent: same content at same path is a no-op (safe to retry). |
| `target_path.py` | Repo-relative path grammar `<NOTULEN_TARGET_DIR>/<YYYY-MM>_<slug>.md` (default dir `minutes/`; month = first 7 chars of meeting date). Delegates to `shared/slug.py` (the one slug home). |
| `tests/test_github_writer.py` | Unit tests for the Contents API call. |
| `tests/test_github_writer_integration.py` | Integration test (requires a live PAT). |

## Gotchas

- The path grammar is **frozen since 2026** — changing it is a content migration (historic notulen would need re-keying).
- The slug lives in `shared/slug.py`, not here — `target_path.py` used to carry a private copy that had drifted.
