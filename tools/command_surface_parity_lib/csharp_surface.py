"""C# handler and operation discovery."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from .models import DIRECT_OPERATION


REGISTERED_HANDLER = re.compile(r"registerHandler\s*\(\s*new\s+([A-Za-z_][A-Za-z0-9_]*)\s*\(")
COMMAND_TYPE = re.compile(r"\bCommandType\s*=>\s*\"([^\"]+)\"")
CLASS_DECLARATION = re.compile(r"\bclass\s+([A-Za-z_][A-Za-z0-9_]*)\b")
PARAMETER_TYPE = re.compile(
    r"(?:FromJson|GetParameters|ParseParameters)\s*<\s*([A-Za-z_][A-Za-z0-9_]*)\s*>"
)
PUBLIC_FIELD = re.compile(
    r"\bpublic\s+(?!class\b|struct\b|interface\b|enum\b)"
    r"[A-Za-z_][A-Za-z0-9_<>,.\[\]?]*\s+"
    r"([A-Za-z_][A-Za-z0-9_]*(?:\s*,\s*[A-Za-z_][A-Za-z0-9_]*)*)\s*"
    r"(?:=[^;]*)?;"
)
CASE_LABEL = re.compile(r"\bcase\s+\"([^\"]+)\"\s*:")


def discover_csharp(root: Path) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Discover registered C# handler and dispatch-operation records."""
    bridge = root / "ClaudeCodeBridge"
    registry_text = (bridge / "BridgeCommandRegistry.cs").read_text(encoding="utf-8")
    registered = sorted(set(REGISTERED_HANDLER.findall(registry_text)))
    sources = {
        path: path.read_text(encoding="utf-8", errors="replace")
        for path in sorted(bridge.glob("*.cs"))
    }
    type_fields = _csharp_type_fields(sources)
    handlers, operations = [], []
    for handler in registered:
        found_handlers, found_operations = _handler_records(root, handler, sources, type_fields)
        handlers.append(found_handlers)
        operations.extend(found_operations)
    return sorted(handlers, key=lambda item: item["id"]), sorted(
        operations, key=lambda item: item["id"]
    )


def _handler_records(
    root: Path,
    handler: str,
    sources: dict[Path, str],
    type_fields: dict[str, list[str]],
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    matching = [(path, text) for path, text in sources.items() if _declares(text, handler)]
    command_matches = [COMMAND_TYPE.search(text) for _, text in matching]
    command_type = next((match.group(1) for match in command_matches if match), None)
    source_paths = [_relative(path, root) for path, _ in matching]
    record = {
        "id": f"{handler}|{command_type or '<missing>'}",
        "handler": handler,
        "command_type": command_type,
        "sources": source_paths,
    }
    if command_type is None:
        return record, []
    text = "\n".join(item[1] for item in matching)
    fields = _handler_fields(text, type_fields)
    operation_names = _dispatch_operations(text) or [DIRECT_OPERATION]
    operations = [
        {
            "id": f"{command_type}|{operation}",
            "command_type": command_type,
            "operation": None if operation == DIRECT_OPERATION else operation,
            "handler": handler,
            "fields": fields,
            "proof": source_paths,
        }
        for operation in operation_names
    ]
    return record, operations


def _csharp_type_fields(sources: dict[Path, str]) -> dict[str, list[str]]:
    result: dict[str, set[str]] = {}
    for text in sources.values():
        for match in CLASS_DECLARATION.finditer(text):
            body = _block_after(text, match.end())
            if body is None:
                continue
            fields = result.setdefault(match.group(1), set())
            for field_match in PUBLIC_FIELD.finditer(body):
                fields.update(name.strip() for name in field_match.group(1).split(","))
    return {name: sorted(fields) for name, fields in result.items()}


def _handler_fields(text: str, type_fields: dict[str, list[str]]) -> list[str]:
    parameter_types = sorted(set(PARAMETER_TYPE.findall(text)))
    return sorted({field for name in parameter_types for field in type_fields.get(name, [])})


def _dispatch_operations(text: str) -> list[str]:
    operations: set[str] = set()
    position = 0
    while match := re.search(r"\bswitch\s*\(", text[position:]):
        start = position + match.start()
        open_paren = text.find("(", start)
        close_paren = _matching(text, open_paren, "(", ")")
        if close_paren is None:
            break
        header = text[open_paren + 1 : close_paren]
        open_brace = _next_nonspace(text, close_paren + 1)
        close_brace = _switch_close(text, open_brace)
        if close_brace is None:
            position = close_paren + 1
            continue
        if re.search(r"\b(operation|action)\b", header, re.IGNORECASE):
            operations.update(_top_level_cases(text[open_brace + 1 : close_brace]))
        position = close_brace + 1
    return sorted(operations)


def _switch_close(text: str, open_brace: int) -> int | None:
    if open_brace >= len(text) or text[open_brace] != "{":
        return None
    return _matching(text, open_brace, "{", "}")


def _top_level_cases(body: str) -> list[str]:
    values = []
    for match in CASE_LABEL.finditer(body):
        prefix = body[: match.start()]
        if prefix.count("{") == prefix.count("}"):
            values.append(match.group(1))
    return values


def _declares(text: str, name: str) -> bool:
    return any(match.group(1) == name for match in CLASS_DECLARATION.finditer(text))


def _block_after(text: str, position: int) -> str | None:
    open_brace = text.find("{", position)
    if open_brace < 0:
        return None
    close_brace = _matching(text, open_brace, "{", "}")
    return None if close_brace is None else text[open_brace + 1 : close_brace]


def _matching(text: str, start: int, opening: str, closing: str) -> int | None:
    depth, in_string, escaped = 0, False, False
    for index in range(start, len(text)):
        char = text[index]
        if in_string:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
            continue
        if char == '"':
            in_string = True
        elif char == opening:
            depth += 1
        elif char == closing:
            depth -= 1
            if depth == 0:
                return index
    return None


def _next_nonspace(text: str, position: int) -> int:
    while position < len(text) and text[position].isspace():
        position += 1
    return position


def _relative(path: Path, root: Path) -> str:
    return path.relative_to(root).as_posix()
