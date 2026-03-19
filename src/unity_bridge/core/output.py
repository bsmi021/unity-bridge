"""
Output formatting for the Unity Bridge CLI.

Supports three modes:
- json: Compact JSON (default, machine-readable)
- pretty: Indented JSON (human-scannable, still machine-parseable)
- human: Formatted text with domain-specific formatters

All CLI output uses snake_case keys. Translation from the bridge's
camelCase responses happens in _to_snake_case_keys().
"""

from __future__ import annotations

import json
import re
import sys
from typing import Any, Callable

from unity_bridge.core.bridge import CommandResult


class OutputFormatter:
    """Routes output to the correct format based on config.

    Attributes:
        format: One of "json", "pretty", "human".
        color: Whether to use ANSI color codes.
    """

    def __init__(self, format: str = "json", color: bool = True) -> None:
        self.format = format
        self.color = color

    def format_result(
        self,
        result: CommandResult,
        human_formatter: Callable[[Any, bool], str] | None = None,
    ) -> str:
        """Format a CommandResult for output.

        Args:
            result: The command result to format.
            human_formatter: Optional callable(data, color) -> str for human mode.

        Returns:
            Formatted string ready for printing.
        """
        if self.format == "human" and human_formatter and result.success:
            return human_formatter(result.data, self.color)

        data = _result_to_dict(result)

        if self.format == "pretty":
            return json.dumps(data, indent=2, default=str)

        return json.dumps(data, default=str)

    def success(
        self,
        data: Any,
        human_formatter: Callable[[Any, bool], str] | None = None,
    ) -> str:
        """Format a successful result."""
        result = CommandResult(success=True, data=data)
        return self.format_result(result, human_formatter)

    def error(self, message: str, details: dict[str, Any] | None = None) -> str:
        """Format an error message."""
        if self.format == "human":
            prefix = _colorize("ERROR:", "red", self.color)
            text = f"{prefix} {message}"
            if details:
                for key, val in details.items():
                    text += f"\n  {key}: {val}"
            return text

        data: dict[str, Any] = {"success": False, "error": message}
        if details:
            data["details"] = _to_snake_case_keys(details)

        if self.format == "pretty":
            return json.dumps(data, indent=2, default=str)
        return json.dumps(data, default=str)


def print_result(
    result: CommandResult,
    formatter: OutputFormatter,
    human_formatter: Callable[[Any, bool], str] | None = None,
) -> None:
    """Print a CommandResult to stdout/stderr and set exit code.

    Success output goes to stdout. Error messages in human mode go
    to stderr. The exit code is taken from result.exit_code.
    """
    output = formatter.format_result(result, human_formatter)

    if result.success:
        print(output, file=sys.stdout)
    else:
        if formatter.format == "human":
            print(output, file=sys.stderr)
        else:
            print(output, file=sys.stdout)

    if result.exit_code != 0:
        raise SystemExit(result.exit_code)


# ---------------------------------------------------------------------------
# Human formatters for specific command types
# ---------------------------------------------------------------------------

def format_test_results(data: Any, color: bool = True) -> str:
    """Format test run results for human-readable output."""
    if not isinstance(data, dict):
        return str(data)

    lines: list[str] = []
    results = data.get("results") or data.get("testResults") or []

    for test in results:
        name = test.get("testName") or test.get("name", "Unknown")
        status = test.get("result") or test.get("status", "unknown")
        duration = test.get("duration", 0)
        duration_ms = int(float(duration) * 1000) if isinstance(duration, (int, float)) else 0

        if status.lower() in ("passed", "pass"):
            tag = _colorize("PASS", "green", color)
        elif status.lower() in ("failed", "fail"):
            tag = _colorize("FAIL", "red", color)
        else:
            tag = _colorize(status.upper(), "yellow", color)

        lines.append(f"{tag}  {name} ({duration_ms}ms)")

        message = test.get("message") or test.get("output", "")
        if message and status.lower() in ("failed", "fail"):
            for msg_line in message.strip().splitlines()[:5]:
                lines.append(f"  {msg_line}")

    # Summary
    passed = data.get("passed", 0)
    failed = data.get("failed", 0)
    total_ms = data.get("duration", 0)
    if isinstance(total_ms, float):
        total_ms = int(total_ms * 1000)
    lines.append("")
    lines.append(f"Results: {passed} passed, {failed} failed ({total_ms}ms total)")

    return "\n".join(lines)


def format_hierarchy(data: Any, color: bool = True) -> str:
    """Format hierarchy tree for human-readable output."""
    if not isinstance(data, dict):
        return str(data)

    lines: list[str] = []
    scene = data.get("sceneName") or data.get("scene", "Unknown")
    lines.append(f"Scene: {_colorize(scene, 'cyan', color)}")

    children = data.get("children") or data.get("objects") or []
    _format_tree_nodes(children, lines, prefix="", color=color)

    return "\n".join(lines)


def format_console_logs(data: Any, color: bool = True) -> str:
    """Format console log entries for human-readable output."""
    if not isinstance(data, (dict, list)):
        return str(data)

    entries = data if isinstance(data, list) else data.get("entries") or data.get("logs") or []
    lines: list[str] = []

    for entry in entries:
        log_type = entry.get("type") or entry.get("logType", "Log")
        message = entry.get("message", "")

        tag = _log_type_tag(log_type, color)
        first_line, *rest = message.splitlines() if message else [""]
        lines.append(f"{tag} {first_line}")
        for extra in rest[:3]:
            lines.append(f"      {extra}")

    return "\n".join(lines)


