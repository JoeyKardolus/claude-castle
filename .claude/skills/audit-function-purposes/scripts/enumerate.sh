#!/usr/bin/env bash
# Enumerate every Python function in scope. Outputs path\tline\tend\tlength\tname,
# sorted by length descending. Agent then reads top-N candidates and judges them
# per SKILL.md.

set -euo pipefail

REPO="$(git rev-parse --show-toplevel)"
SHA="$(git -C "$REPO" rev-parse --short HEAD)"
OUT_DIR="$REPO/tmp/_audit-function-purposes"
mkdir -p "$OUT_DIR"

SCOPES=("apps" "lib")

CANDIDATES="$OUT_DIR/candidates.tsv"
PARSE_ERRORS="$OUT_DIR/parse-errors.txt"
: > "$CANDIDATES"
: > "$PARSE_ERRORS"

# ── AST walk via standalone helper ───────────────────────────────────────────
HELPER="$OUT_DIR/_walk.py"
cat > "$HELPER" <<'PYEOF'
import ast
import os
import sys

repo, candidates_path, errors_path = sys.argv[1:4]
files = sys.argv[4:]

with open(candidates_path, "a") as out, open(errors_path, "a") as err:
    for path in files:
        try:
            with open(path, encoding="utf-8") as fh:
                source = fh.read()
            tree = ast.parse(source, filename=path)
        except (SyntaxError, OSError) as exc:
            err.write(f"{path}\t{exc}\n")
            continue

        rel = os.path.relpath(path, repo)
        for node in ast.walk(tree):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            start = node.lineno
            end = node.end_lineno or start
            length = end - start + 1
            out.write(f"{rel}\t{start}\t{end}\t{length}\t{node.name}\n")
PYEOF

for scope in "${SCOPES[@]}"; do
    [ -d "$REPO/$scope" ] || continue
    find "$REPO/$scope" -name '*.py' -type f \
        ! -path '*/tests/*' \
        ! -path '*/migrations/*' \
        ! -path '*/node_modules/*' \
        ! -path '*/__pycache__/*' \
        ! -path '*/.venv/*' \
        -print0 \
    | xargs -0 python3 "$HELPER" "$REPO" "$CANDIDATES" "$PARSE_ERRORS"
done

rm -f "$HELPER"

# ── Sort by length descending ────────────────────────────────────────────────
sort -t$'\t' -k4 -rn "$CANDIDATES" -o "$CANDIDATES"

TOTAL=$(wc -l < "$CANDIDATES" | tr -d ' ')
ERRORS=$(wc -l < "$PARSE_ERRORS" | tr -d ' ')

echo "candidates: $TOTAL fns"
echo "parse errors: $ERRORS files"
echo ""
echo "top 20 by length:"
head -20 "$CANDIDATES" | awk -F'\t' '{printf "  %4s  %s:%s  %s\n", $4, $1, $2, $5}'
echo ""
echo "full list: $CANDIDATES"
echo "next: agent reads candidates top-down, emits verdicts per SKILL.md."
echo "final report: $REPO/tmp/audit-function-purposes-${SHA}.md"
