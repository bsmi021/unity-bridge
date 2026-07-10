"""Unit tests for commands/scripting.py — script command."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from unity_bridge.core.bridge import CommandResult

ROOT = Path(__file__).resolve().parents[2]


def _import_scripting():
    from unity_bridge.commands import scripting

    return scripting


# ---------------------------------------------------------------------------
# script — expression execution
# ---------------------------------------------------------------------------


class TestScript:
    async def test_builds_correct_parameters(self, mock_bridge: MagicMock) -> None:
        scripting = _import_scripting()
        await scripting.execute_script(mock_bridge, expression="Debug.Log('hi')")
        call_args = mock_bridge.send_command_with_retry.call_args
        params = _extract_parameters(call_args)
        assert params["expression"] == "Debug.Log('hi')"
        assert params["manifest"] == {
            "intent": "read-only",
            "expectedAssemblies": [],
            "expectedAssemblyIdentities": [],
            "declaredObjectIds": [],
            "declaredFilePaths": [],
            "timeoutMs": 30000,
            "undoLabel": "",
            "returnSchema": "auto",
            "allowInternalReflection": False,
        }

    async def test_sends_explicit_mutation_manifest(self, mock_bridge: MagicMock) -> None:
        scripting = _import_scripting()

        await scripting.execute_script(
            mock_bridge,
            expression='Selection.activeGameObject.name = "Player";',
            intent="mutating",
            expected_assemblies=["Assembly-CSharp-Editor", "My.Package.Editor"],
            declared_object_ids=["GlobalObjectId_V1-2-3-4-5"],
            declared_file_paths=["Assets/Data/config.asset"],
            undo_label="Rename selected object",
            return_schema="void",
            allow_internal_reflection=True,
            timeout=45,
        )

        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert params["manifest"] == {
            "intent": "mutating",
            "expectedAssemblies": ["Assembly-CSharp-Editor", "My.Package.Editor"],
            "expectedAssemblyIdentities": [],
            "declaredObjectIds": ["GlobalObjectId_V1-2-3-4-5"],
            "declaredFilePaths": ["Assets/Data/config.asset"],
            "timeoutMs": 45000,
            "undoLabel": "Rename selected object",
            "returnSchema": "void",
            "allowInternalReflection": True,
        }

    async def test_sends_exact_assembly_identity_manifest(
        self, mock_bridge: MagicMock, tmp_path: Path
    ) -> None:
        scripting = _import_scripting()
        assembly_path = tmp_path / "Package.Editor.dll"

        await scripting.execute_script(
            mock_bridge,
            expression="Package.Api.Version",
            assembly_identities=[
                scripting.AssemblyIdentityRequest(
                    full_name=(
                        "Package.Editor, Version=1.2.3.0, Culture=neutral, PublicKeyToken=null"
                    ),
                    mvid="11111111-1111-1111-1111-111111111111",
                    path=assembly_path,
                )
            ],
        )

        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert params["manifest"]["expectedAssemblies"] == []
        assert params["manifest"]["expectedAssemblyIdentities"] == [
            {
                "fullName": (
                    "Package.Editor, Version=1.2.3.0, Culture=neutral, PublicKeyToken=null"
                ),
                "mvid": "11111111-1111-1111-1111-111111111111",
                "path": assembly_path.resolve().as_posix(),
            }
        ]

    @pytest.mark.parametrize(
        "identity_factory",
        [
            pytest.param(
                lambda scripting: scripting.AssemblyIdentityRequest(
                    full_name="Package.Editor",
                    mvid="11111111-1111-1111-1111-111111111111",
                    path=Path("Package.Editor.dll"),
                ),
                id="simple-name-is-not-full-identity",
            ),
            pytest.param(
                lambda scripting: scripting.AssemblyIdentityRequest(
                    full_name="Package.Editor, Version=1.0.0.0",
                    mvid="not-a-guid",
                    path=Path("Package.Editor.dll"),
                ),
                id="invalid-mvid",
            ),
        ],
    )
    async def test_rejects_malformed_exact_assembly_identity(
        self, mock_bridge: MagicMock, identity_factory: Any
    ) -> None:
        scripting = _import_scripting()

        with pytest.raises(ValueError, match="assembly identity"):
            await scripting.execute_script(
                mock_bridge,
                expression="Package.Api.Version",
                assembly_identities=[identity_factory(scripting)],
            )

        mock_bridge.send_command_with_retry.assert_not_called()

    async def test_rejects_duplicate_exact_assembly_identity(
        self, mock_bridge: MagicMock, tmp_path: Path
    ) -> None:
        scripting = _import_scripting()
        request = scripting.AssemblyIdentityRequest(
            full_name="Package.Editor, Version=1.0.0.0",
            mvid="11111111-1111-1111-1111-111111111111",
            path=tmp_path / "Package.Editor.dll",
        )

        with pytest.raises(ValueError, match="duplicate identity"):
            await scripting.execute_script(
                mock_bridge,
                expression="Package.Api.Version",
                assembly_identities=[request, request],
            )

        mock_bridge.send_command_with_retry.assert_not_called()

    def test_exact_assembly_cli_option_parser_is_explicit(self) -> None:
        scripting = _import_scripting()
        value = (
            "Package.Editor, Version=1.0.0.0|"
            "11111111-1111-1111-1111-111111111111|C:/Packages/Package.Editor.dll"
        )

        request = scripting._parse_identity_option(value)

        assert request.full_name == "Package.Editor, Version=1.0.0.0"
        assert request.mvid == "11111111-1111-1111-1111-111111111111"
        assert request.path.as_posix() == "C:/Packages/Package.Editor.dll"
        with pytest.raises(ValueError, match="FULL_NAME"):
            scripting._parse_identity_option("Package.Editor")

    @pytest.mark.parametrize(
        ("kwargs", "message"),
        [
            ({"intent": "write"}, "intent"),
            ({"intent": "mutating"}, "undo_label"),
            ({"intent": "mutating", "undo_label": "Mutation"}, "declared"),
            ({"return_schema": "object"}, "return_schema"),
            ({"timeout": 0}, "timeout"),
            ({"expected_assemblies": ["Assembly-CSharp", "Assembly-CSharp"]}, "duplicate"),
            ({"expected_assemblies": [""]}, "empty"),
            (
                {
                    "declared_object_ids": [
                        "GlobalObjectId_V1-2-3-4-5",
                        "GlobalObjectId_V1-2-3-4-5",
                    ]
                },
                "duplicate",
            ),
            ({"declared_file_paths": [""]}, "empty"),
            (
                {
                    "assembly_identities": [
                        {
                            "full_name": "Package.Editor, Version=1.0.0.0",
                            "mvid": "not-a-guid",
                            "path": "Package.Editor.dll",
                        }
                    ]
                },
                "assembly_identities",
            ),
        ],
    )
    async def test_rejects_invalid_manifest_before_dispatch(
        self,
        mock_bridge: MagicMock,
        kwargs: dict[str, Any],
        message: str,
    ) -> None:
        scripting = _import_scripting()

        with pytest.raises(ValueError, match=message):
            await scripting.execute_script(mock_bridge, expression="1 + 1", **kwargs)

        mock_bridge.send_command_with_retry.assert_not_called()

    async def test_command_type_is_execute_script(self, mock_bridge: MagicMock) -> None:
        scripting = _import_scripting()
        await scripting.execute_script(mock_bridge, expression="1+1")
        call_args = mock_bridge.send_command_with_retry.call_args
        cmd_type = _extract_command_type(call_args)
        assert cmd_type == "execute-script"

    async def test_file_reads_content(self, mock_bridge: MagicMock, tmp_path: Path) -> None:
        scripting = _import_scripting()
        script_file = tmp_path / "setup.cs"
        script_file.write_text(
            'var go = new GameObject("Test");\ngo.transform.position = Vector3.up;',
            encoding="utf-8",
        )
        await scripting.execute_script(mock_bridge, expression=None, file=script_file)
        call_args = mock_bridge.send_command_with_retry.call_args
        params = _extract_parameters(call_args)
        assert "new GameObject" in params["expression"]

    @pytest.mark.parametrize("mode", ["both", "missing-file", "neither"])
    async def test_rejects_invalid_script_source(
        self, mock_bridge: MagicMock, tmp_path: Path, mode: str
    ) -> None:
        scripting = _import_scripting()
        expression = "1 + 1" if mode in {"both"} else None
        file = tmp_path / "missing.cs" if mode in {"both", "missing-file"} else None

        with pytest.raises(ValueError):
            await scripting.execute_script(mock_bridge, expression=expression, file=file)

        mock_bridge.send_command_with_retry.assert_not_called()

    def test_cli_forwards_repeatable_declared_targets(self, mock_bridge: MagicMock) -> None:
        scripting = _import_scripting()
        context = MagicMock()
        context.obj = SimpleNamespace(bridge=mock_bridge, formatter=MagicMock())

        with patch("unity_bridge.core.output.print_result") as print_result:
            scripting.script_cli(
                context,
                expression='Selection.activeObject.name = "Changed";',
                file=None,
                intent="mutating",
                assembly=["Assembly-CSharp-Editor"],
                assembly_identity=[],
                object_id=["GlobalObjectId_V1-2-3-4-5"],
                asset_path=["Assets/Data/config.asset"],
                undo_label="Change selected object",
                return_schema="void",
                allow_internal_reflection=False,
                timeout=30,
            )

        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert params["manifest"]["declaredObjectIds"] == ["GlobalObjectId_V1-2-3-4-5"]
        assert params["manifest"]["declaredFilePaths"] == ["Assets/Data/config.asset"]
        print_result.assert_called_once()

    async def test_timeout_passed_through(self, mock_bridge: MagicMock) -> None:
        scripting = _import_scripting()
        await scripting.execute_script(mock_bridge, expression="1+1", timeout=60)
        call_args = mock_bridge.send_command_with_retry.call_args
        timeout = _extract_kwarg(call_args, "timeout")
        assert timeout == 60.0 or timeout == 60

    async def test_returns_command_result(self, mock_bridge: MagicMock) -> None:
        scripting = _import_scripting()
        expected = CommandResult(
            success=True,
            data={"result": "42", "resultType": "System.Int32"},
        )
        mock_bridge.send_command_with_retry.return_value = expected
        result = await scripting.execute_script(mock_bridge, expression="40+2")
        assert result.success is True
        assert result.data["result"] == "42"

    def test_csharp_handler_exists_and_is_registered(self) -> None:
        handler = ROOT / "ClaudeCodeBridge" / "ExecuteScriptCommandHandler.cs"
        registry = ROOT / "ClaudeCodeBridge" / "BridgeCommandRegistry.cs"

        assert handler.is_file()
        assert 'CommandType => "execute-script"' in handler.read_text(encoding="utf-8")
        assert "new ExecuteScriptCommandHandler()" in registry.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


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


def _extract_kwarg(call_args: Any, key: str) -> Any:
    if key in call_args.kwargs:
        return call_args.kwargs[key]
    return None
