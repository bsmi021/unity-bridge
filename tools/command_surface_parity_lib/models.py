"""Shared models and serialization for command-surface parity."""

from __future__ import annotations

import ast
import json
from dataclasses import dataclass
from typing import Any


DIRECT_OPERATION = "<direct>"
CLASSIFICATIONS = {"typed_cli", "raw_only", "internal", "unreachable"}


@dataclass(frozen=True)
class PythonProducer:
    """One statically observed bridge payload producer."""

    command_type: str
    operation: str | None
    operation_variable: str | None
    fields: tuple[str, ...]
    module: str
    function: str
    source: str

    @property
    def identifier(self) -> str:
        if self.operation is not None:
            operation = self.operation
        elif self.operation_variable is not None:
            operation = f"<dynamic:{self.operation_variable}>"
        else:
            operation = DIRECT_OPERATION
        return f"{self.command_type}|{operation}"


@dataclass(frozen=True)
class FunctionFacts:
    """AST facts needed to resolve producer call chains."""

    parameters: tuple[str, ...]
    calls: tuple[tuple[str, tuple[ast.expr, ...], dict[str, ast.expr]], ...]


def render_json(value: Any) -> str:
    """Return stable, review-friendly JSON bytes as text."""
    return json.dumps(value, indent=2, sort_keys=True, ensure_ascii=True) + "\n"
