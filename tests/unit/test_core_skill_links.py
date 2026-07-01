"""Unit tests for core/skill_links.py — cross-agent skill directory linking.

Codex and GitHub Copilot both scan `.agents/skills/<name>` natively, so they
need no extra files. Claude Code only scans `.claude/skills/<name>`, so this
module creates a real directory link (symlink, or an NTFS junction on
Windows when symlink privilege is unavailable) from the Claude Code path
back to the canonical `.agents/skills/<name>` directory.
"""

from __future__ import annotations

import platform
import subprocess
from pathlib import Path
from unittest.mock import patch

import pytest

from unity_bridge.core.skill_links import (
    SkillLinkError,
    create_directory_link,
    is_directory_link,
)


def _make_target(tmp_path: Path, name: str = "agents_skill") -> Path:
    target = tmp_path / name
    target.mkdir()
    (target / "SKILL.md").write_text("---\nname: unity-bridge-cli\n---\n", encoding="utf-8")
    return target


class TestCreateDirectoryLink:
    def test_creates_symlink_when_supported(self, tmp_path: Path) -> None:
        target = _make_target(tmp_path)
        link = tmp_path / "claude_skill"

        result = create_directory_link(link, target)

        # "symlink" when privilege/Developer Mode is available, "junction"
        # as the automatic Windows fallback otherwise -- both are correct.
        assert result in ("symlink", "junction")
        assert is_directory_link(link)
        assert (link / "SKILL.md").read_text(encoding="utf-8") == (
            target / "SKILL.md"
        ).read_text(encoding="utf-8")

    def test_idempotent_when_link_already_correct(self, tmp_path: Path) -> None:
        target = _make_target(tmp_path)
        link = tmp_path / "claude_skill"
        create_directory_link(link, target)

        result = create_directory_link(link, target)

        assert result == "up_to_date"

    def test_replaces_stale_link_pointing_elsewhere(self, tmp_path: Path) -> None:
        target = _make_target(tmp_path)
        other_target = _make_target(tmp_path, name="other")
        link = tmp_path / "claude_skill"
        create_directory_link(link, other_target)

        result = create_directory_link(link, target)

        assert result in ("symlink", "junction")
        assert (link / "SKILL.md").read_text(encoding="utf-8") == (
            target / "SKILL.md"
        ).read_text(encoding="utf-8")

    def test_raises_when_real_directory_occupies_link_path(self, tmp_path: Path) -> None:
        target = _make_target(tmp_path)
        link = tmp_path / "claude_skill"
        link.mkdir()
        sentinel = link / "user_file.txt"
        sentinel.write_text("do not delete me", encoding="utf-8")

        with pytest.raises(SkillLinkError):
            create_directory_link(link, target)

        assert sentinel.exists()

    def test_raises_when_regular_file_occupies_link_path(self, tmp_path: Path) -> None:
        target = _make_target(tmp_path)
        link = tmp_path / "claude_skill"
        link.write_text("not a directory", encoding="utf-8")

        with pytest.raises(SkillLinkError):
            create_directory_link(link, target)

        assert link.is_file()

    def test_falls_back_to_junction_when_symlink_unavailable(self, tmp_path: Path) -> None:
        target = _make_target(tmp_path)
        link = tmp_path / "claude_skill"

        with (
            patch("pathlib.Path.symlink_to", side_effect=OSError("privilege not held")),
            patch("unity_bridge.core.skill_links.platform.system", return_value="Windows"),
            patch("unity_bridge.core.skill_links.subprocess.run") as mock_run,
        ):
            mock_run.return_value = subprocess.CompletedProcess(
                args=[], returncode=0, stdout="", stderr=""
            )
            result = create_directory_link(link, target)

        assert result == "junction"
        mock_run.assert_called_once()
        called_args = mock_run.call_args[0][0]
        assert called_args[:3] == ["cmd", "/c", "mklink"]
        assert "/J" in called_args

    def test_raises_clear_error_when_junction_also_fails(self, tmp_path: Path) -> None:
        target = _make_target(tmp_path)
        link = tmp_path / "claude_skill"

        with (
            patch("pathlib.Path.symlink_to", side_effect=OSError("privilege not held")),
            patch("unity_bridge.core.skill_links.platform.system", return_value="Windows"),
            patch("unity_bridge.core.skill_links.subprocess.run") as mock_run,
        ):
            mock_run.return_value = subprocess.CompletedProcess(
                args=[], returncode=1, stdout="", stderr="Access is denied."
            )
            with pytest.raises(SkillLinkError, match="Developer Mode|Administrator"):
                create_directory_link(link, target)

    def test_non_windows_symlink_failure_raises_without_junction_attempt(
        self, tmp_path: Path
    ) -> None:
        target = _make_target(tmp_path)
        link = tmp_path / "claude_skill"

        with (
            patch("pathlib.Path.symlink_to", side_effect=OSError("nope")),
            patch("unity_bridge.core.skill_links.platform.system", return_value="Linux"),
            patch("unity_bridge.core.skill_links.subprocess.run") as mock_run,
        ):
            with pytest.raises(SkillLinkError):
                create_directory_link(link, target)
            mock_run.assert_not_called()


class TestIsDirectoryLink:
    def test_false_for_regular_directory(self, tmp_path: Path) -> None:
        real_dir = tmp_path / "real"
        real_dir.mkdir()
        assert is_directory_link(real_dir) is False

    def test_false_for_nonexistent_path(self, tmp_path: Path) -> None:
        assert is_directory_link(tmp_path / "missing") is False

    def test_true_for_real_symlink(self, tmp_path: Path) -> None:
        target = _make_target(tmp_path)
        link = tmp_path / "linked"
        try:
            link.symlink_to(target, target_is_directory=True)
        except OSError:
            pytest.skip("symlink privilege unavailable (enable Developer Mode or run as admin)")
        assert is_directory_link(link) is True

    def test_false_on_non_windows_when_not_a_symlink(self, tmp_path: Path) -> None:
        real_dir = tmp_path / "real"
        real_dir.mkdir()
        with patch("unity_bridge.core.skill_links.platform.system", return_value="Linux"):
            assert is_directory_link(real_dir) is False


class TestRemoveDirectoryLink:
    def test_falls_back_to_rmdir_when_unlink_fails(self, tmp_path: Path) -> None:
        from unity_bridge.core.skill_links import _remove_directory_link

        target = _make_target(tmp_path)
        link = tmp_path / "claude_skill"
        link.symlink_to(target, target_is_directory=True)

        with patch("pathlib.Path.unlink", side_effect=OSError("access denied")):
            _remove_directory_link(link)

        assert not link.exists()
        assert not is_directory_link(link)
        assert target.is_dir()  # target content untouched


@pytest.mark.skipif(platform.system() != "Windows", reason="junction is a Windows/NTFS concept")
class TestRealWindowsJunction:
    def test_real_mklink_junction_is_detected_and_reused(self, tmp_path: Path) -> None:
        target = _make_target(tmp_path)
        link = tmp_path / "claude_skill"
        subprocess.run(
            ["cmd", "/c", "mklink", "/J", str(link), str(target)],
            check=True,
            capture_output=True,
        )

        assert is_directory_link(link) is True
        assert create_directory_link(link, target) == "up_to_date"
