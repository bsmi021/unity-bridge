"""Unit tests for commands/lifecycle.py — init, clean, version, install."""

from __future__ import annotations

import json
import os
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

from unity_bridge.core.operation import STATE_COMPLETED, OperationStore


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


def _create_operation_record(store: OperationStore, command_id: str) -> None:
    """Create a queued operation record with matching event history."""
    store.create_queued(
        command_id=command_id,
        command_type="query-hierarchy",
        parameters={},
        command_path=store.project_root / ".claude" / "unity" / "commands" / f"{command_id}.json",
        response_path=(
            store.project_root / ".claude" / "unity" / "responses" / f"{command_id}.json"
        ),
        domain_generation=None,
        retry_policy="read_only",
    )


def _backdate_terminal_record(store: OperationStore, command_id: str, minutes: int) -> None:
    """Set terminal timestamps old enough for lifecycle clean to remove."""
    record_path = store.record_path(command_id)
    payload = json.loads(record_path.read_text(encoding="utf-8"))
    timestamp = (datetime.now(timezone.utc) - timedelta(minutes=minutes)).isoformat()
    payload["terminalAt"] = timestamp
    payload["lastProgressAt"] = timestamp
    record_path.write_text(json.dumps(payload), encoding="utf-8")


class TestClean:
    async def test_removes_old_files(self, fake_project: Path) -> None:
        lifecycle = _import_lifecycle()
        cmd_dir = fake_project / ".claude" / "unity" / "commands"
        # Create a stale file
        old_file = cmd_dir / "old-cmd.json"
        old_file.write_text("{}", encoding="utf-8")
        # Backdate the modification time
        old_time = time.time() - 600  # 10 minutes ago

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

        os.utime(old_file, (old_time, old_time))

        result = await lifecycle.clean(fake_project, age_minutes=5, dry_run=True)
        assert result.success is True
        assert old_file.exists()  # still there

    async def test_removes_old_temp_files_from_bridge_state(
        self,
        fake_project: Path,
    ) -> None:
        lifecycle = _import_lifecycle()
        store = OperationStore(fake_project)
        bridge_root = fake_project / ".claude" / "unity"
        old_temp_files = [
            bridge_root / "commands" / "cmd.json.tmp",
            bridge_root / "responses" / "response.json.tmp",
            store.operations_path / "operation.json.tmp",
            store.operations_path / "operation.json.abc123.tmp",
        ]
        for path in old_temp_files:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("partial", encoding="utf-8")
            old_time = time.time() - 600
            os.utime(path, (old_time, old_time))
        recent_temp = store.operations_path / "recent.json.tmp"
        recent_temp.write_text("partial", encoding="utf-8")

        result = await lifecycle.clean(fake_project, age_minutes=5)

        assert result.success is True
        for path in old_temp_files:
            assert not path.exists()
            assert str(path) in result.data["files"]
        assert recent_temp.exists()

    async def test_removes_old_terminal_operation_records(self, fake_project: Path) -> None:
        lifecycle = _import_lifecycle()
        store = OperationStore(fake_project)
        _create_operation_record(store, "done")
        store.transition("done", STATE_COMPLETED, reason="success")
        _backdate_terminal_record(store, "done", minutes=10)

        result = await lifecycle.clean(fake_project, age_minutes=5)

        assert result.success is True
        assert not store.record_path("done").exists()
        assert not store.events_path("done").exists()

    async def test_keeps_active_operation_records_when_cleaning_all(
        self,
        fake_project: Path,
    ) -> None:
        lifecycle = _import_lifecycle()
        store = OperationStore(fake_project)
        _create_operation_record(store, "active")
        _create_operation_record(store, "done")
        store.transition("done", STATE_COMPLETED, reason="success")
        temp_file = store.operations_path / "active.json.tmp"
        temp_file.write_text("partial", encoding="utf-8")

        result = await lifecycle.clean(fake_project, all_files=True)

        assert result.success is True
        assert store.record_path("active").exists()
        assert store.events_path("active").exists()
        assert not temp_file.exists()
        assert not store.record_path("done").exists()
        assert not store.events_path("done").exists()

    async def test_dry_run_reports_terminal_operations_without_deleting(
        self,
        fake_project: Path,
    ) -> None:
        lifecycle = _import_lifecycle()
        store = OperationStore(fake_project)
        _create_operation_record(store, "done")
        store.transition("done", STATE_COMPLETED, reason="success")
        _backdate_terminal_record(store, "done", minutes=10)

        result = await lifecycle.clean(fake_project, age_minutes=5, dry_run=True)

        assert result.success is True
        assert store.record_path("done").exists()
        assert store.events_path("done").exists()
        assert str(store.record_path("done")) in result.data["files"]
        assert str(store.events_path("done")) in result.data["files"]


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

    async def test_bridge_version_matches_cli(self) -> None:
        lifecycle = _import_lifecycle()
        result = await lifecycle.version()
        assert result.data["bridge_version"] == result.data["cli_version"]
        assert result.data["bridge_version"] != "unknown"


