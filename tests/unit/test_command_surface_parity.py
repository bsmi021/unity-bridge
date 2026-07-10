"""Tests for the source-derived command-surface parity gate."""

from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from textwrap import dedent

import click

from tools.command_surface_parity import (
    build_surface,
    evaluate_registry,
    render_json,
    seed_registry,
)


ROOT = Path(__file__).resolve().parents[2]
REGISTRY = (
    ROOT
    / "docs"
    / "implementation-plans"
    / "unity-6-5-full-editor-coverage"
    / "command-surface-registry.json"
)


def _write_fixture(root: Path) -> click.Group:
    bridge = root / "ClaudeCodeBridge"
    commands = root / "src" / "unity_bridge" / "commands"
    bridge.mkdir(parents=True)
    commands.mkdir(parents=True)
    (bridge / "BridgeCommandRegistry.cs").write_text(
        """
        public static void RegisterAll(System.Action<ICommandHandler> registerHandler)
        {
            registerHandler(new ExampleCommandHandler());
            registerHandler(new DirectCommandHandler());
        }
        """,
        encoding="utf-8",
    )
    (bridge / "ExampleCommandHandler.cs").write_text(
        """
        public sealed class ExampleCommandHandler : ICommandHandler
        {
            public string CommandType => "example";
            public BridgeResponse HandleCommand(BridgeCommand command)
            {
                var p = JsonUtility.FromJson<ExampleParams>(command.parameters);
                switch (p.operation)
                {
                    case "inspect": return Inspect(p);
                    case "set": return Set(p);
                    default: return Error();
                }
            }
        }
        public sealed class ExampleParams
        {
            public string operation;
            public string assetPath;
        }
        """,
        encoding="utf-8",
    )
    (bridge / "DirectCommandHandler.cs").write_text(
        """
        public sealed class DirectCommandHandler : ICommandHandler
        {
            public string CommandType => "direct";
            public BridgeResponse HandleCommand(BridgeCommand command) => Reply(command);
        }
        """,
        encoding="utf-8",
    )
    (commands / "fixture.py").write_text(
        dedent("""
        async def inspect(bridge, path):
            return await bridge.send_command(
                command_type="example",
                parameters={"operation": "inspect", "assetPath": path},
            )

        async def set_value(bridge, path):
            return await bridge.send_command(
                command_type="example",
                parameters={"operation": "set", "asset_path": path},
            )

        async def direct(bridge):
            return await bridge.send_command(command_type="direct", parameters={})
        """),
        encoding="utf-8",
    )

    root_command = click.Group()
    example = click.Group()

    def inspect_cli() -> None:
        pass

    def set_cli() -> None:
        pass

    def direct_cli() -> None:
        pass

    inspect_cli.__module__ = "unity_bridge.commands.fixture"
    set_cli.__module__ = "unity_bridge.commands.fixture"
    direct_cli.__module__ = "unity_bridge.commands.fixture"
    inspect_cli.__name__ = "inspect"
    set_cli.__name__ = "set_value"
    direct_cli.__name__ = "direct"
    example.add_command(click.Command("inspect", callback=inspect_cli))
    example.add_command(click.Command("set", callback=set_cli))
    root_command.add_command(example, "example")
    root_command.add_command(click.Command("direct", callback=direct_cli))
    return root_command


def test_gate_discovers_exact_surfaces_and_flags_field_mismatch(tmp_path: Path) -> None:
    # Arrange
    cli = _write_fixture(tmp_path)
    surface = build_surface(tmp_path, cli_command=cli)
    registry = seed_registry(surface)

    # Act
    report = evaluate_registry(surface, registry)

    # Assert
    assert [item["id"] for item in surface["handlers"]] == [
        "DirectCommandHandler|direct",
        "ExampleCommandHandler|example",
    ]
    assert [item["id"] for item in surface["csharp_operations"]] == [
        "direct|<direct>",
        "example|inspect",
        "example|set",
    ]
    assert [item["path"] for item in surface["cli_leaves"]] == [
        "direct",
        "example inspect",
        "example set",
    ]
    assert report["counts"] == {
        "handlers": 2,
        "csharp_operations": 3,
        "python_command_types": 2,
        "python_operations": 3,
        "cli_leaves": 3,
        "classified": 3,
        "typed_cli": 3,
        "raw_only": 0,
        "internal": 0,
        "unreachable": 0,
        "gaps": 1,
    }
    assert report["field_name_mismatches"] == [
        {
            "id": "example|set",
            "cli_path": "example set",
            "python_only": ["asset_path"],
            "csharp_fields": ["assetPath", "operation"],
        }
    ]
    assert report["is_complete"] is False


