"""Unit tests for core/project.py — project detection and BridgePaths."""

from __future__ import annotations

from pathlib import Path

import pytest

from unity_bridge.core.project import (
    BridgePaths,
    detect_unity_project,
    get_bridge_paths,
)


# ---------------------------------------------------------------------------
# detect_unity_project
# ---------------------------------------------------------------------------


class TestDetectUnityProject:

    def test_detects_project_from_root(self, fake_project: Path) -> None:
        """Project root with Assets/ and ProjectSettings/ is detected."""
        result = detect_unity_project(fake_project)
        assert result == fake_project

    def test_walks_up_from_subdirectory(self, fake_project: Path) -> None:
        """Starting from Assets/Scripts/ should find the project root."""
        sub = fake_project / "Assets" / "Scripts"
        sub.mkdir(parents=True, exist_ok=True)
        result = detect_unity_project(sub)
        assert result == fake_project

    def test_walks_up_from_claude_dir(self, fake_project: Path) -> None:
        start = fake_project / ".claude" / "unity" / "commands"
        result = detect_unity_project(start)
        assert result == fake_project

    def test_no_project_found_raises(self, tmp_path: Path) -> None:
        """Raises when no Unity project structure exists."""
        empty = tmp_path / "empty_dir"
        empty.mkdir()
        with pytest.raises((FileNotFoundError, SystemExit, RuntimeError)):
            detect_unity_project(empty)

    def test_none_start_uses_cwd(self, fake_project: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.chdir(fake_project)
        result = detect_unity_project(None)
        assert result == fake_project


# ---------------------------------------------------------------------------
# BridgePaths
# ---------------------------------------------------------------------------


class TestBridgePaths:

    def test_construction(self, fake_project: Path) -> None:
        paths = get_bridge_paths(fake_project)
        assert isinstance(paths, BridgePaths)
        assert paths.project_root == fake_project
        assert paths.commands_dir == fake_project / ".claude" / "unity" / "commands"
        assert paths.responses_dir == fake_project / ".claude" / "unity" / "responses"
        assert paths.heartbeat_file == fake_project / ".claude" / "unity" / "heartbeat.json"

    def test_editor_bridge_dir(self, fake_project: Path) -> None:
        paths = get_bridge_paths(fake_project)
        expected = fake_project / "Assets" / "Scripts" / "Editor" / "ClaudeCodeBridge"
        assert paths.editor_bridge_dir == expected

    def test_all_paths_are_absolute(self, fake_project: Path) -> None:
        paths = get_bridge_paths(fake_project)
        assert paths.project_root.is_absolute()
        assert paths.commands_dir.is_absolute()
        assert paths.responses_dir.is_absolute()
        assert paths.heartbeat_file.is_absolute()
