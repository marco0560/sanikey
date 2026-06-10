#!/usr/bin/env bash
set -euo pipefail

if [ ! -f CHANGELOG.md ]; then
  echo "ERROR: CHANGELOG.md not found"
  exit 1
fi

if ! grep -q '^## Unreleased' CHANGELOG.md; then
  echo "ERROR: CHANGELOG.md must contain an Unreleased section"
  exit 1
fi
