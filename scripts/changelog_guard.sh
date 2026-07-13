#!/usr/bin/env bash
set -euo pipefail

if [ ! -f CHANGELOG.md ]; then
  echo "ERRORE: CHANGELOG.md non trovato"
  exit 1
fi

if ! grep -q '^## Unreleased' CHANGELOG.md; then
  echo "ERRORE: CHANGELOG.md deve contenere una sezione Unreleased"
  exit 1
fi
