#!/bin/bash
# Step 00 — take the lock, define shared paths + helpers.
#
# The lock guarantees two deploy runs never overlap (the timer fires every
# 2 minutes; a slow build can take longer than that). We use flock(1) on a
# file descriptor: the kernel releases it automatically when the process
# exits FOR ANY REASON — crash, kill, reboot — so a stale lock can never
# wedge deploys.
#
# FAILURE POLICY: if another run holds the lock we log and exit 0 — the
# timer fires again in 2 minutes and picks the work up then.
#
# Sourced by auto-deploy.sh; shares its shell. Not executable on its own.

REPO="/opt/castle/repo"
ENV_FILE="/opt/castle/castle.env"
COMPOSE_FILE="$REPO/docker-compose.yml"
LOCK="/tmp/castle-deploy.lock"
LOG="/tmp/castle-deploy.log"
STATE_DIR="/var/lib/castle"
LAST_SHA_FILE="$STATE_DIR/last-deployed-sha"
LAST_FAIL_FILE="$STATE_DIR/last-failed-sha"

log() { echo "[$(date -Iseconds)] $*" | tee -a "$LOG"; }

# One place to spell out how we call docker compose: always with the env
# file from /opt/castle (secrets live there, never in git) and always with
# the repo's compose file.
compose() { docker compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" "$@"; }

# ── The lock itself ─────────────────────────────────────────────────────────
exec 9>"$LOCK"
if ! flock -n 9; then
    log "previous deploy run still active; skipping this cycle"
    exit 0
fi
# fd 9 stays open for the script's lifetime; the kernel releases it on exit.
