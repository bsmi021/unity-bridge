"""Workflow commands: tdd, snapshot save/diff, test watch."""

from __future__ import annotations

import asyncio
import copy
import json
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Annotated, Any

import typer

from unity_bridge.core.bridge import CommandResult, DirectBridge

# ---------------------------------------------------------------------------
# Data types
# ---------------------------------------------------------------------------


@dataclass
class HierarchyDiff:
    """Result of comparing two hierarchy snapshots."""

    added: list[str]
    removed: list[str]
    modified: list[dict[str, Any]]


# ---------------------------------------------------------------------------
# Core async functions (CLI + MCP)
# ---------------------------------------------------------------------------


async def tdd(
    bridge: DirectBridge,
    platform: str = "EditMode",
    filter_pattern: str | None = None,
    strict: bool = False,
) -> CommandResult:
    """TDD workflow: clear -> compile -> test -> read console on failure."""
    steps: list[dict[str, object]] = []

    clear_result = await bridge.send_command("clear-console", timeout=5.0)
    steps.append({"step": "clear-console", "success": clear_result.success})

    compile_result = await bridge.send_command(
        "compile", {"waitForCompletion": True}, timeout=120.0,
    )
    steps.append({"step": "compile", "success": compile_result.success})
    if not compile_result.success:
        return _fail(steps, "compile", compile_result.data, "Compilation failed")
    if strict and _has_warnings(compile_result.data):
        return _fail(steps, "compile", compile_result.data, "Compilation has warnings (strict mode)")

    test_params: dict[str, object] = {"testPlatform": platform}
    if filter_pattern:
        test_params["testFilter"] = filter_pattern
    test_result = await bridge.send_command("run-tests", test_params, timeout=300.0)
    steps.append({"step": "run-tests", "success": test_result.success})

    if not test_result.success:
        console_result = await bridge.send_command(
            "read-console",
            {"logTypes": ["Error"], "maxEntries": 20, "maxStackTraceLines": 3},
            timeout=10.0,
        )
        steps.append({"step": "read-console", "success": console_result.success})
        return CommandResult(
            success=False,
            data={"steps": steps, "test_results": test_result.data, "console": console_result.data},
            error="Tests failed",
        )

    return CommandResult(success=True, data={"steps": steps, "test_results": test_result.data})


async def snapshot_save(
    bridge: DirectBridge,
    output_file: Path,
    depth: int = 5,
    max_objects: int = 1000,
    root: str | None = None,
) -> CommandResult:
    """Save a scene state snapshot to a JSON file.

    Args:
        bridge: Active bridge connection.
        output_file: Path to save the snapshot.
        depth: Maximum hierarchy depth.
        max_objects: Truncate after this many objects.
        root: Optional root path to snapshot from.
    """
    params: dict[str, object] = {"maxDepth": depth, "includeInactive": True}
    if root is not None:
        params["rootPath"] = root

    hierarchy_result = await bridge.send_command("query-hierarchy", params)
    if not hierarchy_result.success:
        return hierarchy_result

    obj_count = count_objects(hierarchy_result.data or {})
    data = hierarchy_result.data
    if obj_count > max_objects and data is not None:
        data = truncate_hierarchy(data, max_objects)

    snapshot = {
        "version": 1,
        "timestamp": datetime.now(timezone.utc).isoformat() + "Z",
        "project_root": str(bridge.project_root),
        "hierarchy": data,
    }

    output_file.write_text(json.dumps(snapshot, indent=2), encoding="utf-8")
    return CommandResult(
        success=True,
        data={"file": str(output_file), "objects": count_objects(data or {})},
    )


async def snapshot_diff(file1: Path, file2: Path) -> CommandResult:
    """Compare two scene snapshots.

    Args:
        file1: Path to the first snapshot.
        file2: Path to the second snapshot.
    """
    snap1 = json.loads(file1.read_text(encoding="utf-8"))
    snap2 = json.loads(file2.read_text(encoding="utf-8"))

    diffs = compute_hierarchy_diff(snap1["hierarchy"], snap2["hierarchy"])
    return CommandResult(
        success=True,
        data={"added": diffs.added, "removed": diffs.removed, "modified": diffs.modified},
    )


