#!/usr/bin/env bash
# One-command setup for your castle, run from the repo root: ./setup.sh
# Safe to run again at any time; it never overwrites answers without asking.
set -euo pipefail

cd "$(dirname "$0")"

say() { printf '%s\n' "$*"; }
ok() { printf '  \342\234\224 %s\n' "$*"; }
miss() { printf '  \342\234\230 %s\n' "$*"; }

say ""
say "Welcome to Claude Castle setup."
say ""

# 1. Tool check ---------------------------------------------------------------
say "Checking your tools:"
MISSING=0
check_tool() {
  local cmd="$1" name="$2" hint="$3"
  if command -v "$cmd" >/dev/null 2>&1; then
    ok "$name"
  else
    miss "$name is not installed. $hint"
    MISSING=1
  fi
}
check_tool git   "git (version control)"        "See guides/02-install-the-tools.md"
check_tool gh    "gh (GitHub CLI)"              "See guides/02-install-the-tools.md"
check_tool claude "claude (Claude Code)"        "See guides/02-install-the-tools.md"
check_tool scw   "scw (Scaleway CLI)"           "See guides/02-install-the-tools.md"
check_tool uv    "uv (Python manager)"          "See guides/02-install-the-tools.md"

if [ "$MISSING" -eq 1 ]; then
  say ""
  say "Some tools are missing. Install them first (guides/02-install-the-tools.md),"
  say "then run ./setup.sh again. Tip: once Claude Code is installed you can paste"
  say "prompts/01-check-my-setup.md into it and Claude fixes the rest with you."
fi

# 2. Your settings ------------------------------------------------------------
mkdir -p config
ENV_FILE="config/castle.env"
EXAMPLE_FILE="config/castle.env.example"

if [ -f "$ENV_FILE" ]; then
  say ""
  say "Found existing $ENV_FILE, leaving your answers as they are."
else
  say ""
  say "A few questions. Press Enter to accept a default shown in [brackets]."
  read -r -p "Your domain name (example: castle.example.com): " CASTLE_DOMAIN
  read -r -p "Scaleway region [fr-par]: " CASTLE_REGION
  CASTLE_REGION="${CASTLE_REGION:-fr-par}"
  DEFAULT_REPO="$(git remote get-url origin 2>/dev/null | sed -E 's#(git@github.com:|https://github.com/)##; s#\.git$##' || true)"
  read -r -p "Your GitHub repo [${DEFAULT_REPO:-yourname/claude-castle}]: " GITHUB_REPO
  GITHUB_REPO="${GITHUB_REPO:-${DEFAULT_REPO:-yourname/claude-castle}}"

  cp "$EXAMPLE_FILE" "$ENV_FILE"
  # Fill in the three answers; everything else stays as a labelled placeholder.
  sed -i.bak \
    -e "s|^CASTLE_DOMAIN=.*|CASTLE_DOMAIN=${CASTLE_DOMAIN}|" \
    -e "s|^CASTLE_REGION=.*|CASTLE_REGION=${CASTLE_REGION}|" \
    -e "s|^GITHUB_REPO=.*|GITHUB_REPO=${GITHUB_REPO}|" \
    "$ENV_FILE" && rm -f "$ENV_FILE.bak"
  ok "Wrote $ENV_FILE (this file stays on your laptop, git ignores it)."
fi

# 3. Claude memory ------------------------------------------------------------
if [ -x .claude/bootstrap.sh ]; then
  say ""
  say "Wiring up Claude's persistent memory:"
  ./.claude/bootstrap.sh
fi

# 4. Next steps ---------------------------------------------------------------
say ""
say "Setup done. Next:"
say "  1. Open guides/00-start-here.md and follow the guides in order."
say "  2. When a guide says PLAYBOOK, start 'claude' in this folder and paste that prompts/ file."
say ""
