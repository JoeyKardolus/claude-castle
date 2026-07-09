#!/usr/bin/env bash
# Mint the kubeconfig the notulen dashboard uses to submit GPU jobs.
#
# Why this exists: the kubeconfig `scw k8s kubeconfig get` returns
# authenticates through the scw command itself (an "exec plugin"). Inside
# the notulen container there is no scw, so every request would arrive
# anonymous and be refused. This script creates a service account that can
# do exactly one thing, manage transcription Jobs in the castle namespace,
# and prints a self-contained kubeconfig with a static token for it.
#
# Usage (admin kubeconfig from scw must be active):
#   KUBECONFIG=<admin-kubeconfig> infra/gpu/make-dashboard-kubeconfig.sh > dashboard-kubeconfig.yaml
#   base64 -w0 dashboard-kubeconfig.yaml   -> KUBECONFIG_DATA in /opt/castle/castle.env
#
# Idempotent: safe to run again; it reuses everything that already exists.
set -euo pipefail

NS="${CASTLE_K8S_NAMESPACE:-castle}"
SA=castle-dashboard

log() { printf '[dashboard-kubeconfig] %s\n' "$*" >&2; }

kubectl get namespace "$NS" >/dev/null 2>&1 || kubectl create namespace "$NS" >/dev/null
kubectl -n "$NS" get serviceaccount "$SA" >/dev/null 2>&1 \
    || kubectl -n "$NS" create serviceaccount "$SA" >/dev/null
kubectl -n "$NS" get role "$SA" >/dev/null 2>&1 \
    || kubectl -n "$NS" create role "$SA" --verb=create,get,list --resource=jobs.batch >/dev/null
kubectl -n "$NS" get rolebinding "$SA" >/dev/null 2>&1 \
    || kubectl -n "$NS" create rolebinding "$SA" --role="$SA" --serviceaccount="$NS:$SA" >/dev/null

# Long-lived token bound to the service account (a Secret of this type is
# auto-filled by Kubernetes with a token that survives restarts).
kubectl -n "$NS" get secret "$SA-token" >/dev/null 2>&1 || kubectl -n "$NS" apply -f - >/dev/null <<EOF
apiVersion: v1
kind: Secret
metadata:
  name: $SA-token
  annotations:
    kubernetes.io/service-account.name: $SA
type: kubernetes.io/service-account-token
EOF

# The token is filled in asynchronously; wait for it.
TOKEN=""
for _ in $(seq 1 20); do
    TOKEN=$(kubectl -n "$NS" get secret "$SA-token" -o jsonpath='{.data.token}' 2>/dev/null | base64 -d || true)
    [ -n "$TOKEN" ] && break
    sleep 2
done
[ -n "$TOKEN" ] || { log "token never appeared on secret $SA-token"; exit 1; }

SERVER=$(kubectl config view --minify -o jsonpath='{.clusters[0].cluster.server}')
CA=$(kubectl config view --minify --raw -o jsonpath='{.clusters[0].cluster.certificate-authority-data}')

log "service account $NS/$SA ready; kubeconfig on stdout"
cat <<EOF
apiVersion: v1
kind: Config
clusters:
- name: castle
  cluster:
    server: $SERVER
    certificate-authority-data: $CA
contexts:
- name: castle
  context: {cluster: castle, namespace: $NS, user: $SA}
current-context: castle
users:
- name: $SA
  user:
    token: $TOKEN
EOF
