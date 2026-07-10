#!/usr/bin/env bash
# Hourly burn-and-health watch for the castle. Alert-first by design: the
# server on purpose has no power over the Scaleway account beyond reading
# the bill and the vault, so this script warns loudly instead of deleting
# things. Each check is defended: one failing check never blocks the rest,
# and the script exits 0 unless the watchdog itself is broken.
#
# Checks:
#   1. GPU node age    - a node on a scale-to-zero pool should live minutes;
#                        hours means the autoscaler is wedged (money burning).
#   2. Stuck jobs      - recordings stuck in a working state for over 2 hours
#                        are marked failed so the queue never clogs.
#   3. Disk            - root filesystem over 90 percent (auto-deploy dies
#                        silently on a full disk).
#   4. Monthly spend   - month-to-date bill past CASTLE_BUDGET_EUR (default
#                        30): warned at most once a day.
#
# Alerts go by email when the email module is configured (TEM_* in the env
# cache), and always to the system journal: journalctl -t castle-watchdog
set -u

ENV_CACHE="${ENV_CACHE:-/opt/castle/castle.env}"
CREDS_FILE="${CREDS_FILE:-/opt/castle/scw-secrets.env}"
STATE_DIR="${STATE_DIR:-/var/lib/castle}"
REPO="${REPO:-/opt/castle/repo}"

log()   { logger -t castle-watchdog "$*"; echo "[watchdog] $*"; }

getenvv() { grep "^$1=" "$ENV_CACHE" 2>/dev/null | head -1 | cut -d= -f2-; }

alert() {
    local subject="$1" body="$2"
    log "ALERT: $subject"
    local from proj
    from=$(getenvv TEM_FROM); proj=$(getenvv TEM_PROJECT_ID)
    if [ -n "$from" ] && [ -n "$proj" ] && [ -f "$CREDS_FILE" ]; then
        local owner_mail
        owner_mail=$(getenvv CASTLE_OWNER_EMAIL)
        [ -z "$owner_mail" ] && owner_mail="$from"
        # shellcheck disable=SC1090
        ( set -a; . "$CREDS_FILE"; set +a
          TEM_FROM="$from" TEM_PROJECT_ID="$proj" TEM_REGION="$(getenvv TEM_REGION)" \
          python3 "$REPO/infra/email/send_document.py" \
              --to "$owner_mail" --subject "Castle warning: $subject" \
              --body "$body" ) >/dev/null 2>&1 \
            || log "email alert failed; journal entry above is the record"
    fi
}

# ── 1. GPU node age ──────────────────────────────────────────────────────────
check_nodes() {
    local kdata; kdata=$(getenvv KUBECONFIG_DATA)
    [ -z "$kdata" ] && return 0
    command -v kubectl >/dev/null || { log "kubectl missing; node check skipped"; return 0; }
    local kc; kc=$(mktemp); printf '%s' "$kdata" | base64 -d > "$kc" 2>/dev/null || { rm -f "$kc"; return 0; }
    local now aged
    now=$(date -u +%s)
    aged=$(KUBECONFIG="$kc" kubectl get nodes -o json 2>/dev/null | python3 -c "
import json, sys, datetime
try:
    nodes = json.load(sys.stdin).get('items', [])
except Exception:
    sys.exit(0)
now = datetime.datetime.now(datetime.timezone.utc)
for n in nodes:
    ts = n['metadata']['creationTimestamp']
    created = datetime.datetime.fromisoformat(ts.replace('Z', '+00:00'))
    hours = (now - created).total_seconds() / 3600
    if hours > 3:
        print(f\"{n['metadata']['name']} {hours:.1f}h\")
")
    rm -f "$kc"
    if [ -n "$aged" ]; then
        alert "a graphics card machine is stuck" \
"A transcription machine has been running for hours: $aged. On a healthy castle it disappears minutes after a recording finishes; stuck means it is costing about 80 cents per hour for nothing. Open Claude and say: my GPU node is stuck, scale the pool to zero."
    fi
}

# ── 2. Stuck jobs ────────────────────────────────────────────────────────────
check_stuck_jobs() {
    local n
    n=$(cd "$REPO" 2>/dev/null && sudo docker compose --env-file "$ENV_CACHE" exec -T postgres \
        psql -U "$(getenvv POSTGRES_USER)" -d "$(getenvv POSTGRES_DB)" -t -A -c \
        "UPDATE notulen_jobs SET status='failed', error='Watchdog: stuck over 2 hours' \
         WHERE status IN ('pending','transcribing','structuring') \
         AND created_at < now() - interval '2 hours' RETURNING id" </dev/null 2>/dev/null | grep -c .)
    [ "${n:-0}" -gt 0 ] && log "marked $n stuck recording(s) as failed (over 2 hours old)"
    return 0
}

# ── 3. Disk ──────────────────────────────────────────────────────────────────
check_disk() {
    local pct; pct=$(df --output=pcent / 2>/dev/null | tail -1 | tr -dc '0-9')
    if [ "${pct:-0}" -ge 90 ]; then
        alert "the server disk is almost full (${pct}%)" \
"Above 90 percent full, updates stop deploying and recordings can fail. Open Claude and say: my server disk is almost full, clean it up."
    fi
}

# ── 4. Monthly spend ─────────────────────────────────────────────────────────
check_spend() {
    [ -f "$CREDS_FILE" ] || return 0
    local budget; budget=$(getenvv CASTLE_BUDGET_EUR); budget="${budget:-30}"
    local stamp="$STATE_DIR/spend-alerted-$(date -u +%Y-%m-%d)"
    [ -f "$stamp" ] && return 0
    local sk region total
    sk=$(grep '^SCW_SECRET_KEY=' "$CREDS_FILE" | cut -d= -f2-)
    region=$(grep '^SCW_DEFAULT_REGION=' "$CREDS_FILE" | cut -d= -f2-); region="${region:-fr-par}"
    [ -z "$sk" ] && return 0
    total=$(curl -s -m 20 -H "X-Auth-Token: $sk" \
        "https://api.scaleway.com/billing/v2beta1/consumptions?begin_date=$(date -u +%Y-%m-01)T00:00:00Z" \
        | python3 -c "
import json, sys
try:
    d = json.load(sys.stdin)
except Exception:
    sys.exit(0)
rows = d.get('consumptions', [])
total = 0.0
for r in rows:
    v = r.get('value') or {}
    units = float(v.get('units', 0)); nanos = float(v.get('nanos', 0)) / 1e9
    total += units + nanos
print(f'{total:.2f}')
" 2>/dev/null)
    [ -z "$total" ] && return 0
    if python3 -c "import sys; sys.exit(0 if float('$total') > float('$budget') else 1)" 2>/dev/null; then
        mkdir -p "$STATE_DIR" && touch "$stamp"
        alert "spending passed your ${budget} euro line" \
"Your castle spent ${total} euro this month, past your ${budget} euro line. Usually that is fine (a busy month of recordings), but if it surprises you, open Claude and ask: what is costing money this month?"
    fi
}

check_nodes   || log "node check errored"
check_stuck_jobs || log "stuck-job check errored"
check_disk    || log "disk check errored"
check_spend   || log "spend check errored"
exit 0
