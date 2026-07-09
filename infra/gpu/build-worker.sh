#!/usr/bin/env bash
# Build and push the notulen GPU worker image from a temporary Scaleway
# instance in your region.
#
# Why a temporary instance: the image is big (PyTorch plus CUDA base,
# more than 10 GB). Building it on a laptop or pushing it over home
# internet fails often. A small cloud instance in the same region as the
# registry builds and pushes it in minutes, then gets deleted. Total
# cost: a few cents.
#
# Usage:
#   infra/gpu/build-worker.sh [tag]     # tag defaults to v1
#
# Environment:
#   HF_TOKEN         optional Hugging Face token; bakes the gated speaker
#                    label models into the image (see the Dockerfile header
#                    at infra/docker/notulen-worker/Dockerfile)
#   FORCE_REBUILD=1  rebuild even when the tag already exists in the registry
#   BUILDER_TYPE     instance type for the build box (default PRO2-M)
#
# Prereqs: scw configured (access key, secret key, default region and zone)
# and an ssh key at ~/.ssh/id_ed25519 registered with Scaleway.
#
# The EXIT trap always deletes the build instance, even on failure.
# The last line of output on success is the pushed image reference.
set -euo pipefail

TAG="${1:-v1}"
BUILDER_TYPE="${BUILDER_TYPE:-PRO2-M}"

REGION=$(scw config get default-region)
ZONE=$(scw config get default-zone)
if [ -z "$REGION" ] || [ -z "$ZONE" ]; then
    echo "ERROR: scw has no default region or zone; run scw config set default-region=... default-zone=..." >&2
    exit 1
fi

REGISTRY="rg.${REGION}.scw.cloud"
IMAGE_REF="${REGISTRY}/castle/notulen-worker:${TAG}"

REPO_ROOT=$(cd "$(dirname "$0")/../.." && pwd)
cd "$REPO_ROOT"

echo "==> Target image: $IMAGE_REF"

# --- Registry namespace, created once, reused after -------------------------
if scw registry namespace list region="$REGION" -o json \
        | python3 -c 'import sys,json; ns=json.load(sys.stdin) or []; sys.exit(0 if any(n.get("name")=="castle" for n in ns) else 1)'; then
    echo "==> Registry namespace castle already exists."
else
    echo "==> Creating registry namespace castle in ${REGION}..."
    scw registry namespace create name=castle region="$REGION" is-public=false >/dev/null
fi

# --- Skip the whole build when the tag is already in the registry ------------
tag_exists() {
    local image_id
    image_id=$(scw registry image list name=notulen-worker region="$REGION" -o json \
        | python3 -c 'import sys,json; imgs=[i for i in (json.load(sys.stdin) or []) if i.get("name")=="notulen-worker"]; print(imgs[0]["id"] if imgs else "")')
    [ -n "$image_id" ] || return 1
    scw registry tag list image-id="$image_id" region="$REGION" -o json \
        | python3 -c 'import sys,json; tags=json.load(sys.stdin) or []; sys.exit(0 if any(t.get("name")==sys.argv[1] for t in tags) else 1)' "$TAG"
}

if [ "${FORCE_REBUILD:-0}" != "1" ] && tag_exists; then
    echo "==> Tag ${TAG} is already in the registry; nothing to build (set FORCE_REBUILD=1 to rebuild)."
    echo "$IMAGE_REF"
    exit 0
fi

# --- Bundle the repo (the build context) --------------------------------------
echo "==> Bundling the repo source..."
BUNDLE=$(mktemp -t castle-src-XXXXXX.tgz)
tar czf "$BUNDLE" \
    --exclude='.git' --exclude='*/.git' \
    --exclude='.venv' --exclude='*/.venv' \
    --exclude='node_modules' --exclude='*/node_modules' \
    --exclude='__pycache__' --exclude='*/__pycache__' \
    --exclude='*.pyc' \
    .
echo "    bundle: $(du -h "$BUNDLE" | awk '{print $1}')"

