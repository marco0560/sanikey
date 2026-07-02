#!/usr/bin/env python3
"""Compatibility wrapper for ``sanikey build-database``."""

from __future__ import annotations

import sys

from sanikey_command import main_for_script

if __name__ == "__main__":
    raise SystemExit(main_for_script("build_database.py", sys.argv[1:]))
