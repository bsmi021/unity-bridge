"""Unit tests for commands/lifecycle.py — init, clean, version, install."""

from __future__ import annotations

import json
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from unity_bridge.core.bridge import CommandResult


# ---------------------------------------------------------------------------
# Lazy imports — lifecycle module may not exist yet; tests are structured
# to fail clearly when it does.
# ---------------------------------------------------------------------------


def _import_lifecycle():
    """Import lifecycle module — raises ImportError if not yet created."""
    from unity_bridge.commands import lifecycle
    return lifecycle


# ---------------------------------------------------------------------------
# init
# ---------------------------------------------------------------------------


class TestInit:

    async def test_creates_directories(self, tmp_path: Path) -> None:
        lifecycle = _import_lifecycle()
        (tmp_path / "Assets").mkdir()
        (tmp_path / "ProjectSettings").mkdir()
        result = await lifecycle.init(tmp_path)
        assert result.success is True
        assert (tmp_path / ".claude" / "unity" / "commands").exists()
        assert (tmp_path / ".claude" / "unity" / "responses").exists()

    async def test_idempotent_on_existing(self, fake_project: Path) -> None:
        lifecycle = _import_lifecycle()
        result = await lifecycle.init(fake_project)
        assert result.success is True
        # Directories already existed; should still succeed

    async def test_returns_created_list(self, tmp_path: Path) -> None:
        lifecycle = _import_lifecycle()
        (tmp_path / "Assets").mkdir()
        (tmp_path / "ProjectSettings").mkdir()
        result = await lifecycle.init(tmp_path)
        assert "created" in result.data or "project_root" in result.data


# ---------------------------------------------------------------------------
# clean
# ---------------------------------------------------------------------------


class TestClean:

    async def test_removes_old_files(self, fake_project: Path) -> None:
        lifecycle = _import_lifecycle()
        cmd_dir = fake_project / ".claude" / "unity" / "commands"
        # Create a stale file
        old_file = cmd_dir / "old-cmd.json"
        old_file.write_text("{}", encoding="utf-8")
        # Backdate the modification time
        old_time = time.time() - 600  # 10 minutes ago
        import os
        os.utime(old_file, (old_time, old_time))

        result = await lifecycle.clean(fake_project, age_minutes=5)
        assert result.success is True
        assert not old_file.exists()

    async def test_skips_recent_files(self, fake_project: Path) -> None:
        lifecycle = _import_lifecycle()
        cmd_dir = fake_project / ".claude" / "unity" / "commands"
        recent = cmd_dir / "recent-cmd.json"
        recent.write_text("{}", encoding="utf-8")

        result = await lifecycle.clean(fake_project, age_minutes=5)
        assert result.success is True
        assert recent.exists()  # should NOT be deleted

    async def test_dry_run_does_not_delete(self, fake_project: Path) -> None:
        lifecycle = _import_lifecycle()
        cmd_dir = fake_project / ".claude" / "unity" / "commands"
        old_file = cmd_dir / "old-cmd.json"
        old_file.write_text("{}", encoding="utf-8")
        old_time = time.time() - 600
        import os
        os.utime(old_file, (old_time, old_time))

        result = await lifecycle.clean(fake_project, age_minutes=5, dry_run=True)
        assert result.success is True
        assert old_file.exists()  # still there


# ---------------------------------------------------------------------------
# version
# ---------------------------------------------------------------------------


class TestVersion:

    async def test_returns_version_data(self) -> None:
        lifecycle = _import_lifecycle()
        result = await lifecycle.version()
        assert result.success is True
        assert isinstance(result.data, dict)
        assert "cli_version" in result.data
        assert "python_version" in result.data

    async def test_includes_python_version(self) -> None:
        lifecycle = _import_lifecycle()
        result = await lifecycle.version()
        assert "3." in result.data["python_version"]

    async def test_includes_platform(self) -> None:
        lifecycle = _import_lifecycle()
        result = await lifecycle.version()
        assert "platform" in result.data
