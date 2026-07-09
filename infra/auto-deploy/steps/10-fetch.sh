#!/bin/bash
# Step 10 — fetch origin/main and decide whether there is anything to do.
#
# Two change sources, checked every cycle:
#   1. The vault: pull-env.sh refreshes the env cache at /opt/castle/castle.env
#      from the castle-env secret (see infra/secrets/). A changed cache means
#      a new secret version was pushed and the stack must be redeployed, even
#      when no commit landed; that is what makes rotation zero-ssh.
#   2. Git: compares origin/main against the "last deployed" bookmark written
#      by step 40. Same SHA and no env change → nothing to do, exit quietly.
#      New SHA → fast-forward the local clone and note (for step 30) whether
#      the Caddyfile changed.
#
# FAILURE POLICY: fail loud (exit 1) when the repo is unreadable, the fetch
# fails, or the local branch has diverged from origin/main — a broken clone
# must show up as a red systemd unit, not silently mark the SHA as done.
# The vault pull is the opposite: pull-env.sh never fails the run; on any
# fetch problem it keeps the existing cache and exits 0 with a warning.
#
# Sourced by auto-deploy.sh; shares its shell. Not executable on its own.

mkdir -p "$STATE_DIR"
cd "$REPO" || { log "FATAL: cannot cd $REPO"; exit 1; }

# ── Vault: refresh the env cache ────────────────────────────────────────────
ENV_CHANGED=false
if [ -f /opt/castle/scw-secrets.env ] && [ -f "$REPO/infra/secrets/pull-env.sh" ]; then
    ENV_SUM_BEFORE=$(md5sum "$ENV_FILE" 2>/dev/null | cut -d' ' -f1)
    bash "$REPO/infra/secrets/pull-env.sh" >> "$LOG" 2>&1
    ENV_SUM_AFTER=$(md5sum "$ENV_FILE" 2>/dev/null | cut -d' ' -f1)
    if [ "$ENV_SUM_BEFORE" != "$ENV_SUM_AFTER" ]; then
        ENV_CHANGED=true
        log "env cache changed (new vault version); deploying"
    fi
fi

# ── Git: fetch and compare ──────────────────────────────────────────────────
if ! git fetch origin main >> "$LOG" 2>&1; then
    log "FATAL: git fetch origin main failed"
    exit 1
fi

NEW_SHA=$(git rev-parse FETCH_HEAD)
OLD_SHA=$(cat "$LAST_SHA_FILE" 2>/dev/null || echo "")

if [ "$OLD_SHA" = "$NEW_SHA" ] && [ "$ENV_CHANGED" = false ]; then
    log "no change since $NEW_SHA"
    exit 0
fi

# Move the working tree to origin/main. --ff-only means: refuse anything
# that is not a plain fast-forward. Nobody should ever commit on the VM;
# if someone did, this fails loudly instead of merging surprises.
if ! git merge --ff-only FETCH_HEAD >> "$LOG" 2>&1; then
    log "FATAL: local clone diverged from origin/main — fix by hand (git status in $REPO)"
    exit 1
fi

log "change detected: ${OLD_SHA:0:8} -> ${NEW_SHA:0:8}"

# What changed since the last successful deploy? On a cold start (no
# bookmark yet, or the bookmarked commit no longer exists) treat everything
# as changed so nothing is silently skipped.
if [ -n "$OLD_SHA" ] && git rev-parse -q --verify "$OLD_SHA" >/dev/null 2>&1; then
    CHANGED=$(git diff --name-only "$OLD_SHA" "$NEW_SHA")
else
    CHANGED=$(git ls-files)
    log "no usable prior SHA — treating all files as changed"
fi

CADDY_CHANGED=false
if echo "$CHANGED" | grep -q '^infra/caddy/Caddyfile$'; then
    CADDY_CHANGED=true
fi
log "caddyfile changed: $CADDY_CHANGED"