def test_gate_output_is_deterministic_and_rejects_unclassified_operation(
    tmp_path: Path,
) -> None:
    # Arrange
    cli = _write_fixture(tmp_path)
    surface = build_surface(tmp_path, cli_command=cli)
    registry = seed_registry(surface)
    registry["records"] = [
        record for record in registry["records"] if record["id"] != "example|set"
    ]

    # Act
    first = evaluate_registry(surface, registry)
    second = evaluate_registry(surface, json.loads(render_json(registry)))

    # Assert
    assert render_json(first) == render_json(second)
    assert first["unclassified_csharp_operations"] == ["example|set"]
    assert first["counts"]["gaps"] == 1
    assert first["is_complete"] is False


def test_gate_rejects_every_versioned_surface_drift_category(tmp_path: Path) -> None:
    # Arrange
    cli = _write_fixture(tmp_path)
    cli.add_command(cli.commands["example"], "example-alias")
    surface = build_surface(tmp_path, cli_command=cli)
    registry = seed_registry(surface)
    drifted = deepcopy(registry)
    drifted["surface"]["handlers"] = [
        "ExampleCommandHandler|example",
        "RemovedHandler|removed",
    ]
    drifted["surface"]["python_command_types"] = ["example", "removed"]
    drifted["surface"]["python_operations"] = ["example|inspect", "removed|old"]
    drifted["surface"]["cli_leaves"] = ["example inspect", "removed old"]

    # Act
    report = evaluate_registry(surface, drifted)

    # Assert
    assert [item["path"] for item in surface["cli_leaves"]] == [
        "direct",
        "example inspect",
        "example set",
        "example-alias inspect",
        "example-alias set",
    ]
    assert report["added_handlers"] == ["DirectCommandHandler|direct"]
    assert report["removed_handlers"] == ["RemovedHandler|removed"]
    assert report["added_python_command_types"] == ["direct"]
    assert report["removed_python_command_types"] == ["removed"]
    assert report["added_python_operations"] == [
        "direct|<direct>",
        "example|set",
    ]
    assert report["removed_python_operations"] == ["removed|old"]
    assert report["added_cli_leaves"] == [
        "direct",
        "example set",
        "example-alias inspect",
        "example-alias set",
    ]
    assert report["removed_cli_leaves"] == ["removed old"]
    assert report["is_complete"] is False


def test_gate_rejects_python_operation_without_csharp_dispatch(tmp_path: Path) -> None:
    # Arrange
    cli = _write_fixture(tmp_path)
    python_source = tmp_path / "src" / "unity_bridge" / "commands" / "fixture.py"
    python_source.write_text(
        python_source.read_text(encoding="utf-8")
        + dedent(
            """

            async def unsupported(bridge):
                return await bridge.send_command(
                    command_type="example",
                    parameters={"operation": "unsupported"},
                )
            """
        ),
        encoding="utf-8",
    )
    surface = build_surface(tmp_path, cli_command=cli)
    registry = seed_registry(surface)

    # Act
    report = evaluate_registry(surface, registry)

    # Assert
    assert report["python_operations_without_csharp_dispatch"] == ["example|unsupported"]
    assert report["counts"]["gaps"] == 2
    assert report["is_complete"] is False


def test_unresolved_parameter_builder_is_not_mislabeled_as_direct(tmp_path: Path) -> None:
    # Arrange
    cli = _write_fixture(tmp_path)
    python_source = tmp_path / "src" / "unity_bridge" / "commands" / "fixture.py"
    python_source.write_text(
        python_source.read_text(encoding="utf-8")
        + dedent(
            """

            def build_params():
                return {"operation": "inspect"}

            async def built_payload(bridge):
                params = build_params()
                return await bridge.send_command(
                    command_type="example",
                    parameters=params,
                )
            """
        ),
        encoding="utf-8",
    )

    # Act
    surface = build_surface(tmp_path, cli_command=cli)
    report = evaluate_registry(surface, seed_registry(surface))

    # Assert
    assert "example|<direct>" not in surface["python_operations"]
    assert "example|<dynamic:unknown>" in surface["python_operations"]
    assert report["python_operations_without_csharp_dispatch"] == []


def test_real_repository_registry_covers_current_source_exactly() -> None:
    # Arrange
    registry = json.loads(REGISTRY.read_text(encoding="utf-8"))

    # Act
    surface = build_surface(ROOT)
    report = evaluate_registry(surface, registry)

    # Assert
    assert report["unclassified_csharp_operations"] == []
    assert report["removed_csharp_operations"] == []
    assert report["added_handlers"] == []
    assert report["removed_handlers"] == []
    assert report["added_python_command_types"] == []
    assert report["removed_python_command_types"] == []
    assert report["added_cli_leaves"] == []
    assert report["removed_cli_leaves"] == []
    assert report["registered_without_python_sender"] == []
    assert report["field_name_mismatches"] == []
    assert report["python_operations_without_csharp_dispatch"] == []
    assert report["counts"] == {
        "handlers": 101,
        "csharp_operations": 406,
        "python_command_types": 100,
        "python_operations": 333,
        "cli_leaves": 394,
        "classified": 406,
        "typed_cli": 305,
        "raw_only": 101,
        "internal": 0,
        "unreachable": 0,
        "gaps": 0,
    }
    assert report["is_complete"] is True
