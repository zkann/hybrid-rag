#!/usr/bin/env bash
# Pull a real technical-docs corpus into docs_corpus/ for the demo.
# Default: a bounded slice of the FastAPI documentation (markdown-rich API docs).
set -euo pipefail

REPO="${SEED_REPO:-https://github.com/fastapi/fastapi.git}"
SRC_SUBDIR="${SEED_SUBDIR:-docs/en/docs}"
CACHE=".cache/seed-src"
DEST="docs_corpus/fastapi"

mkdir -p "$(dirname "$CACHE")" docs_corpus
rm -rf "$CACHE" "$DEST"

echo "Cloning $REPO (shallow)..."
git clone --depth 1 --quiet "$REPO" "$CACHE"

mkdir -p "$DEST"
# Bounded subset keeps embedding cost/time small; widen by editing these globs.
for sub in tutorial advanced "*.md"; do
  if compgen -G "$CACHE/$SRC_SUBDIR/$sub" >/dev/null 2>&1; then
    cp -R "$CACHE/$SRC_SUBDIR/"$sub "$DEST"/ 2>/dev/null || true
  fi
done

COUNT=$(find "$DEST" -name '*.md' | wc -l | tr -d ' ')
echo "Seeded $COUNT markdown files into $DEST"
