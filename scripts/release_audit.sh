#!/usr/bin/env bash
set -euo pipefail

ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
cd "$ROOT"

echo "== Audit rilascio =="

echo "[1] Controllo working tree pulito..."
git diff --quiet || { echo "ERRORE: working tree sporco"; exit 1; }
git diff --cached --quiet || { echo "ERRORE: modifiche staged non committate"; exit 1; }

echo "[2] Controllo allineamento branch..."
LOCAL=$(git rev-parse @)
REMOTE=$(git rev-parse @{u} 2>/dev/null || echo "")
if [ -n "$REMOTE" ] && [ "$LOCAL" != "$REMOTE" ]; then
  BASE=$(git merge-base @ @{u})
  if [ "$LOCAL" = "$BASE" ]; then
    echo "ERRORE: branch indietro rispetto al remoto"
    exit 1
  fi
fi

echo "[3] Controllo ancestry dell'ultimo tag..."
LATEST_TAG=$(git tag --sort=-v:refname | head -1)
if [ -n "$LATEST_TAG" ]; then
  if ! git merge-base --is-ancestor "$LATEST_TAG" HEAD; then
    echo "ERRORE: l'ultimo tag non e' un antenato di HEAD"
    exit 1
  fi
fi

echo "[4] Controllo changelog guard..."
bash scripts/changelog_guard.sh

echo "OK: baseline rilascio valida"
