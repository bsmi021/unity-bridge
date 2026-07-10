"""Unit tests for commands/script_edit.py — safe MonoScript text edits."""

from __future__ import annotations

from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

from typer.testing import CliRunner

from unity_bridge.core.bridge import CommandResult
from unity_bridge.core.output import OutputFormatter

ROOT = Path(__file__).resolve().parents[2]


def _import_script_edit():
    from unity_bridge.commands import script_edit

    return script_edit


class TestScriptEditRange:
    async def test_sends_range_edit_payload(self, mock_bridge: MagicMock) -> None:
        mod = _import_script_edit()

        await mod.script_edit_range(
            mock_bridge,
            "Assets/Scripts/Player.cs",
            start_line=10,
            end_line=12,
            replacement="private int health;",
            if_match="abc123",
        )

        call_args = mock_bridge.send_command_with_retry.call_args
        assert _extract_command_type(call_args) == "script-edit"
        assert _extract_parameters(call_args) == {
            "operation": "range",
            "assetPath": "Assets/Scripts/Player.cs",
            "startLine": 10,
            "endLine": 12,
            "replacement": "private int health;",
            "ifMatch": "abc123",
        }

    async def test_omits_if_match_when_absent(self, mock_bridge: MagicMock) -> None:
        mod = _import_script_edit()

        await mod.script_edit_range(
            mock_bridge,
            "Assets/Scripts/Player.cs",
            start_line=1,
            end_line=1,
            replacement="using System;",
        )

        assert "ifMatch" not in _extract_parameters(mock_bridge.send_command_with_retry.call_args)


class TestScriptEditAnchor:
    async def test_sends_anchor_edit_payload(self, mock_bridge: MagicMock) -> None:
        mod = _import_script_edit()

        await mod.script_edit_anchor(
            mock_bridge,
            "Assets/Scripts/Player.cs",
            anchor="// TODO",
            replacement="// Done",
            occurrence=2,
        )

        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert params["operation"] == "anchor"
        assert params["assetPath"] == "Assets/Scripts/Player.cs"
        assert params["anchor"] == "// TODO"
        assert params["replacement"] == "// Done"
        assert params["occurrence"] == 2

    async def test_returns_command_result(self, mock_bridge: MagicMock) -> None:
        mod = _import_script_edit()
        expected = CommandResult(success=True, data={"success": True, "sha256After": "def456"})
        mock_bridge.send_command_with_retry.return_value = expected

        result = await mod.script_edit_anchor(
            mock_bridge,
            "Assets/Scripts/Player.cs",
            anchor="old",
            replacement="new",
        )

        assert result.data["sha256After"] == "def456"


class TestScriptEditCli:
    def test_range_cli_passes_payload(self, mock_bridge: MagicMock) -> None:
        mod = _import_script_edit()

        result = CliRunner().invoke(
            mod.script_edit_app,
            [
                "range",
                "Assets/Scripts/Player.cs",
                "--start-line",
                "3",
                "--end-line",
                "4",
                "--replacement",
                "new text",
                "--if-match",
                "abc123",
            ],
            obj=_state(mock_bridge),
        )

        assert result.exit_code == 0
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert params["startLine"] == 3
        assert params["endLine"] == 4
        assert params["ifMatch"] == "abc123"

    def test_anchor_cli_passes_payload(self, mock_bridge: MagicMock) -> None:
        mod = _import_script_edit()

        result = CliRunner().invoke(
            mod.script_edit_app,
            [
                "anchor",
                "Assets/Scripts/Player.cs",
                "--anchor",
                "old",
                "--replacement",
                "new",
            ],
            obj=_state(mock_bridge),
        )

        assert result.exit_code == 0
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert params["operation"] == "anchor"
        assert params["occurrence"] == 1


class TestScriptEditBridgeSource:
    def test_csharp_handler_exists_registered_and_enforces_safety(self) -> None:
        handler = ROOT / "ClaudeCodeBridge" / "ScriptEditCommandHandler.cs"
        models = ROOT / "ClaudeCodeBridge" / "ScriptEditModels.cs"
        registry = ROOT / "ClaudeCodeBridge" / "BridgeCommandRegistry.cs"

        assert handler.is_file()
        handler_source = handler.read_text(encoding="utf-8")
        model_source = models.read_text(encoding="utf-8")
        registry_source = registry.read_text(encoding="utf-8")

        assert 'CommandType => "script-edit"' in handler_source
        assert "ComputeSha256" in handler_source
        assert "ifMatch" in model_source
        assert "Hash precondition failed" in handler_source
        assert "ProjectAssetPath.TryResolve" in handler_source
        assert 'StartsWith("Assets/"' not in handler_source
        assert 'EndsWith(".cs"' in handler_source
        assert "AssetDatabase.ImportAsset" in handler_source
        assert "compileFeedback" in model_source
        assert "new ScriptEditCommandHandler()" in registry_source


def _extract_parameters(call_args: Any) -> dict:
    if call_args.kwargs.get("parameters") is not None:
        return call_args.kwargs["parameters"]
    if len(call_args.args) >= 2:
        return call_args.args[1]
    return {}


def _extract_command_type(call_args: Any) -> str:
    if "command_type" in call_args.kwargs:
        return call_args.kwargs["command_type"]
    return call_args.args[0]


def _state(mock_bridge: MagicMock):
    return type(
        "State",
        (),
        {
            "bridge": mock_bridge,
            "formatter": OutputFormatter(),
        },
    )()
