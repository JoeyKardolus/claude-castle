#!/usr/bin/env bash
# Mechanical dead-code audit: vulture (Python) + ts-prune (TS) + shellcheck SC2034 (bash).
# Outputs intermediate findings under tmp/_audit-mechanical/. The LLM resolve pass
# is performed separately by the agent (see SKILL.md).

set -euo pipefail

REPO="$(git rev-parse --show-toplevel)"
SHA="$(git -C "$REPO" rev-parse --short HEAD)"
OUT_DIR="$REPO/tmp/_audit-mechanical"
mkdir -p "$OUT_DIR"

PY_SCOPE=("apps" "lib")

# -- 1. Python (vulture) ------------------------------------------------------
echo "running vulture..."
PY_OUT="$OUT_DIR/python.txt"
{
    for scope in "${PY_SCOPE[@]}"; do
        if [ -d "$REPO/$scope" ]; then
            uv run --with vulture vulture \
                --min-confidence 80 \
                --exclude '**/.venv/**,**/node_modules/**,**/migrations/**,**/tests/**' \
                "$REPO/$scope" 2>&1 || true
        fi
    done
} > "$PY_OUT"
echo "  -> $PY_OUT ($(wc -l < "$PY_OUT") lines)"

# -- 2. TypeScript (ts-prune) -------------------------------------------------
echo "running ts-prune..."
TS_OUT="$OUT_DIR/typescript.txt"
{
    for pkg in "$REPO"/apps/*/ "$REPO"/lib/*/; do
        if [ -f "$pkg/package.json" ] && [ -f "$pkg/tsconfig.json" ]; then
            (cd "$pkg" && npx --yes ts-prune 2>&1 || true)
        fi
    done
} > "$TS_OUT"
echo "  -> $TS_OUT ($(wc -l < "$TS_OUT") lines)"

# -- 3. Bash (shellcheck SC2034) ----------------------------------------------
SH_OUT="$OUT_DIR/bash.txt"
if command -v shellcheck >/dev/null 2>&1; then
    echo "running shellcheck SC2034..."
    {
        { find "$REPO/infra" -name '*.sh' -type f 2>/dev/null; ls "$REPO/setup.sh" 2>/dev/null; } \
            | xargs -r shellcheck --include=SC2034 --format=tty 2>&1 || true
    } > "$SH_OUT"
    echo "  -> $SH_OUT ($(wc -l < "$SH_OUT") lines)"
else
    echo "shellcheck not installed; skipping bash pass (install: apt-get install shellcheck)"
    echo "(shellcheck not installed; bash pass skipped)" > "$SH_OUT"
fi

# -- Summary --------------------------------------------------------------------
SUMMARY="$OUT_DIR/summary.md"
{
    echo "# Mechanical dead-code findings, $SHA"
    echo ""
    echo "## Python (vulture)"
    echo ""
    echo '```'
    cat "$PY_OUT"
    echo '```'
    echo ""
    echo "## TypeScript (ts-prune)"
    echo ""
    echo '```'
    cat "$TS_OUT"
    echo '```'
    echo ""
    echo "## Bash (shellcheck SC2034)"
    echo ""
    echo '```'
    cat "$SH_OUT"
    echo '```'
} > "$SUMMARY"

echo ""
echo "-- mechanical pass done --"
echo "summary: $SUMMARY"
echo ""
echo "next: agent runs the LLM resolve pass per SKILL.md; reads each flagged"
echo "symbol's import sites and assigns Dead | Live | Uncertain verdict."
echo "final report goes to: $REPO/tmp/audit-dead-code-${SHA}.md"