async def test_watch(
    bridge: DirectBridge,
    platform: str = "EditMode",
    filter_pattern: str | None = None,
    watch_path: Path | None = None,
) -> None:
    """Watch for .cs file changes and re-run TDD workflow.

    Requires the ``watchfiles`` package.

    Args:
        bridge: Active bridge connection.
        platform: Test platform.
        filter_pattern: Optional test name filter.
        watch_path: Directory to watch (defaults to Assets/).
    """
    try:
        from watchfiles import awatch
    except ImportError:
        raise typer.BadParameter(
            "watchfiles package required for test watch. "
            "Install with: pip install unity-bridge[watch]"
        )

    path = watch_path or bridge.project_root / "Assets"
    sys.stdout.write(f"Watching {path} for .cs file changes...\n")
    sys.stdout.flush()

    async for changes in awatch(path):
        cs_changes = [c for c in changes if c[1].endswith(".cs")]
        if cs_changes:
            changed_files = [Path(c[1]).name for c in cs_changes]
            sys.stdout.write(f"\nChanged: {', '.join(changed_files)}\n")
            sys.stdout.flush()
            result = await tdd(bridge, platform, filter_pattern)
            _print_tdd_summary(result)


# ---------------------------------------------------------------------------
# Hierarchy helpers
# ---------------------------------------------------------------------------


def count_objects(hierarchy: dict[str, Any]) -> int:
    """Recursively count GameObjects in a hierarchy tree."""
    count = 0
    nodes = hierarchy.get("children", hierarchy.get("roots", []))
    for node in nodes:
        count += 1
        count += count_objects(node)
    return count


def truncate_hierarchy(hierarchy: dict[str, Any], max_objects: int) -> dict[str, Any]:
    """Breadth-first truncation of hierarchy to *max_objects*."""
    result = copy.deepcopy(hierarchy)
    seen = 0
    queue = result.get("children", result.get("roots", []))
    for node in queue:
        seen += 1
        if seen >= max_objects:
            remaining = count_objects(node)
            node["children"] = [{"name": "... truncated ...", "truncated_count": remaining}]
            break
        queue.extend(node.get("children", []))
    return result


def _collect_paths(node: dict[str, Any], prefix: str = "") -> dict[str, dict[str, Any]]:
    """Flatten hierarchy into ``{path: node_data}``."""
    path = f"{prefix}/{node['name']}" if prefix else node["name"]
    result: dict[str, dict[str, Any]] = {path: node}
    for child in node.get("children", []):
        result.update(_collect_paths(child, path))
    return result


def _normalize_components(components: list) -> set[str]:
    """Convert component list (strings or dicts) to a set of type names."""
    result = set()
    for c in components:
        if isinstance(c, str):
            result.add(c)
        elif isinstance(c, dict):
            result.add(c.get("type", str(c)))
        else:
            result.add(str(c))
    return result


def compute_hierarchy_diff(
    hierarchy1: dict[str, Any],
    hierarchy2: dict[str, Any],
) -> HierarchyDiff:
    """Compare two hierarchy trees by flattening to path maps."""
    paths1: dict[str, dict[str, Any]] = {}
    for root in hierarchy1.get("children", hierarchy1.get("roots", [])):
        paths1.update(_collect_paths(root))

    paths2: dict[str, dict[str, Any]] = {}
    for root in hierarchy2.get("children", hierarchy2.get("roots", [])):
        paths2.update(_collect_paths(root))

    added = sorted(set(paths2.keys()) - set(paths1.keys()))
    removed = sorted(set(paths1.keys()) - set(paths2.keys()))

    modified: list[dict[str, Any]] = []
    for p in sorted(set(paths1.keys()) & set(paths2.keys())):
        comps1 = _normalize_components(paths1[p].get("components", []))
        comps2 = _normalize_components(paths2[p].get("components", []))
        if comps1 != comps2:
            modified.append({
                "path": p,
                "components_added": sorted(comps2 - comps1),
                "components_removed": sorted(comps1 - comps2),
            })

    return HierarchyDiff(added=added, removed=removed, modified=modified)


