#!/usr/bin/env bash
# Fresh-machine setup for this repo. Run once from the repo root after cloning:
#   bash .claude/bootstrap.sh
# Safe to re-run. It only links Claude's memory folder into this repo and
# prints the manual steps it cannot do for you.
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
REPO_MEM="$REPO/.claude/memory"

# --- 1. Link Claude's memory folder into the repo -------------------------
# Claude Code stores memory at ~/.claude/projects/<encoded-repo-path>/memory,
# where the encoded path is the absolute repo path with every / turned into -.
# We point that folder at the repo's tracked .claude/memory so memory rides
# along with git (push = backed up to GitHub).
ENC="$(printf '%s' "$REPO" | sed 's#/#-#g')"
TARGET="$HOME/.claude/projects/$ENC/memory"

mkdir -p "$(dirname "$TARGET")"

if [ -L "$TARGET" ]; then
  ln -sfn "$REPO_MEM" "$TARGET"
  echo "memory: relinked $TARGET -> $REPO_MEM"
elif [ -d "$TARGET" ]; then
  # A real folder is already there. Move it aside so we never lose notes,
  # then link. Reconcile <target>.bak into the repo by hand if it had extras.
  mv "$TARGET" "$TARGET.bak.$$"
  ln -sfn "$REPO_MEM" "$TARGET"
  echo "memory: existing folder saved to $TARGET.bak.$$ ; linked to repo"
  echo "        check that .bak for any notes not already in $REPO_MEM"
else
  ln -sfn "$REPO_MEM" "$TARGET"
  echo "memory: linked $TARGET -> $REPO_MEM"
fi

# --- 2. Manual steps this script cannot do --------------------------------
cat <<'STEPS'

Done with the automatic part. Finish the rest by hand:

KEYS (one SSH key, used twice)
  GitHub: ssh-keygen -t ed25519 -C "you@your-machine", then add
          ~/.ssh/id_ed25519.pub under GitHub > Settings > SSH keys.
          Test: ssh -T git@github.com
  VM:     add the same public key to the VM's castle user.
          Test: ssh castle@<your-vm-ip> true

TOOLS (install if missing)
  gh   GitHub CLI, then: gh auth login
  node/npm (for the github MCP server and web apps)

VERIFY
  gh repo view          # GitHub reachable from this repo
  claude                # start Claude Code in the repo root

Full setup guide: guides/ in this repo.
STEPS
