# Watchdog: the burn-protection ladder

Money can only leak in a few known ways, and each rung below closes one. The watchdog is the last rung: an hourly check on the server that warns you when something outlived its purpose. It warns rather than kills, because the server on purpose has almost no power over your Scaleway account (it may read the bill and the vault, never change anything).

The ladder, top to bottom:

1. **Your bank card's own line**: Scaleway's optional budget alert email (console, Billing, Budget alerts).
2. **Every transcription job dies after 30 minutes**, never retries by itself, and cleans itself up 5 minutes after finishing.
3. **At most 50 jobs per day** (`MAX_DAILY_JOBS`).
4. **The GPU machine disappears by itself** about 10 minutes after the last job.
5. **Build machines self-destruct**: the temporary instance that builds the worker image is deleted even when the build fails.
6. **The hourly watchdog** (this folder, `castle-watchdog.timer`):
   - a GPU machine older than 3 hours means the scale-down is wedged: warning, with the exact sentence to say to Claude;
   - recordings stuck in a working state for over 2 hours are marked failed so the queue never clogs;
   - a root disk over 90 percent full: warning (deploys die silently on a full disk);
   - month-to-date spending past `CASTLE_BUDGET_EUR` (default 30): warning, at most once a day.

Warnings go to the system journal (`journalctl -t castle-watchdog`) always, and by email when the castle's email module is configured (`TEM_*` in the vault; `CASTLE_OWNER_EMAIL` decides the inbox).

Run it by hand any time: `/opt/castle/repo/infra/watchdog/watchdog.sh`.
