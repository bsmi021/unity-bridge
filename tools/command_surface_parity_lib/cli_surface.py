"""Runtime Typer/Click leaf discovery and producer reachability."""

from __future__ import annotations

from typing import Any

from .models import FunctionFacts, PythonProducer


def discover_cli(cli_command: Any | None) -> list[dict[str, str]]:
    """Return exact invokable paths and callback symbols."""
    if cli_command is None:
        from typer.main import get_command
        from unity_bridge.app import app

        cli_command = get_command(app)
    leaves: list[dict[str, str]] = []

    def walk(command: Any, path: tuple[str, ...]) -> None:
        if hasattr(command, "commands"):
            if command.invoke_without_command and command.callback and path:
                leaves.append(_cli_record(path, command.callback))
            for name, child in sorted(command.commands.items()):
                walk(child, (*path, name))
            return
        if path:
            leaves.append(_cli_record(path, command.callback))

    walk(cli_command, ())
    return sorted(leaves, key=lambda item: item["path"])


def producer_record(
    producer: PythonProducer,
    leaves: list[dict[str, str]],
    facts: dict[str, FunctionFacts],
) -> dict[str, Any]:
    """Join one producer to every runtime CLI leaf that reaches it."""
    cli_paths = []
    for leaf in leaves:
        if leaf["module"] != producer.module:
            continue
        reachable = _reachable_functions(producer.module, leaf["callback"], facts)
        if producer.function in reachable:
            cli_paths.append(leaf["path"])
    return {
        "id": producer.identifier,
        "command_type": producer.command_type,
        "operation": producer.operation,
        "operation_variable": producer.operation_variable,
        "fields": list(producer.fields),
        "module": producer.module,
        "function": producer.function,
        "source": producer.source,
        "cli_paths": sorted(cli_paths),
    }


def _cli_record(path: tuple[str, ...], callback: Any) -> dict[str, str]:
    return {
        "path": " ".join(path),
        "module": getattr(callback, "__module__", ""),
        "callback": getattr(callback, "__name__", ""),
    }


def _reachable_functions(module: str, start: str, facts: dict[str, FunctionFacts]) -> set[str]:
    visited: set[str] = set()
    pending = [start]
    while pending:
        current = pending.pop()
        if current in visited:
            continue
        visited.add(current)
        item = facts.get(f"{module}:{current}")
        if item:
            pending.extend(callee for callee, _, _ in item.calls)
    return visited
