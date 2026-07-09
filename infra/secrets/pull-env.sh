#!/usr/bin/env bash
# pull-env.sh: refresh the VM's env cache from the vault (VM side).
#
# Reads the scoped credentials in /opt/castle/scw-secrets.env, fetches the
# latest version of the castle-env vault secret over the Secret Manager
# HTTPS API, and atomically rewrites the cache at /opt/castle/castle.env
# (mode 600), which is the file docker compose reads via --env-file.
#
# RESILIENCE POLICY: the cache is the fallback. On ANY failure (missing
# credentials, network down, API error, garbage payload) this script keeps
# the existing /opt/castle/castle.env untouched and exits 0 with a warning,
# so a Secret Manager blip can never take the stack down.

set -u
umask 177

CREDS_FILE="${CREDS_FILE:-/opt/castle/scw-secrets.env}"
CACHE_FILE="${CACHE_FILE:-/opt/castle/castle.env}"
API_BASE="https://api.scaleway.com/secret-manager/v1beta1"

warn() { echo "[pull-env] WARNING: $*, keeping the existing cache" >&2; }

if [ ! -f "$CREDS_FILE" ]; then
    warn "$CREDS_FILE missing (vault not set up on this VM yet)"
    exit 0
fi

# shellcheck disable=SC1090
. "$CREDS_FILE"

if [ -z "${SCW_SECRET_KEY:-}" ] || [ -z "${SCW_DEFAULT_REGION:-}" ] || [ -z "${CASTLE_ENV_SECRET_ID:-}" ]; then
    warn "SCW_SECRET_KEY, SCW_DEFAULT_REGION or CASTLE_ENV_SECRET_ID not set in $CREDS_FILE"
    exit 0
fi

URL="$API_BASE/regions/$SCW_DEFAULT_REGION/secrets/$CASTLE_ENV_SECRET_ID/versions/latest/access"

fetch() {
    curl -sf --max-time 20 -H "X-Auth-Token: $SCW_SECRET_KEY" "$URL"
}

# One retry with a pause: freshly created IAM keys take a few seconds to
# propagate, and transient API blips happen.
if ! RESPONSE=$(fetch); then
    sleep 5
    if ! RESPONSE=$(fetch); then
        warn "vault fetch failed twice ($URL)"
        exit 0
    fi
fi

# The response is JSON with the payload base64-encoded in the "data" field.
# Base64 uses no quote characters, so this extraction is safe without jq.
DATA_B64=$(printf '%s' "$RESPONSE" | grep -o '"data":"[^"]*"' | head -1 | cut -d'"' -f4)
if [ -z "$DATA_B64" ]; then
    warn "vault response had no data field"
    exit 0
fi

if ! NEW_CONTENT=$(printf '%s' "$DATA_B64" | base64 -d 2>/dev/null); then
    warn "could not decode the vault payload"
    exit 0
fi

case "$NEW_CONTENT" in
    *CASTLE_DOMAIN=*) ;;
    *)
        warn "vault payload does not look like the castle env (no CASTLE_DOMAIN= line)"
        exit 0
        ;;
esac

# Atomic replace: write a private temp file next to the target, then rename
# over it, so readers only ever see the old file or the complete new one.
if ! TMP_FILE=$(mktemp "$CACHE_FILE.XXXXXX"); then
    warn "mktemp failed"
    exit 0
fi
if ! printf '%s\n' "$NEW_CONTENT" > "$TMP_FILE"; then
    warn "writing the new cache failed"
    rm -f "$TMP_FILE"
    exit 0
fi
chmod 600 "$TMP_FILE"
if ! mv "$TMP_FILE" "$CACHE_FILE"; then
    warn "replacing $CACHE_FILE failed"
    rm -f "$TMP_FILE"
    exit 0
fi

echo "[pull-env] $CACHE_FILE refreshed from the latest vault version"
