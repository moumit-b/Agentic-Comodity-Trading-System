#!/usr/bin/env python3
"""
Quick script to run the Streamlit dashboard locally for testing.
Prerequisites: docker-compose up -d (for postgres + redis)
"""

import subprocess
import sys
from pathlib import Path

def main():
    """Run the Streamlit dashboard."""
    # Get project root
    project_root = Path(__file__).parent.parent

    print("=" * 80)
    print("Starting Streamlit Dashboard (Local Testing)")
    print("=" * 80)
    print()
    print("Prerequisites:")
    print("  ✓ Docker Compose running (postgres + redis)")
    print("  ✓ Environment variables set in .env")
    print()
    print("Dashboard will be available at: http://localhost:8501")
    print("Press Ctrl+C to stop")
    print("=" * 80)
    print()

    # Run streamlit
    dashboard_path = project_root / "dashboard" / "app.py"

    cmd = [
        sys.executable,
        "-m",
        "streamlit",
        "run",
        str(dashboard_path),
        "--server.port=8501",
        "--server.address=localhost",
        "--theme.base=dark",
    ]

    try:
        subprocess.run(cmd, cwd=str(project_root))
    except KeyboardInterrupt:
        print("\n\nDashboard stopped.")
        sys.exit(0)

if __name__ == "__main__":
    main()