def _fail(
    steps: list[dict[str, object]], at: str, data: Any, error: str,
) -> CommandResult:
    """Build a failure result for the TDD workflow."""
    return CommandResult(
        success=False,
        data={"steps": steps, "failed_at": at, "details": data},
        error=error,
    )


def _has_warnings(data: Any) -> bool:
    """Check if compile result data contains warnings."""
    if isinstance(data, dict):
        return bool(data.get("warnings"))
    return False


def _print_tdd_summary(result: CommandResult) -> None:
    """Print a brief summary of a TDD run."""
    status = "PASS" if result.success else "FAIL"
    sys.stdout.write(f"TDD: {status}")
    if result.error:
        sys.stdout.write(f" — {result.error}")
    sys.stdout.write("\n")
    sys.stdout.flush()


# ---------------------------------------------------------------------------
# Typer CLI wrappers
# ---------------------------------------------------------------------------

workflow_app = typer.Typer(name="workflow", help="Developer workflow commands.")
snapshot_app = typer.Typer(name="snapshot", help="Scene snapshot commands.")


@workflow_app.command("tdd")
def tdd_cli(
    ctx: typer.Context,
    platform: Annotated[
        str,
        typer.Option("--platform", "-P", help="Test platform: EditMode or PlayMode."),
    ] = "EditMode",
    filter_pattern: Annotated[
        str | None,
        typer.Option("--filter", "-f", help="Test name filter."),
    ] = None,
    strict: Annotated[
        bool,
        typer.Option("--strict", help="Treat warnings as failures."),
    ] = False,
) -> None:
    """Run TDD workflow: clear -> compile -> test -> console."""
    from unity_bridge.core.output import print_result

    state = ctx.obj
    result = asyncio.run(tdd(state.bridge, platform, filter_pattern, strict))
    print_result(result, state.formatter)


@snapshot_app.command("save")
def snapshot_save_cli(
    ctx: typer.Context,
    file: Annotated[
        Path, typer.Argument(help="Output file path for the snapshot.")
    ],
    depth: Annotated[
        int,
        typer.Option("--depth", "-d", help="Maximum hierarchy depth."),
    ] = 5,
    max_objects: Annotated[
        int,
        typer.Option("--max-objects", help="Truncate after N objects."),
    ] = 1000,
    root: Annotated[
        str | None,
        typer.Option("--root", "-r", help="Root GameObject path."),
    ] = None,
) -> None:
    """Save a scene state snapshot to a JSON file."""
    from unity_bridge.core.output import print_result

    state = ctx.obj
    result = asyncio.run(
        snapshot_save(state.bridge, file, depth, max_objects, root)
    )
    print_result(result, state.formatter)


@snapshot_app.command("diff")
def snapshot_diff_cli(
    ctx: typer.Context,
    file1: Annotated[Path, typer.Argument(help="First snapshot file.")],
    file2: Annotated[Path, typer.Argument(help="Second snapshot file.")],
) -> None:
    """Compare two scene snapshots."""
    from unity_bridge.core.output import print_result

    state = ctx.obj
    result = asyncio.run(snapshot_diff(file1, file2))
    print_result(result, state.formatter)


@workflow_app.command("test-watch")
def test_watch_cli(
    ctx: typer.Context,
    platform: Annotated[
        str,
        typer.Option("--platform", "-P", help="Test platform: EditMode or PlayMode."),
    ] = "EditMode",
    filter_pattern: Annotated[
        str | None,
        typer.Option("--filter", "-f", help="Test name filter."),
    ] = None,
    path: Annotated[
        Path | None,
        typer.Option("--path", help="Directory to watch for .cs changes."),
    ] = None,
) -> None:
    """Watch for .cs file changes and re-run tests (Ctrl+C to stop)."""
    state = ctx.obj
    try:
        asyncio.run(
            test_watch(state.bridge, platform, filter_pattern, path)
        )
    except (KeyboardInterrupt, SystemExit):
        pass
