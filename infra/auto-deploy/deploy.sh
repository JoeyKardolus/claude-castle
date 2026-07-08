#!/usr/bin/env bash
# Safe deploy: build + restart the containers, with automatic rollback for
# any service whose healthcheck fails on the new version.
#
# Usually called by auto-deploy.sh (step 20), but safe to run by hand:
#
#   /opt/castle/repo/infra/auto-deploy/deploy.sh
#
# What it does:
#   1. Snapshot the image each running service uses (the rollback target)
#   2. docker compose build (website + notulen, the two images built here)
#   3. docker compose up -d (whole stack)
#   4. Wait up to 180s for the built services to report "healthy"
#   5. Any service that is unhealthy → roll back JUST that service to its
#      previous image; healthy services stay on the new version
#
# FAILURE POLICY: build failure or any rolled-back service exits 1, so the
# caller (auto-deploy step 40) keeps its bookmark and retries next cycle.

set -euo pipefail

REPO="${REPO:-/opt/castle/repo}"
ENV_FILE="${ENV_FILE:-/opt/castle/castle.env}"
COMPOSE_FILE="${COMPOSE_FILE:-$REPO/docker-compose.yml}"
HEALTHCHECK_TIMEOUT=180  # seconds to wait for healthy
HEALTHCHECK_INTERVAL=5   # seconds between checks

# The services we build from this repo and health-check after deploy.
# caddy / postgres / nextcloud run stock images and keep their state in
# volumes — `up -d` handles them, no build or rollback needed.
BUILD_SERVICES=(website notulen)

log() { echo "[deploy] $(date +%H:%M:%S) $*"; }
err() { echo "[deploy] $(date +%H:%M:%S) ERROR: $*" >&2; }

compose() { docker compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" "$@"; }

cd "$REPO"

# ── Step 1: snapshot current image IDs (rollback targets) ──────────────────
declare -A OLD_IMAGES
for svc in "${BUILD_SERVICES[@]}"; do
    container=$(compose ps -q "$svc" 2>/dev/null || true)
    if [[ -n "$container" ]]; then
        OLD_IMAGES[$svc]=$(docker inspect --format='{{.Image}}' "$container" 2>/dev/null || true)
        log "snapshot $svc: ${OLD_IMAGES[$svc]:0:19}..."
    fi
done

# ── Step 2: build ───────────────────────────────────────────────────────────
log "building images..."
if ! compose build "${BUILD_SERVICES[@]}"; then
    err "docker compose build failed"
    exit 1
fi

# ── Step 3: start / restart ─────────────────────────────────────────────────
log "starting containers..."
compose up -d --remove-orphans
# --force-recreate for the built services: `up -d` occasionally keeps an old
# container running even though the image changed. A recreate is cheap for
# these stateless services and guarantees the new image is actually live.
compose up -d --force-recreate "${BUILD_SERVICES[@]}"

# ── Step 4: wait for the healthchecks ───────────────────────────────────────
# Both built services define a healthcheck in docker-compose.yml; docker
# runs it inside the container and reports starting/healthy/unhealthy.
health_of() {
    local cid
    cid=$(compose ps -q "$1" 2>/dev/null || true)
    [[ -n "$cid" ]] || { echo "missing"; return; }
    docker inspect --format='{{.State.Health.Status}}' "$cid" 2>/dev/null || echo "unknown"
}

log "waiting up to ${HEALTHCHECK_TIMEOUT}s for healthchecks..."
elapsed=0
while (( elapsed < HEALTHCHECK_TIMEOUT )); do
    sleep "$HEALTHCHECK_INTERVAL"
    elapsed=$((elapsed + HEALTHCHECK_INTERVAL))

    settled=true
    for svc in "${BUILD_SERVICES[@]}"; do
        case "$(health_of "$svc")" in
            healthy|unhealthy) ;;    # this one has made up its mind
            *) settled=false ;;      # still starting
        esac
    done
    $settled && break
    log "  ${elapsed}s: still waiting..."
done

# ── Step 5: check results + roll back what failed ──────────────────────────
FAILED_SERVICES=()
for svc in "${BUILD_SERVICES[@]}"; do
    health=$(health_of "$svc")
    if [[ "$health" == "healthy" ]]; then
        log "  OK $svc: healthy"
    else
        FAILED_SERVICES+=("$svc")
        err "  FAIL $svc: $health"
    fi
done

if (( ${#FAILED_SERVICES[@]} == 0 )); then
    log "deploy SUCCESS — all services healthy"
    exit 0
fi

log "rolling back ${#FAILED_SERVICES[@]} failed service(s)..."
for svc in "${FAILED_SERVICES[@]}"; do
    old_image="${OLD_IMAGES[$svc]:-}"
    if [[ -z "$old_image" ]]; then
        err "  no snapshot for $svc (first deploy?) — cannot roll back, leaving as-is"
        continue
    fi
    log "  rolling back $svc to ${old_image:0:19}..."
    compose stop "$svc" || true
    # Re-tag the old image under the name compose expects for this service,
    # then start it again WITHOUT rebuilding.
    image_name=$(compose config --images 2>/dev/null | grep -F "$svc" | head -1 || true)
    if [[ -n "$image_name" ]]; then
        docker tag "$old_image" "$image_name" || true
    fi
    compose up -d --no-build "$svc"
    sleep 15
    log "  $svc after rollback: $(health_of "$svc")"
done

err "deploy PARTIAL FAILURE — rolled back: ${FAILED_SERVICES[*]}"
exit 1
