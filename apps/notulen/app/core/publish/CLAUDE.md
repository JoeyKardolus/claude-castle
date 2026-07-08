<!-- Per-area overlay. Read ../../../../CLAUDE.md (notulen) first. -->

# notulen/app/core/publish/CLAUDE.md

ADR-0020 commit pipeline: retry loop that commits `committing` jobs to GitHub and flips them to `complete`. Runs as a daemon thread started at app startup.

## File map

### `retry/` — commit retry loop and stuck detection

| File | Job |
|---|---|
| `retry/git_writer_loop.py` | Daemon loop: polls `committing` rows, calls `finalize_commit`; no time window (idempotent + cheap); pages ops for stuck jobs |
| `retry/finalize_commit.py` | ADR-0020 invariant: commits via `github_writer` then marks `complete` — `complete` is never set without a commit URL |
| `retry/stuck_commits.py` | Detects rows stuck in `committing` past a threshold (pure — no DB/clock, caller passes `now=`) |
| `retry/alert_stuck_committing.py` | Ops page for stuck rows; in-process hourly throttle; Tier-2 swallow (alert failure must not break the commit loop) |
| `retry/tests/test_commit_gating.py` | Pins: `finalize_commit` converts commit failure to `None` (job stays `committing`); `complete` never set on failure |
| `retry/tests/test_stuck_alert_throttle.py` | Pins the in-process hourly throttle |

### `github/` — GitHub write-path

| File | Job |
|---|---|
| `github/github_writer.py` | Commits notulen markdown to the repo in `NOTULEN_GITHUB_REPO` via the GitHub Contents API (unset = publishing skipped, job still completes) |
| `github/target_path.py` | Repo-relative path grammar: `<NOTULEN_TARGET_DIR>/<YYYY-MM>_<slug>.md` (default dir `minutes/`) |
| `github/tests/test_github_writer.py` | Unit tests for the GitHub Contents API call |
| `github/tests/test_github_writer_integration.py` | Integration test (requires live PAT) |

## Gotchas

- The select in `git_writer_loop.py` has **no time window** — a job is retriable until it lands, regardless of age (old 24h cutoff caused the #364 silent data loss).
- `finalize_commit.py` failure policy is split: commit failure → Tier-2 swallow returning `None` (retry); `complete` write → Tier-1 propagates.
- `github_writer.py` is idempotent: same content at same path is a no-op (safe to retry).
- `target_path.py` path grammar is **frozen** since 2026 — changing it is a content migration (historic notulen would need re-keying).
- `alert_stuck_committing.py` was split from `stuck_commits.py` on 2026-06-12 to satisfy one-function-one-purpose (ADR-0011).