# --- Temporary build instance -------------------------------------------------
echo "==> Creating temporary build instance (${BUILDER_TYPE}, 100 GB, ${ZONE})..."
INSTANCE_ID=$(scw instance server create \
    name="castle-builder-$(date +%s)" \
    type="$BUILDER_TYPE" \
    zone="$ZONE" \
    image=ubuntu_noble \
    root-volume=block:100G \
    ip=new \
    -o json | python3 -c 'import sys,json; print(json.load(sys.stdin)["id"])')
echo "    instance: $INSTANCE_ID"

# Always delete the instance, even when a later step fails. A forgotten
# build box would otherwise keep billing.
cleanup() {
    echo "==> Deleting build instance ${INSTANCE_ID}..."
    scw instance server terminate "$INSTANCE_ID" zone="$ZONE" with-ip=true with-block=true >/dev/null || \
        echo "WARNING: could not delete instance ${INSTANCE_ID}; delete it by hand in the Scaleway console." >&2
    rm -f "$BUNDLE"
}
trap cleanup EXIT

echo "==> Waiting for the instance's public IP..."
IP=""
for _attempt in $(seq 1 30); do
    IP=$(scw instance server get "$INSTANCE_ID" zone="$ZONE" -o json 2>/dev/null \
        | python3 -c '
import sys, json
data = json.load(sys.stdin)
ip = (data.get("public_ip") or {}).get("address")
if not ip:
    ips = data.get("public_ips") or []
    if ips:
        ip = ips[0].get("address", "")
print(ip or "")
' 2>/dev/null)
    [ -n "$IP" ] && break
    sleep 5
done
if [ -z "$IP" ]; then
    echo "ERROR: timed out waiting for the instance's public IP" >&2
    exit 1
fi
echo "    IP: $IP"

echo "==> Waiting for ssh..."
SSH_OPTS=(-o StrictHostKeyChecking=accept-new -o ConnectTimeout=5 -o BatchMode=yes)
SSH_OK=0
for _attempt in $(seq 1 40); do
    if ssh "${SSH_OPTS[@]}" "root@$IP" true 2>/dev/null; then
        SSH_OK=1
        break
    fi
    sleep 5
done
if [ "$SSH_OK" != "1" ]; then
    echo "ERROR: timed out waiting for ssh on $IP" >&2
    exit 1
fi

echo "==> Installing Docker on the build instance..."
ssh "${SSH_OPTS[@]}" "root@$IP" \
    "command -v docker >/dev/null 2>&1 || curl -fsSL https://get.docker.com | sh >/dev/null 2>&1; docker --version"

echo "==> Uploading the source bundle..."
scp "${SSH_OPTS[@]}" "$BUNDLE" "root@$IP:/root/castle-src.tgz"
ssh "${SSH_OPTS[@]}" "root@$IP" "mkdir -p /root/build && tar xzf /root/castle-src.tgz -C /root/build"

echo "==> Logging in to the registry (intra-region push)..."
scw config get secret-key \
    | ssh "${SSH_OPTS[@]}" "root@$IP" "docker login '$REGISTRY' -u nologin --password-stdin"

SECRET_ARGS=""
if [ -n "${HF_TOKEN:-}" ]; then
    echo "==> Hugging Face token found; speaker label models will be baked in."
    printf '%s' "$HF_TOKEN" \
        | ssh "${SSH_OPTS[@]}" "root@$IP" "cat > /root/hf-token && chmod 600 /root/hf-token"
    SECRET_ARGS="--secret id=HF_TOKEN,src=/root/hf-token"
else
    echo "==> No HF_TOKEN set; the image will transcribe without speaker labels (add them later, see infra/gpu/README.md)."
fi

echo "==> Building the image on the instance (this is the long part, expect 15 to 30 minutes)..."
ssh "${SSH_OPTS[@]}" "root@$IP" \
    "cd /root/build && DOCKER_BUILDKIT=1 docker build -f infra/docker/notulen-worker/Dockerfile $SECRET_ARGS -t '$IMAGE_REF' . 2>&1 | tail -5"

echo "==> Pushing to the registry..."
ssh "${SSH_OPTS[@]}" "root@$IP" "docker push '$IMAGE_REF' 2>&1 | tail -3"

# Clean up now instead of at exit, so the pushed reference is the last line.
trap - EXIT
cleanup

echo "==> Done."
echo "$IMAGE_REF"
