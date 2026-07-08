#!/usr/bin/env bash
# Enforce two-factor authentication for every Nextcloud user. Idempotent —
# safe to run as often as you like; it does nothing once enforcement is on.
#
# Nextcloud is the one service in the castle with its own login screen, so
# it gets its own second factor (TOTP: the 6-digit codes from an authenticator
# app on your phone).
#
# FAIL-CLOSED by design: before flipping enforcement ON, every existing user
# must already have a second factor enrolled. If ANY user has none — or the
# output cannot be positively parsed — this script ABORTS instead of locking
# someone out. Run `--check` first to see who still needs to enrol.
#
# Usage (from /opt/castle/repo on the VM):
#   infra/nextcloud/nextcloud-2fa-enforce.sh --check   # dry-run: who is enrolled?
#   infra/nextcloud/nextcloud-2fa-enforce.sh           # enforce (aborts if unsafe)
#
# Exit codes: 0 = enforced / already enforced / --check done
#             3 = aborted (someone would be locked out, or occ failed)
set -u

REPO="${REPO:-/opt/castle/repo}"
ENV_FILE="${ENV_FILE:-/opt/castle/castle.env}"
COMPOSE_FILE="${COMPOSE_FILE:-$REPO/docker-compose.yml}"
MODE="${1:-enforce}"

log() { printf "[2fa-enforce] %s\n" "$*"; }

# occ is Nextcloud's admin command-line tool; it lives inside the container
# and must run as the web-server user (www-data).
occ() {
    docker compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" \
        exec -T -u www-data nextcloud php occ "$@"
}

# Print user ids, one per line; non-zero (fail closed) if the list can't be
# fetched or parsed.
list_uids() {
    local users_json
    users_json="$(occ user:list --output=json 2>/dev/null)" || return 1
    printf '%s' "$users_json" \
        | python3 -c 'import json,sys; print("\n".join(json.load(sys.stdin).keys()))'
}

# True only on the positive "is enabled for user" line. The negative reads
# "is not enabled", so anything ambiguous counts as NOT enrolled — a parse
# mismatch aborts rather than locks someone out.
is_enrolled() {
    occ twofactorauth:state "$1" 2>/dev/null | grep -qi "is enabled for user"
}

# Make sure the TOTP provider app is on — without it nobody CAN enrol a
# second factor. Idempotent (a no-op if already enabled).
occ app:enable twofactor_totp >/dev/null 2>&1 \
    || log "note: could not enable twofactor_totp (is the nextcloud container running?)"

# ── Dry-run: print each user's state, change nothing ────────────────────────
if [ "$MODE" = "--check" ]; then
    uids="$(list_uids)" || { log "ABORT: could not list users"; exit 3; }
    blockers=""
    while IFS= read -r uid; do
        [ -z "$uid" ] && continue
        if is_enrolled "$uid"; then
            log "  enrolled : $uid"
        else
            log "  NO 2FA   : $uid"
            blockers="${blockers}${uid} "
        fi
    done <<< "$uids"
    if [ -n "$blockers" ]; then
        log "WOULD ABORT — these users have no active 2FA yet: $blockers"
    else
        log "OK — all users enrolled; enforce would succeed."
    fi
    exit 0
fi

# ── Enforce ──────────────────────────────────────────────────────────────────
# Already on? Then there is nothing to do. (Once enforced, Nextcloud itself
# forces new users into 2FA setup at their first login.)
if occ twofactorauth:enforce 2>/dev/null | grep -qi "enforced for all users"; then
    log "already enforced — nothing to do"
    exit 0
fi

uids="$(list_uids)" || {
    log "ABORT: could not list/parse Nextcloud users; enforcement NOT applied"
    exit 3
}

unenrolled=""
while IFS= read -r uid; do
    [ -z "$uid" ] && continue
    is_enrolled "$uid" || unenrolled="${unenrolled}${uid} "
done <<< "$uids"

if [ -n "$unenrolled" ]; then
    log "ABORT: these users have no second factor and would be locked out: $unenrolled"
    log "Have them log in, go to Settings > Security, and set up TOTP. Then re-run."
    exit 3
fi

if occ twofactorauth:enforce --on; then
    log "2FA is now enforced for all users"
    exit 0
else
    log "ABORT: occ twofactorauth:enforce --on failed"
    exit 3
fi
