#!/usr/bin/env bash
# push-env.sh: push the castle's full environment to the vault (laptop side).
#
# The vault is one Scaleway Secret Manager secret named "castle-env" whose
# content is the complete KEY=value environment the compose stack needs.
# Every change is a NEW VERSION of that one secret. The VM pulls the latest
# version into its cache at /opt/castle/castle.env (see pull-env.sh); the
# auto-deploy loop runs that pull every cycle, so a pushed version is live
# within one deploy cycle, no ssh needed.
#
# Usage:
#   infra/secrets/push-env.sh <file-with-the-full-env-content>
#
# Uses the scw CLI already configured on this laptop. Creates the secret on
# first use. NEVER prints the content.

set -euo pipefail

SECRET_NAME="castle-env"

if [[ $# -ne 1 ]]; then
    echo "usage: $0 <env-file>" >&2
    exit 2
fi
ENV_CONTENT_FILE="$1"

if [[ ! -s "$ENV_CONTENT_FILE" ]]; then
    echo "refusing to push: $ENV_CONTENT_FILE is missing or empty" >&2
    exit 2
fi

# A basic shape check so a wrong file (a log, a PDF) never becomes the env.
if ! grep -q '^CASTLE_DOMAIN=' "$ENV_CONTENT_FILE"; then
    echo "refusing to push: $ENV_CONTENT_FILE has no CASTLE_DOMAIN= line, so it does not look like the castle env" >&2
    exit 2
fi

# json_field <field>: read one string field from the JSON on stdin.
json_field() {
    python3 -c '
import json, sys
data = json.load(sys.stdin)
if isinstance(data, list):
    data = data[0] if data else {}
print(data.get(sys.argv[1], ""))
' "$1"
}

# Find the secret; create it on first use.
SECRET_ID=$(scw secret secret list name="$SECRET_NAME" -o json | json_field id)
if [[ -z "$SECRET_ID" ]]; then
    echo "vault secret $SECRET_NAME does not exist yet; creating it"
    SECRET_ID=$(scw secret secret create name="$SECRET_NAME" -o json | json_field id)
fi
if [[ -z "$SECRET_ID" ]]; then
    echo "could not find or create the vault secret $SECRET_NAME" >&2
    exit 1
fi

# Push the content as a new version. data=@file makes the CLI read the file;
# the content never appears on the command line or in this script's output.
REVISION=$(scw secret version create "$SECRET_ID" data=@"$ENV_CONTENT_FILE" -o json | json_field revision)
if [[ -z "$REVISION" ]]; then
    echo "pushing the new version failed" >&2
    exit 1
fi

echo "pushed vault version $REVISION of $SECRET_NAME ($SECRET_ID)"
echo "it goes live on the VM at the next auto-deploy cycle, or immediately via: ssh castle@<SERVER_IP> /opt/castle/repo/infra/secrets/pull-env.sh"
