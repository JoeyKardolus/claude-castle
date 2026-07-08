<!-- Per-area overlay. Loaded automatically when Claude Code opens a file in this directory tree. Read the closest overlay first. -->

# apps/notulen/app/core/publish/retry/CLAUDE.md

The ADR-0020 commit retry loop: a daemon thread that polls `committing` jobs, commits them to GitHub, and flips them to `complete`. Read [`core/publish/CLAUDE.md`](../CLAUDE.md) first.

| File | Job |
|---|---|
| `git_writer_loop.py` | Daemon loop: polls `committing` rows, calls `finalize_commit`; pages ops for stuck jobs. **No time window** — a job is retriable until it lands (the old 24h cutoff caused #364 silent data loss). |
| `finalize_commit.py` | ADR-0020 invariant: commit via `github_writer`, then mark `complete` — `complete` is never set without a commit URL. |
| `stuck_commits.py` | Pure stuck-detection: rows stuck in `committing` past a threshold. No DB/clock — caller passes `now=`. |
| `alert_stuck_committing.py` | Throttled (hourly, in-process) ops page for stuck rows. Tier-2 swallow: alert failure must not break the commit loop. Split from `stuck_commits.py` 2026-06-12 (ADR-0011). |
| `tests/test_commit_gating.py` | Pins: commit failure → `None` (job stays `committing`); `complete` never set on failure. |
| `tests/test_stuck_alert_throttle.py` | Pins the in-process hourly alert throttle. |

## Gotchas

- `finalize_commit.py` failure policy is split: commit failure → Tier-2 swallow returning `None` (retry); `complete` write → Tier-1 propagates.
