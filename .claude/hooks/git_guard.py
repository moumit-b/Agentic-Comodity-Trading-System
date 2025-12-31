#!/usr/bin/env python3
"""Git guard hook - prevents accidental git commits/pushes."""

import json
import sys

# Read tool input from stdin (JSON payload from Claude Code)
try:
    if not sys.stdin.isatty():
        payload = json.loads(sys.stdin.read())
    else:
        payload = {}
except (json.JSONDecodeError, Exception):
    payload = {}

command = payload.get("command", "")

blocked = ["git commit", "git push", "git rebase", "git reset", "git cherry-pick"]

for blocked_cmd in blocked:
    if command.strip().startswith(blocked_cmd):
        print(f"BLOCKED: Moumit controls git. Attempted: {command}", file=sys.stderr)
        sys.exit(2)  # Non-zero exit blocks the tool

sys.exit(0)  # Allow the tool to proceed