# ---------------------------------------------------------------------------
# install
# ---------------------------------------------------------------------------


def _create_fake_bridge_source(tmp_path: Path) -> Path:
    """Create a fake ClaudeCodeBridge source directory with test files."""
    source = tmp_path / "ClaudeCodeBridge"
    source.mkdir()
    (source / "ClaudeUnityBridge.cs").write_text("// main bridge", encoding="utf-8")
    (source / "ClaudeUnityBridge.cs.meta").write_text("meta", encoding="utf-8")
    (source / "BridgeModels.cs").write_text("// models", encoding="utf-8")
    (source / "BridgeModels.cs.meta").write_text("meta", encoding="utf-8")
    return source


def _create_fake_skill_source(tmp_path: Path) -> Path:
    """Create a fake unity-bridge-cli skill directory."""
    source = tmp_path / "unity-bridge-cli"
    references = source / "references"
    references.mkdir(parents=True)
    (source / "SKILL.md").write_text("---\nname: unity-bridge-cli\n---\n", encoding="utf-8")
    (references / "tools-commands.md").write_text("# Tools\n", encoding="utf-8")
    return source


class TestInstall:
    def test_bridge_source_falls_back_to_installed_bundle(self, tmp_path: Path) -> None:
        lifecycle = _import_lifecycle()
        module_file = tmp_path / "site-packages" / "unity_bridge" / "commands" / "lifecycle.py"
        bundled = (
            tmp_path / "site-packages" / "unity_bridge" / "_bundled_bridge" / "ClaudeCodeBridge"
        )
        bundled.mkdir(parents=True)
        (bundled / "ClaudeUnityBridge.cs").write_text("// bundled bridge", encoding="utf-8")

        with patch.object(lifecycle, "__file__", str(module_file)):
            source = lifecycle._get_bridge_source_dir()

        assert source == bundled

    async def test_install_copies_files(self, fake_project: Path, tmp_path: Path) -> None:
        lifecycle = _import_lifecycle()
        source = _create_fake_bridge_source(tmp_path)

        with patch.object(lifecycle, "_get_bridge_source_dir", return_value=source):
            result = await lifecycle.install(fake_project)

        assert result.success is True
        target = fake_project / "Assets" / "Scripts" / "Editor" / "ClaudeCodeBridge"
        assert (target / "ClaudeUnityBridge.cs").is_file()
        assert (target / "BridgeModels.cs").is_file()

    async def test_install_copies_project_skill(self, fake_project: Path, tmp_path: Path) -> None:
        lifecycle = _import_lifecycle()
        bridge_source = _create_fake_bridge_source(tmp_path)
        skill_source = _create_fake_skill_source(tmp_path)

        with (
            patch.object(lifecycle, "_get_bridge_source_dir", return_value=bridge_source),
            patch.object(lifecycle, "_get_skill_source_dir", return_value=skill_source),
        ):
            result = await lifecycle.install(fake_project)

        assert result.success is True
        target = fake_project / ".agents" / "skills" / "unity-bridge-cli"
        assert (target / "SKILL.md").is_file()
        assert (target / "references" / "tools-commands.md").is_file()
        assert result.data["skill"]["action"] == "install"
        assert result.data["skill"]["files_copied"] == 2

    async def test_install_creates_manifest(self, fake_project: Path, tmp_path: Path) -> None:
        lifecycle = _import_lifecycle()
        source = _create_fake_bridge_source(tmp_path)

        with patch.object(lifecycle, "_get_bridge_source_dir", return_value=source):
            result = await lifecycle.install(fake_project)

        assert result.success is True
        target = fake_project / "Assets" / "Scripts" / "Editor" / "ClaudeCodeBridge"
        manifest_path = target / "bridge_manifest.json"
        assert manifest_path.is_file()
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        assert "version" in manifest
        assert "files" in manifest
        assert "ClaudeUnityBridge.cs" in manifest["files"]

    async def test_install_check_not_installed(self, fake_project: Path) -> None:
        lifecycle = _import_lifecycle()
        result = await lifecycle.install(fake_project, check=True)
        assert result.success is True
        assert result.data["installed"] is False
        assert result.data["skill"]["installed"] is False

    async def test_install_check_up_to_date(self, fake_project: Path, tmp_path: Path) -> None:
        lifecycle = _import_lifecycle()
        source = _create_fake_bridge_source(tmp_path)

        with patch.object(lifecycle, "_get_bridge_source_dir", return_value=source):
            await lifecycle.install(fake_project)
            result = await lifecycle.install(fake_project, check=True)

        assert result.success is True
        assert result.data["installed"] is True
        assert result.data["status"] == "up_to_date"
        assert result.data["skill"]["status"] == "up_to_date"

    async def test_install_force_reinstalls(self, fake_project: Path, tmp_path: Path) -> None:
        lifecycle = _import_lifecycle()
        source = _create_fake_bridge_source(tmp_path)

        with patch.object(lifecycle, "_get_bridge_source_dir", return_value=source):
            await lifecycle.install(fake_project)
            result = await lifecycle.install(fake_project, force=True)

        assert result.success is True
        assert result.data["action"] in ("install", "update")

    async def test_install_skips_when_up_to_date(
        self,
        fake_project: Path,
        tmp_path: Path,
    ) -> None:
        lifecycle = _import_lifecycle()
        source = _create_fake_bridge_source(tmp_path)

        with patch.object(lifecycle, "_get_bridge_source_dir", return_value=source):
            await lifecycle.install(fake_project)
            result = await lifecycle.install(fake_project)

        assert result.success is True
        assert result.data["action"] == "up_to_date"
        assert result.data["skill"]["action"] == "up_to_date"

    async def test_install_restores_missing_bridge_file_when_version_unchanged(
        self, fake_project: Path, tmp_path: Path
    ) -> None:
        """A plain `install` (no --force) must detect and restore a bridge file
        that went missing from the target directory, even though the stored
        manifest's version string still matches the current version — it must
        not rely on version-string equality alone to decide "up to date"."""
        lifecycle = _import_lifecycle()
        source = _create_fake_bridge_source(tmp_path)

        with patch.object(lifecycle, "_get_bridge_source_dir", return_value=source):
            await lifecycle.install(fake_project)
            target = fake_project / "Assets" / "Scripts" / "Editor" / "ClaudeCodeBridge"
            (target / "BridgeModels.cs").unlink()
            (target / "BridgeModels.cs.meta").unlink()

            result = await lifecycle.install(fake_project)

        assert result.success is True
        assert result.data["action"] == "update"
        target = fake_project / "Assets" / "Scripts" / "Editor" / "ClaudeCodeBridge"
        assert (target / "BridgeModels.cs").is_file()
        assert (target / "BridgeModels.cs.meta").is_file()

    async def test_install_updates_skill_when_bridge_is_up_to_date(
        self, fake_project: Path, tmp_path: Path
    ) -> None:
        lifecycle = _import_lifecycle()
        bridge_source = _create_fake_bridge_source(tmp_path)
        skill_source = _create_fake_skill_source(tmp_path)

        with (
            patch.object(lifecycle, "_get_bridge_source_dir", return_value=bridge_source),
            patch.object(lifecycle, "_get_skill_source_dir", return_value=skill_source),
        ):
            await lifecycle.install(fake_project)
            target_skill = fake_project / ".agents" / "skills" / "unity-bridge-cli"
            (target_skill / "SKILL.md").write_text("stale", encoding="utf-8")
            result = await lifecycle.install(fake_project)

        assert result.success is True
        assert result.data["action"] == "update"
        assert result.data["skill"]["action"] == "update"
        assert (target_skill / "SKILL.md").read_text(encoding="utf-8").startswith("---")

    async def test_install_skill_source_not_found(self, fake_project: Path, tmp_path: Path) -> None:
        lifecycle = _import_lifecycle()
        source = _create_fake_bridge_source(tmp_path)

        with (
            patch.object(lifecycle, "_get_bridge_source_dir", return_value=source),
            patch.object(lifecycle, "_get_skill_source_dir", return_value=None),
        ):
            result = await lifecycle.install(fake_project)

        assert result.success is False
        assert "skill source directory not found" in result.error

    async def test_install_source_not_found(self, fake_project: Path) -> None:
        lifecycle = _import_lifecycle()

        with patch.object(lifecycle, "_get_bridge_source_dir", return_value=None):
            result = await lifecycle.install(fake_project)

        assert result.success is False
        assert "source directory not found" in result.error

    async def test_install_no_project(self) -> None:
        lifecycle = _import_lifecycle()

        with patch("unity_bridge.core.project.find_unity_project_root", return_value=None):
            result = await lifecycle.install(project_root=None)

        assert result.success is False
        assert "not found" in result.error
