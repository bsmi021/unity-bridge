"""CLI wrapper tests for material commands."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any
from unittest.mock import MagicMock

from typer.testing import CliRunner

from unity_bridge.commands.material import material_app
from unity_bridge.core.output import OutputFormatter


def _state(mock_bridge: MagicMock) -> SimpleNamespace:
    return SimpleNamespace(bridge=mock_bridge, formatter=OutputFormatter())


def _params(call_args: Any) -> dict[str, object]:
    if call_args.kwargs.get("parameters") is not None:
        return call_args.kwargs["parameters"]
    return call_args.args[1]


def _run_material(args: list[str], mock_bridge: MagicMock):
    runner = CliRunner()
    return runner.invoke(material_app, args, obj=_state(mock_bridge))


def test_modify_cli_sends_properties(mock_bridge: MagicMock) -> None:
    result = _run_material(
        ["modify", "Assets/M.mat", "--properties", '{"_Color":{"r":1}}'],
        mock_bridge,
    )

    assert result.exit_code == 0
    params = _params(mock_bridge.send_command_with_retry.call_args)
    assert params["operation"] == "modify"
    assert params["materialPath"] == "Assets/M.mat"
    assert params["properties"] == {"_Color": {"r": 1}}


def test_create_cli_sends_create_operation(mock_bridge: MagicMock) -> None:
    result = _run_material(["create", "Assets/New.mat"], mock_bridge)

    assert result.exit_code == 0
    params = _params(mock_bridge.send_command_with_retry.call_args)
    assert params == {"operation": "create", "materialPath": "Assets/New.mat"}


def test_modify_cli_allows_missing_properties(mock_bridge: MagicMock) -> None:
    result = _run_material(["modify", "Assets/M.mat"], mock_bridge)

    assert result.exit_code == 0
    params = _params(mock_bridge.send_command_with_retry.call_args)
    assert params == {"operation": "modify", "materialPath": "Assets/M.mat"}


def test_duplicate_cli_sends_duplicate_operation(mock_bridge: MagicMock) -> None:
    result = _run_material(["duplicate", "Assets/M.mat"], mock_bridge)

    assert result.exit_code == 0
    params = _params(mock_bridge.send_command_with_retry.call_args)
    assert params == {"operation": "duplicate", "materialPath": "Assets/M.mat"}


def test_enable_keyword_cli_sends_keyword(mock_bridge: MagicMock) -> None:
    result = _run_material(["enable-keyword", "Assets/M.mat", "_EMISSION"], mock_bridge)

    assert result.exit_code == 0
    params = _params(mock_bridge.send_command_with_retry.call_args)
    assert params["operation"] == "enable-keyword"
    assert params["keyword"] == "_EMISSION"


def test_disable_keyword_cli_sends_keyword(mock_bridge: MagicMock) -> None:
    result = _run_material(["disable-keyword", "Assets/M.mat", "_EMISSION"], mock_bridge)

    assert result.exit_code == 0
    params = _params(mock_bridge.send_command_with_retry.call_args)
    assert params["operation"] == "disable-keyword"
    assert params["keyword"] == "_EMISSION"


def test_get_keywords_cli_sends_get_keywords(mock_bridge: MagicMock) -> None:
    result = _run_material(["get-keywords", "Assets/M.mat"], mock_bridge)

    assert result.exit_code == 0
    params = _params(mock_bridge.send_command_with_retry.call_args)
    assert params == {"operation": "get-keywords", "materialPath": "Assets/M.mat"}


def test_set_render_queue_cli_sends_render_queue(mock_bridge: MagicMock) -> None:
    result = _run_material(["set-render-queue", "Assets/M.mat", "3000"], mock_bridge)

    assert result.exit_code == 0
    params = _params(mock_bridge.send_command_with_retry.call_args)
    assert params["operation"] == "set-render-queue"
    assert params["renderQueue"] == 3000


def test_copy_properties_cli_uses_target_then_source(mock_bridge: MagicMock) -> None:
    result = _run_material(
        ["copy-properties", "Assets/Target.mat", "Assets/Source.mat"],
        mock_bridge,
    )

    assert result.exit_code == 0
    params = _params(mock_bridge.send_command_with_retry.call_args)
    assert params["operation"] == "copy-properties"
    assert params["materialPath"] == "Assets/Target.mat"
    assert params["sourceMaterialPath"] == "Assets/Source.mat"


def test_modify_cli_rejects_invalid_property_json(mock_bridge: MagicMock) -> None:
    result = _run_material(["modify", "Assets/M.mat", "--properties", "not-json"], mock_bridge)

    assert result.exit_code != 0
    assert "Invalid JSON for --properties" in result.output
    mock_bridge.send_command_with_retry.assert_not_called()


def test_modify_cli_rejects_non_object_property_json(mock_bridge: MagicMock) -> None:
    result = _run_material(["modify", "Assets/M.mat", "--properties", '["_Color"]'], mock_bridge)

    assert result.exit_code != 0
    assert "--properties must be a JSON object" in result.output
    mock_bridge.send_command_with_retry.assert_not_called()
