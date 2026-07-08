#!/bin/bash
# Step 40 — record the outcome.
#
# On success the new SHA is written to the "last deployed" bookmark, so the
# next cycle sees "no change" and does nothing. On failure the bookmark
# STAYS at the previous good SHA: the next cycle diffs from there and
# retries the whole deploy. The failed SHA is noted separately so you can
# see what broke.
#
# FAILURE POLICY: exits 1 on a failed deploy so the systemd unit goes red —
# `systemctl status auto-deploy.service` (or journalctl) shows it.
#
# Sourced by auto-deploy.sh; shares its shell. Not executable on its own.

if [ "$DEPLOY_OK" = true ]; then
    echo "$NEW_SHA" > "$LAST_SHA_FILE"
    log "deploy complete at $NEW_SHA"
else
    echo "$NEW_SHA" > "$LAST_FAIL_FILE"
    log "deploy FAILED at $NEW_SHA — bookmark stays at ${OLD_SHA:-none}; next cycle retries"
    exit 1
fi
