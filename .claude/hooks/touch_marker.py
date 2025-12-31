#!/usr/bin/env python3
"""Touch marker hook - marks that files have been modified."""

import sys
from datetime import datetime
from pathlib import Path

marker_file = Path(".claude/.state/files_modified_marker.txt")
marker_file.parent.mkdir(parents=True, exist_ok=True)
marker_file.write_text(f"Modified at {datetime.now().isoformat()}\n")
sys.exit(0)
