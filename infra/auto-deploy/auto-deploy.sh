#!/bin/bash
# Auto-deploy — the castle's whole CI/CD, in one small script.
#
# A systemd timer (infra/systemd/auto-deploy.timer) runs this every 2 minutes
# on the VM. It checks whether origin/main moved; if it did, it pulls the new
# code, rebuilds + restarts the containers (with rollback if one comes up
# broken), reloads Caddy when its config changed, and records the outcome.
# Pushing to main IS the deploy button.
#
# This file owns ONLY the step ordering. Each slice of behaviour lives in a
# step file under steps/, sourced below IN ORDER into this one shell process,
# so all steps share variables, helper functions, and the lock.
#
#   00-lock.sh     take the lock (so two runs never overlap) + shared helpers
#   10-fetch.sh    git fetch + diff origin/main; exit early if nothing changed
#   20-deploy.sh   docker compose build + up, healthcheck, rollback (deploy.sh)
#   30-caddy.sh    reload Caddy if infra/caddy/Caddyfile changed
#   40-outcome.sh  record success/failure so the next run knows where it stands
#
# FAILURE POLICY: a failed deploy does NOT advance the "last deployed"
# bookmark — the next cycle simply retries. A broken Caddyfile is validated
# first and never reloaded, so it can't take the live sites down.

set -u

# systemd does not read ~/.bashrc, so make sure the usual tool locations are
# on PATH regardless of how this script is started.
export PATH="$HOME/.local/bin:/usr/local/bin:/usr/bin:/bin:$PATH"

# Find the steps/ directory relative to this file, so the script works from
# the VM clone and a dev checkout alike.
AUTO_DEPLOY_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Explicit list, not a glob: a missing step must be a loud error, never a
# silent skip.
# shellcheck disable=SC1091
. "$AUTO_DEPLOY_DIR/steps/00-lock.sh"
. "$AUTO_DEPLOY_DIR/steps/10-fetch.sh"
. "$AUTO_DEPLOY_DIR/steps/20-deploy.sh"
. "$AUTO_DEPLOY_DIR/steps/30-caddy.sh"
. "$AUTO_DEPLOY_DIR/steps/40-outcome.sh"
