#!/usr/bin/env python3
"""
Git commit-msg hook enforcing Conventional Commit formatting.

This hook validates the first line of the commit message against a
restricted Conventional Commit format and ensures that the optional
scope belongs to a predefined list of allowed scopes.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ALLOWED_TYPES = {
    "feat",
    "fix",
    "docs",
    "perf",
    "refactor",
    "test",
    "chore",
    "style",
}
ALLOWED_SCOPES = {
    "build",
    "ci",
    "cli",
    "config",
    "core",
    "decision",
    "dev",
    "docs",
    "git",
    "release",
    "scaffold",
    "template",
    "tests",
    "validation",
}

msg_file = sys.argv[1]

with Path(msg_file).open(encoding="utf-8") as handle:
    first_line = handle.readline().strip()

pattern = re.compile(
    r"^(?P<type>feat|fix|docs|perf|refactor|test|chore|style)"
    r"(\((?P<scope>[a-z0-9._-]+)\))?"
    r"(?P<breaking>!)?: "
    r".{1,72}$"
)

match = pattern.match(first_line)
if not match:
    print("ERROR: commit message non compliant.")
    print("Expected format:")
    print("  type(scope): summary")
    print("Types admitted:")
    for item in sorted(ALLOWED_TYPES):
        print(f"  - {item}")
    raise SystemExit(1)

scope = match.group("scope")
if scope and scope not in ALLOWED_SCOPES:
    print(f"ERROR: scope '{scope}' not admitted.")
    print("Scopes admitted:")
    for item in sorted(ALLOWED_SCOPES):
        print(f"  - {item}")
    raise SystemExit(1)
