"""Unit tests for commands/workflow.py — tdd, snapshot_save, snapshot_diff."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock


from unity_bridge.core.bridge import CommandResult


def _import_workflow():
    from unity_bridge.commands import workflow
    return workflow


# ---------------------------------------------------------------------------
# tdd
# ---------------------------------------------------------------------------


class TestTdd:

    def _setup_bridge(
        self,
        mock_bridge: MagicMock,
        compile_ok: bool = True,
        test_ok: bool = True,
    ) -> None:
        """Configure mock_bridge.send_command to return staged results."""
        results: dict[str, CommandResult] = {
            "clear-console": CommandResult(success=True),
            "compile": CommandResult(
                success=compile_ok,
                data={"errors": 0} if compile_ok else {"errors": 2, "warnings": 1},
            ),
            "run-tests": CommandResult(
                success=test_ok,
                data={"passed": 5, "failed": 0} if test_ok else {"passed": 3, "failed": 2},
            ),
            "read-console": CommandResult(
                success=True,
                data={"entries": [{"type": "Error", "message": "NullRef"}]},
            ),
        }

        async def route_command(cmd_type: str, *args: Any, **kwargs: Any) -> CommandResult:
            return results.get(cmd_type, CommandResult(success=True))

        mock_bridge.send_command = AsyncMock(side_effect=route_command)

    async def test_tdd_stops_on_compile_failure(self, mock_bridge: MagicMock) -> None:
        workflow = _import_workflow()
        self._setup_bridge(mock_bridge, compile_ok=False)
        result = await workflow.tdd(mock_bridge)
        assert result.success is False
        assert "compile" in (result.error or "").lower() or \
            result.data.get("failed_at") == "compile"

    async def test_tdd_reads_console_on_test_failure(
        self, mock_bridge: MagicMock
    ) -> None:
        workflow = _import_workflow()
        self._setup_bridge(mock_bridge, compile_ok=True, test_ok=False)
        result = await workflow.tdd(mock_bridge)
        assert result.success is False
        # Should have called read-console
        cmd_types = [c.args[0] for c in mock_bridge.send_command.call_args_list]
        assert "read-console" in cmd_types

    async def test_tdd_success_path(self, mock_bridge: MagicMock) -> None:
        workflow = _import_workflow()
        self._setup_bridge(mock_bridge, compile_ok=True, test_ok=True)
        result = await workflow.tdd(mock_bridge)
        assert result.success is True
        assert "steps" in result.data

    async def test_tdd_strict_fails_on_warnings(self, mock_bridge: MagicMock) -> None:
        """--strict treats compilation warnings as failures."""
        workflow = _import_workflow()

        async def route(cmd_type: str, *a: Any, **kw: Any) -> CommandResult:
            if cmd_type == "clear-console":
                return CommandResult(success=True)
            if cmd_type == "compile":
                return CommandResult(
                    success=True,
                    data={"errors": 0, "warnings": 3},
                )
            return CommandResult(success=True)

        mock_bridge.send_command = AsyncMock(side_effect=route)
        result = await workflow.tdd(mock_bridge, strict=True)
        assert result.success is False


# ---------------------------------------------------------------------------
# snapshot_save
# ---------------------------------------------------------------------------


class TestSnapshotSave:

    async def test_writes_valid_json(
        self, mock_bridge: MagicMock, tmp_path: Path, sample_hierarchy: dict
    ) -> None:
        workflow = _import_workflow()
        mock_bridge.send_command = AsyncMock(
            return_value=CommandResult(success=True, data=sample_hierarchy)
        )
        outfile = tmp_path / "snap.json"
        result = await workflow.snapshot_save(mock_bridge, outfile)
        assert result.success is True
        assert outfile.exists()
        snap = json.loads(outfile.read_text(encoding="utf-8"))
        assert "version" in snap
        assert "timestamp" in snap
        assert "hierarchy" in snap


# ---------------------------------------------------------------------------
# snapshot_diff
# ---------------------------------------------------------------------------


class TestSnapshotDiff:

    async def test_detects_added_objects(self, tmp_path: Path) -> None:
        workflow = _import_workflow()
        snap1 = {
            "hierarchy": {
                "children": [
                    {"name": "Camera", "components": ["Transform"], "children": []}
                ]
            }
        }
        snap2 = {
            "hierarchy": {
                "children": [
                    {"name": "Camera", "components": ["Transform"], "children": []},
                    {"name": "Player", "components": ["Transform"], "children": []},
                ]
            }
        }
        f1 = tmp_path / "snap1.json"
        f2 = tmp_path / "snap2.json"
        f1.write_text(json.dumps(snap1), encoding="utf-8")
        f2.write_text(json.dumps(snap2), encoding="utf-8")

        result = await workflow.snapshot_diff(f1, f2)
        assert result.success is True
        assert "Player" in result.data["added"]

    async def test_detects_removed_objects(self, tmp_path: Path) -> None:
        workflow = _import_workflow()
        snap1 = {
            "hierarchy": {
                "children": [
                    {"name": "Camera", "components": [], "children": []},
                    {"name": "OldObj", "components": [], "children": []},
                ]
            }
        }
        snap2 = {
            "hierarchy": {
                "children": [
                    {"name": "Camera", "components": [], "children": []}
                ]
            }
        }
        f1 = tmp_path / "s1.json"
        f2 = tmp_path / "s2.json"
        f1.write_text(json.dumps(snap1), encoding="utf-8")
        f2.write_text(json.dumps(snap2), encoding="utf-8")

        result = await workflow.snapshot_diff(f1, f2)
        assert "OldObj" in result.data["removed"]

    async def test_detects_modified_components(self, tmp_path: Path) -> None:
        workflow = _import_workflow()
        snap1 = {
            "hierarchy": {
                "children": [
                    {"name": "Player", "components": ["Transform"], "children": []}
                ]
            }
        }
        snap2 = {
            "hierarchy": {
                "children": [
                    {
                        "name": "Player",
                        "components": ["Transform", "Rigidbody"],
                        "children": [],
                    }
                ]
            }
        }
        f1 = tmp_path / "s1.json"
        f2 = tmp_path / "s2.json"
        f1.write_text(json.dumps(snap1), encoding="utf-8")
        f2.write_text(json.dumps(snap2), encoding="utf-8")

        result = await workflow.snapshot_diff(f1, f2)
        modified = result.data["modified"]
        assert len(modified) >= 1
        assert any("Rigidbody" in str(m) for m in modified)


# ---------------------------------------------------------------------------
# Helper functions (count_objects, truncate_hierarchy)
# ---------------------------------------------------------------------------


class TestHierarchyHelpers:

    def test_count_objects_recursive(self, sample_hierarchy: dict) -> None:
        workflow = _import_workflow()
        count = workflow.count_objects(sample_hierarchy)
        # sample_hierarchy has: Camera, Light, Player, Weapon, Muzzle, Shield,
        # Environment, Ground, Trees, Oak_01, Pine_01 = 11 objects
        assert count == 11

    def test_count_objects_empty(self) -> None:
        workflow = _import_workflow()
        assert workflow.count_objects({"children": []}) == 0

    def test_truncate_hierarchy_respects_max(self, sample_hierarchy: dict) -> None:
        workflow = _import_workflow()
        original_count = workflow.count_objects(sample_hierarchy)
        truncated = workflow.truncate_hierarchy(sample_hierarchy, max_objects=3)
        truncated_count = workflow.count_objects(truncated)
        # Truncated should have fewer objects than original
        assert truncated_count < original_count

    def test_truncate_does_not_mutate_original(self, sample_hierarchy: dict) -> None:
        workflow = _import_workflow()
        import copy
        original = copy.deepcopy(sample_hierarchy)
        workflow.truncate_hierarchy(sample_hierarchy, max_objects=2)
        assert sample_hierarchy == original
