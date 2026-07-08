#!/usr/bin/env bash
# One-time setup: install the systemd units on the VM and start the timers.
#
# Run as root, once, after cloning the repo to /opt/castle/repo:
#
#   sudo /opt/castle/repo/infra/systemd/install.sh
#
# Idempotent — safe to run again after adding or changing a unit file
# (auto-deploy also re-copies nothing; units are read from /etc/systemd,
# so re-run this script whenever a file in infra/systemd/ changes).

set -euo pipefail

if [[ "$(id -u)" -ne 0 ]]; then
    echo "run me as root: sudo $0" >&2
    exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# The deploy scripts run as the 'castle' user and need docker.
if ! id -nG castle 2>/dev/null | grep -qw docker; then
    echo "WARNING: user 'castle' is missing or not in the docker group." >&2
    echo "  fix:  sudo usermod -aG docker castle" >&2
fi

# State directory for the deploy bookmark (last deployed / last failed SHA).
mkdir -p /var/lib/castle
chown castle:castle /var/lib/castle

echo "installing units:"
for unit in "$SCRIPT_DIR"/*.service "$SCRIPT_DIR"/*.timer; do
    echo "  $(basename "$unit")"
    cp "$unit" /etc/systemd/system/
done

systemctl daemon-reload

for timer in "$SCRIPT_DIR"/*.timer; do
    systemctl enable --now "$(basename "$timer")"
done

echo "done. check with: systemctl list-timers | grep -E 'auto-deploy|purge'"
