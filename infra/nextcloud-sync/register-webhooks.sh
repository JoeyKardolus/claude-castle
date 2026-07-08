#!/usr/bin/env bash
# Register the Nextcloud webhook listeners that feed the nextcloud-sync
# service. Idempotent - safe to re-run; listeners that already exist are
# skipped.
#
# What it wires up: the webhook_listeners app (ships with Nextcloud 30+)
# fires an HTTP POST at http://nextcloud-sync:8000/nextcloud/file-event
# whenever a file is written, deleted, or renamed. The sync service then
# commits files under each user's "Sync" folder to the GitHub repo.
#
# Registration only exists on Nextcloud's OCS API (the app's ONLY occ
# command is webhook_listeners:list, there is no register command), so:
#   1. enable the webhook_listeners app,
#   2. allow Nextcloud to call the docker-internal service hostname
#      (allow_local_remote_servers; Nextcloud refuses private addresses
#      by default),
#   3. mint a temporary admin app password with occ (plain-password basic
#      auth stops working once 2FA is enforced; app passwords keep working),
#   4. POST the three listeners to the OCS API with curl from inside the
#      nextcloud container,
#   5. delete the temporary app password again.
#
# The bearer secret (NEXTCLOUD_WEBHOOK_SECRET) is baked into each listener:
# Nextcloud stores it encrypted and replays it verbatim as the
# Authorization header on every delivery; the sync service compares it in
# constant time.
#
# Usage (from /opt/castle/repo on the VM):
#   infra/nextcloud-sync/register-webhooks.sh
#
# Exit codes: 0 = all three listeners registered (or already were)
#             3 = aborted (missing config, occ failure, or a rejected POST)
set -u

REPO="${REPO:-/opt/castle/repo}"
ENV_FILE="${ENV_FILE:-/opt/castle/castle.env}"
COMPOSE_FILE="${COMPOSE_FILE:-$REPO/docker-compose.yml}"
SYNC_URL="${SYNC_URL:-http://nextcloud-sync:8000/nextcloud/file-event}"
OCS_PATH="/ocs/v2.php/apps/webhook_listeners/api/v1/webhooks"
TOKEN_NAME="castle-webhook-register"

EVENT_CLASSES=(
    'OCP\Files\Events\Node\NodeWrittenEvent'
    'OCP\Files\Events\Node\NodeDeletedEvent'
    'OCP\Files\Events\Node\NodeRenamedEvent'
)

log() { printf "[register-webhooks] %s\n" "$*"; }

compose() {
    docker compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" "$@"
}

# occ is Nextcloud's admin command-line tool; it lives inside the container
# and must run as the web-server user (www-data).
occ() {
    # </dev/null matters: exec -T reads stdin, and inside per-item while
    # loops that would swallow the remaining input, silently processing
    # only the first item.
    compose exec -T -u www-data nextcloud php occ "$@" </dev/null
}

# Read one variable's value from the env file (last assignment wins,
# optional surrounding quotes stripped).
env_var() {
    local line
    line="$(grep -E "^$1=" "$ENV_FILE" | tail -n 1)" || return 1
    line="${line#*=}"
    line="${line%\"}"; line="${line#\"}"
    line="${line%\'}"; line="${line#\'}"
    [ -n "$line" ] || return 1
    printf '%s' "$line"
}

secret="$(env_var NEXTCLOUD_WEBHOOK_SECRET)" \
    || { log "ABORT: NEXTCLOUD_WEBHOOK_SECRET not set in $ENV_FILE"; exit 3; }
admin_user="$(env_var NEXTCLOUD_ADMIN_USER)" \
    || { log "ABORT: NEXTCLOUD_ADMIN_USER not set in $ENV_FILE"; exit 3; }
admin_pw="$(env_var NEXTCLOUD_ADMIN_PASSWORD)" \
    || { log "ABORT: NEXTCLOUD_ADMIN_PASSWORD not set in $ENV_FILE"; exit 3; }
domain="$(env_var CASTLE_DOMAIN)" \
    || { log "ABORT: CASTLE_DOMAIN not set in $ENV_FILE"; exit 3; }

# Sanity: is the sync service up and resolvable from inside the stack?
# Not fatal - registration is still valid if the container comes up later;
# Nextcloud retries failed deliveries.
if compose exec -T nextcloud curl -fsS --max-time 5 \
        "http://nextcloud-sync:8000/healthz" >/dev/null 2>&1 </dev/null; then
    log "nextcloud-sync service reachable from the nextcloud container"
else
    log "WARNING: nextcloud-sync not reachable yet (is the container up?); registering anyway"
fi

