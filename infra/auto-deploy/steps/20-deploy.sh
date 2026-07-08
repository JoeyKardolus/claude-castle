#!/bin/bash
# Step 20 — rebuild + restart the containers, via deploy.sh.
#
# deploy.sh does the real work: docker compose build, up, wait for the
# healthchecks, and roll a service back to its previous image if it comes up
# broken. It is a separate script (not inlined here) so you can also run it
# by hand on the VM:
#
#   /opt/castle/repo/infra/auto-deploy/deploy.sh
#
# FAILURE POLICY: a deploy failure is recorded in DEPLOY_OK and handled by
# step 40 (the bookmark does not advance, so the next cycle retries). It
# does not abort the remaining steps — a Caddy config fix should still be
# reloaded even if an app build failed.
#
# Sourced by auto-deploy.sh; shares its shell. Not executable on its own.

DEPLOY_OK=true
if "$AUTO_DEPLOY_DIR/deploy.sh" >> "$LOG" 2>&1; then
    log "deploy.sh succeeded"
else
    DEPLOY_OK=false
    log "deploy.sh FAILED (details above in $LOG)"
fi
