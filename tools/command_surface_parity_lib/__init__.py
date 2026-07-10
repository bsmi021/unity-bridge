"""Public command-surface parity API."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .cli_surface import discover_cli, producer_record
from .csharp_surface import discover_csharp
from .gate import evaluate_registry, seed_registry
from .models import render_json
from .python_surface import discover_python


def build_surface(root: Path, cli_command: Any | None = None) -> dict[str, Any]:
    """Discover every parity surface below *root*."""
    root = root.resolve()
    handlers, operations = discover_csharp(root)
    producers, facts = discover_python(root)
    leaves = discover_cli(cli_command)
    producer_records = [producer_record(item, leaves, facts) for item in producers]
    return {
        "schema_version": "1.0",
        "handlers": handlers,
        "csharp_operations": operations,
        "python_command_types": sorted({item.command_type for item in producers}),
        "python_operations": sorted({item.identifier for item in producers}),
        "python_producers": sorted(producer_records, key=_producer_sort_key),
        "cli_leaves": leaves,
    }


def _producer_sort_key(item: dict[str, Any]) -> tuple[Any, ...]:
    return (item["id"], item["module"], item["function"], item["fields"])


__all__ = [
    "build_surface",
    "evaluate_registry",
    "render_json",
    "seed_registry",
]