def format_snapshot_diff(data: Any, color: bool = True) -> str:
    """Format snapshot diff for human-readable output."""
    if not isinstance(data, dict):
        return str(data)

    lines: list[str] = []
    added = data.get("added", [])
    removed = data.get("removed", [])
    modified = data.get("modified", [])

    if added:
        lines.append(_colorize(f"+ {len(added)} added", "green", color))
        for item in added[:20]:
            name = item if isinstance(item, str) else item.get("name", str(item))
            lines.append(f"  + {name}")

    if removed:
        lines.append(_colorize(f"- {len(removed)} removed", "red", color))
        for item in removed[:20]:
            name = item if isinstance(item, str) else item.get("name", str(item))
            lines.append(f"  - {name}")

    if modified:
        lines.append(_colorize(f"~ {len(modified)} modified", "yellow", color))
        for item in modified[:20]:
            name = item if isinstance(item, str) else item.get("name", str(item))
            lines.append(f"  ~ {name}")

    if not (added or removed or modified):
        lines.append("No differences found.")

    return "\n".join(lines)


def format_diagnostics(data: Any, color: bool = True) -> str:
    """Format diagnostic/status output for human-readable display."""
    if not isinstance(data, dict):
        return str(data)

    healthy = data.get("healthy", False)
    lines: list[str] = []

    if healthy:
        status_str = _colorize("ONLINE", "green", color)
        lines.append(f"Unity Bridge: {status_str}")
        version = data.get("unityVersion") or data.get("unity_version", "")
        scene = data.get("activeScene") or data.get("active_scene", "")
        uptime = _format_uptime(data.get("uptimeSeconds") or data.get("uptime_seconds", 0))
        lines.append(f"  Unity {version} | Scene: {scene} | Uptime: {uptime}")
        hb_age = data.get("heartbeatAgeSeconds") or data.get("heartbeat_age_seconds", 0)
        cmds = data.get("commandsProcessed") or data.get("commands_processed", 0)
        lines.append(f"  Heartbeat: {hb_age:.1f}s ago | Commands processed: {cmds}")
    else:
        status_str = _colorize("OFFLINE", "red", color)
        lines.append(f"Unity Bridge: {status_str}")
        reason = data.get("reason", "Unknown reason")
        lines.append(f"  {reason}")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

_CAMEL_TO_SNAKE_RE = re.compile(r"(?<=[a-z0-9])([A-Z])")


def _to_snake_case(name: str) -> str:
    """Convert a camelCase string to snake_case."""
    return _CAMEL_TO_SNAKE_RE.sub(r"_\1", name).lower()


def _to_snake_case_keys(data: Any) -> Any:
    """Recursively convert all dict keys from camelCase to snake_case."""
    if isinstance(data, dict):
        return {_to_snake_case(k): _to_snake_case_keys(v) for k, v in data.items()}
    if isinstance(data, list):
        return [_to_snake_case_keys(item) for item in data]
    return data


def _result_to_dict(result: CommandResult) -> dict[str, Any]:
    """Convert CommandResult to a snake_case dict for JSON output."""
    d: dict[str, Any] = {"success": result.success}
    if result.data is not None:
        d["data"] = _to_snake_case_keys(result.data)
    if result.error is not None:
        d["error"] = result.error
    if result.command_id is not None:
        d["command_id"] = result.command_id
    if result.execution_time_ms > 0:
        d["execution_time_ms"] = result.execution_time_ms
    if result.exit_code != 0:
        d["exit_code"] = result.exit_code
    if result.cached:
        d["cached"] = True
    return d


_ANSI_COLORS: dict[str, str] = {
    "red": "\033[91m",
    "green": "\033[92m",
    "yellow": "\033[93m",
    "cyan": "\033[96m",
    "reset": "\033[0m",
}


def _colorize(text: str, color: str, enabled: bool = True) -> str:
    """Wrap text in ANSI color codes if enabled."""
    if not enabled or color not in _ANSI_COLORS:
        return text
    return f"{_ANSI_COLORS[color]}{text}{_ANSI_COLORS['reset']}"


def _log_type_tag(log_type: str, color: bool) -> str:
    """Create a colored tag for a console log type."""
    lt = log_type.lower()
    if "error" in lt or "exception" in lt:
        return _colorize("[ERR]", "red", color)
    if "warn" in lt:
        return _colorize("[WRN]", "yellow", color)
    return _colorize("[LOG]", "cyan", color)


def _format_uptime(seconds: int | float) -> str:
    """Format seconds into a human-readable uptime string."""
    s = int(seconds)
    if s < 60:
        return f"{s}s"
    if s < 3600:
        return f"{s // 60}m {s % 60}s"
    hours = s // 3600
    mins = (s % 3600) // 60
    return f"{hours}h {mins}m"


def _format_tree_nodes(
    nodes: list[dict[str, Any]],
    lines: list[str],
    prefix: str,
    color: bool,
) -> None:
    """Recursively format hierarchy tree nodes."""
    for i, node in enumerate(nodes):
        is_last = i == len(nodes) - 1
        connector = "|__ " if is_last else "|-- "
        name = node.get("name", "???")
        components = node.get("components", [])

        comp_str = ""
        if components:
            comp_names = [c if isinstance(c, str) else c.get("type", "?") for c in components]
            comp_str = f" [{', '.join(comp_names)}]"

        lines.append(f"{prefix}{connector}{name}{comp_str}")

        children = node.get("children", [])
        if children:
            child_prefix = prefix + ("    " if is_last else "|   ")
            _format_tree_nodes(children, lines, child_prefix, color)