# 1. The webhook_listeners app ships with Nextcloud but starts disabled.
occ app:enable webhook_listeners >/dev/null \
    || { log "ABORT: could not enable the webhook_listeners app"; exit 3; }

# 2. The sync service lives on the docker network ('nextcloud-sync' resolves
#    to a private address), and Nextcloud's HTTP client refuses private
#    addresses unless this flag is on.
occ config:system:set allow_local_remote_servers --value=true --type=boolean >/dev/null \
    || { log "ABORT: could not set allow_local_remote_servers"; exit 3; }

# 3. What is already registered? (uri + event pairs)
existing_json="$(occ webhook_listeners:list --output=json)" \
    || { log "ABORT: could not list existing webhook listeners"; exit 3; }

has_listener() {
    printf '%s' "$existing_json" | python3 -c '
import json, sys
uri, event = sys.argv[1], sys.argv[2]
rows = json.load(sys.stdin) or []
match = any(row.get("uri") == uri and row.get("event") == event for row in rows)
sys.exit(0 if match else 1)
' "$SYNC_URL" "$1"
}

missing=()
for cls in "${EVENT_CLASSES[@]}"; do
    if has_listener "$cls"; then
        log "  exists: $cls"
    else
        missing+=("$cls")
    fi
done

if [ "${#missing[@]}" -eq 0 ]; then
    log "all three listeners already registered - nothing to do"
    exit 0
fi

# 4. Mint a temporary admin app password (survives enforced 2FA, unlike
#    the plain admin password). Output is two lines: "app password:" then
#    the token itself.
app_pass="$(compose exec -T -e NC_PASS="$admin_pw" -u www-data nextcloud \
        php occ user:auth-tokens:add "$admin_user" --password-from-env --name "$TOKEN_NAME" </dev/null \
    | tail -n 1 | tr -d '[:space:]')"
if [ -z "$app_pass" ]; then
    log "ABORT: could not mint a temporary app password for $admin_user"
    exit 3
fi

# Always remove the temporary app password again, even on abort.
cleanup_token() {
    local ids
    ids="$(occ user:auth-tokens:list "$admin_user" --output=json 2>/dev/null \
        | python3 -c '
import json, sys
name = sys.argv[1]
rows = json.load(sys.stdin) or []
print("\n".join(str(row["id"]) for row in rows if row.get("name") == name))
' "$TOKEN_NAME" 2>/dev/null)" || return 0
    while IFS= read -r token_id; do
        [ -z "$token_id" ] && continue
        occ user:auth-tokens:delete "$admin_user" "$token_id" >/dev/null 2>&1 \
            || log "WARNING: could not delete temporary app password id $token_id"
    done <<< "$ids"
}
trap cleanup_token EXIT

# 5. Register each missing listener via the OCS API. curl runs inside the
#    nextcloud container against localhost, with the Host header spoofed to
#    the trusted domain (requests to a hostname outside trusted_domains are
#    rejected). authData is a header map: Nextcloud replays it verbatim on
#    every delivery.
payload_for() {
    # JSON needs the PHP namespace backslashes doubled.
    local cls_json="${1//\\/\\\\}"
    printf '{"httpMethod":"POST","uri":"%s","event":"%s","eventFilter":null,"userIdFilter":"","headers":null,"authMethod":"header","authData":{"Authorization":"Bearer %s"}}' \
        "$SYNC_URL" "$cls_json" "$secret"
}

failures=0
for cls in "${missing[@]}"; do
    payload="$(payload_for "$cls")"
    code="$(compose exec -T nextcloud curl -sS -o /dev/null -w '%{http_code}' \
        -u "$admin_user:$app_pass" \
        -H "Host: cloud.$domain" \
        -H "OCS-APIRequest: true" \
        -H "Content-Type: application/json" \
        -H "Accept: application/json" \
        -X POST --data "$payload" \
        "http://localhost$OCS_PATH" </dev/null)" || code="000"
    if [ "$code" = "200" ]; then
        log "  + $cls"
    else
        log "  FAILED ($code): $cls"
        failures=$((failures + 1))
    fi
done

if [ "$failures" -gt 0 ]; then
    log "ABORT: $failures listener registration(s) failed"
    exit 3
fi

# 6. Verify: all three (uri, event) pairs must now exist.
existing_json="$(occ webhook_listeners:list --output=json)" \
    || { log "ABORT: could not re-list webhook listeners"; exit 3; }
for cls in "${EVENT_CLASSES[@]}"; do
    has_listener "$cls" \
        || { log "ABORT: $cls not present after registration"; exit 3; }
done

log "all three listeners registered at $SYNC_URL"
log "deliveries run through Nextcloud background jobs (the cron container), so a sync can take a few minutes"
exit 0
