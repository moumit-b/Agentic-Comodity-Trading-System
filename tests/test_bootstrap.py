"""Bootstrap verification test - ensures the project is set up correctly."""

import sys
from pathlib import Path


def test_python_version():
    """Verify Python 3.12+ is being used."""
    assert sys.version_info >= (3, 12), "Python 3.12+ required"


def test_project_structure():
    """Verify key directories exist."""
    project_root = Path(__file__).parent.parent

    required_dirs = [
        "src",
        "tests",
        "docs",
        "scripts",
        ".claude/commands",
        ".claude/skills",
        ".claude/hooks",
        "context/local",
        "context/shared",
    ]

    for dir_path in required_dirs:
        full_path = project_root / dir_path
        assert full_path.exists(), f"Missing directory: {dir_path}"
        assert full_path.is_dir(), f"Not a directory: {dir_path}"


def test_config_files_exist():
    """Verify key configuration files exist."""
    project_root = Path(__file__).parent.parent

    required_files = [
        "CLAUDE.md",
        "GEMINI.md",
        ".gitignore",
        ".env.example",
        "pyproject.toml",
        "docs/PROJECT_REQUIREMENTS.md",
        "docs/TRADING_SYSTEM_PLAN.md",
        "docs/DEV_WORKFLOW.md",
        "context/shared/runbook.md",
    ]

    for file_path in required_files:
        full_path = project_root / file_path
        assert full_path.exists(), f"Missing file: {file_path}"
        assert full_path.is_file(), f"Not a file: {file_path}"


def test_hooks_exist():
    """Verify all Python hooks are in place."""
    project_root = Path(__file__).parent.parent

    hook_files = [
        ".claude/hooks/git_guard.py",
        ".claude/hooks/touch_marker.py",
        ".claude/hooks/stop_quality_gate.py",
    ]

    for hook_path in hook_files:
        full_path = project_root / hook_path
        assert full_path.exists(), f"Missing hook: {hook_path}"
        content = full_path.read_text()
        assert "#!/usr/bin/env python3" in content or "python3" in content.lower()


def test_src_package_importable():
    """Verify src package can be imported."""
    try:
        import src

        assert hasattr(src, "__version__")
        assert src.__version__ == "0.1.0"
    except ImportError as e:
        raise AssertionError(f"Cannot import src package: {e}")
