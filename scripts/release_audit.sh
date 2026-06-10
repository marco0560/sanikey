#!/usr/bin/env bash
set -euo pipefail

ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
cd "$ROOT"

echo "== Release Audit =="

echo "[1] Checking working tree clean..."
git diff --quiet || { echo "ERROR: dirty working tree"; exit 1; }
git diff --cached --quiet || { echo "ERROR: staged but uncommitted changes"; exit 1; }

echo "[2] Checking branch alignment..."
LOCAL=$(git rev-parse @)
REMOTE=$(git rev-parse @{u} 2>/dev/null || echo "")
if [ -n "$REMOTE" ] && [ "$LOCAL" != "$REMOTE" ]; then
  BASE=$(git merge-base @ @{u})
  if [ "$LOCAL" = "$BASE" ]; then
    echo "ERROR: branch behind remote"
    exit 1
  fi
fi

echo "[3] Checking latest tag ancestry..."
LATEST_TAG=$(git tag --sort=-v:refname | head -1)
if [ -n "$LATEST_TAG" ]; then
  if ! git merge-base --is-ancestor "$LATEST_TAG" HEAD; then
    echo "ERROR: latest tag is not an ancestor of HEAD"
    exit 1
  fi
fi

echo "[4] Checking changelog guard..."
bash scripts/changelog_guard.sh

echo "OK: release baseline valid"
