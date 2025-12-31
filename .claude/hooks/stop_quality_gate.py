#!/usr/bin/env python3
"""Stop hook - runs quality gates when Claude stops (if files were modified)."""

import subprocess
import sys
from pathlib import Path

marker_file = Path(".claude/.state/files_modified_marker.txt")

if not marker_file.exists():
    print("[StopHook] No files modified, skipping quality gate.")
    sys.exit(0)

marker_file.unlink()  # Clear marker

print("[StopHook] Running quality gate (ruff check)...")
result = subprocess.run(["ruff", "check", ".", "--fix"], capture_output=True, text=True)
if result.returncode != 0:
    print(result.stdout)
    print(result.stderr, file=sys.stderr)
    print("[StopHook] Quality gate failed. Fix issues before next session.", file=sys.stderr)
    # Don't block stop, just warn

sys.exit(0)
