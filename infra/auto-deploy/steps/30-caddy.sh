#!/bin/bash
# Step 30 — reload Caddy when its config changed.
#
# The compose file mounts the infra/caddy/ directory into the Caddy
# container, so after the git fast-forward in step 10 the new Caddyfile is
# already in place — Caddy just needs to be told to re-read it.
#
# VALIDATE BEFORE RELOAD: a reload of a broken Caddyfile would take down
# HTTPS for every domain at once. So we ask Caddy to check the file first
# and skip the reload if it does not parse — the live config stays as it
# was, and the failure is in the log.
#
# FAILURE POLICY: best-effort, never aborts the cycle. Worst case the old
# (working) Caddy config stays live until the file is fixed.
#
# Sourced by auto-deploy.sh; shares its shell. Not executable on its own.

if [ "$CADDY_CHANGED" = true ]; then
    if compose exec -T caddy caddy validate --config /etc/caddy/Caddyfile --adapter caddyfile >> "$LOG" 2>&1; then
        if compose exec -T caddy caddy reload --config /etc/caddy/Caddyfile >> "$LOG" 2>&1; then
            log "caddy reloaded with the new Caddyfile"
        else
            log "caddy reload failed (non-fatal; old config still live)"
        fi
    else
        log "caddy validate FAILED — reload skipped, live config unchanged. Fix infra/caddy/Caddyfile and push again."
    fi
fi
