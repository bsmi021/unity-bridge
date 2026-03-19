"""Lifecycle commands: install, init, clean, version."""

from __future__ import annotations

import asyncio
import platform
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Annotated, Any

import typer

from unity_bridge.core.bridge import CommandResult

# ---------------------------------------------------------------------------
# Core async functions (CLI + MCP)
# ---------------------------------------------------------------------------


async def install(
    project_root: Path | None = None,
    check: bool = False,
    force: bool = False,
) -> CommandResult:
    """Install or update the C# bridge files.

    Wraps the logic from ``install_bridge.py``.

    Args:
        project_root: Unity project root (auto-detected if None).
        check: If True, report status without making changes.
        force: If True, force reinstall regardless of version.
    """
    # Import the installer lazily to avoid hard dependency at import time
    try:
        from install_bridge import (
            install_unity_bridge,
            find_unity_project_root,
            load_installed_manifest,
            compare_versions,
            BRIDGE_VERSION,
        )
    except ImportError:
        return CommandResult(
            success=False,
            error="install_bridge module not found. Ensure it is on the Python path.",
        )

    if check:
        return _check_install_status(
            project_root, find_unity_project_root, load_installed_manifest,
            compare_versions, BRIDGE_VERSION,
        )

    if force and project_root is not None:
        # Remove manifest to force reinstall
        target = (
            project_root / "Assets" / "Scripts" / "Editor"
            / "ClaudeCodeBridge" / "bridge_manifest.json"
        )
        if target.is_file():
            target.unlink(missing_ok=True)

    result = install_unity_bridge(project_root)
    return CommandResult(
        success=result.get("success", False),
        data=result,
        error=result.get("error"),
    )


def _check_install_status(
    project_root: Path | None,
    find_root: Any,
    load_manifest: Any,
    compare_ver: Any,
    bridge_version: str,
) -> CommandResult:
    """Check installation status without making changes."""
    root = project_root or find_root(Path.cwd())
    if root is None:
        return CommandResult(success=False, error="Unity project not found.")

    target_dir = root / "Assets" / "Scripts" / "Editor" / "ClaudeCodeBridge"
    key_file = target_dir / "ClaudeUnityBridge.cs"
    if not key_file.is_file():
        return CommandResult(
            success=True,
            data={"installed": False, "available_version": bridge_version},
        )

    manifest = load_manifest(target_dir)
    installed_version = manifest.get("version", "unknown") if manifest else "unknown"
    comparison = compare_ver(installed_version, bridge_version)

    status_text = "up_to_date" if comparison == 0 else (
        "update_available" if comparison < 0 else "newer_than_source"
    )
    return CommandResult(
        success=True,
        data={
            "installed": True,
            "installed_version": installed_version,
            "available_version": bridge_version,
            "status": status_text,
        },
    )


async def init(project_root: Path) -> CommandResult:
    """Create the ``.claude/unity/`` directory structure.

    Args:
        project_root: Unity project root directory.
    """
    from unity_bridge.core.project import get_bridge_paths

    paths = get_bridge_paths(project_root)
    created: list[str] = []
    for name, path in [
        ("commands", paths.commands_dir),
        ("responses", paths.responses_dir),
    ]:
        if not path.exists():
            path.mkdir(parents=True, exist_ok=True)
            created.append(name)

    return CommandResult(
        success=True,
        data={"created": created, "project_root": str(project_root)},
    )


async def clean(
    project_root: Path,
    age_minutes: int = 5,
    all_files: bool = False,
    dry_run: bool = False,
) -> CommandResult:
    """Remove orphaned command/response files.

    Args:
        project_root: Unity project root directory.
        age_minutes: Delete files older than this many minutes.
        all_files: If True, delete all files regardless of age.
        dry_run: If True, list files that would be deleted without deleting.
    """
    from unity_bridge.core.project import get_bridge_paths

    paths = get_bridge_paths(project_root)
    effective_age = 0 if all_files else age_minutes
    cutoff = datetime.now(timezone.utc) - timedelta(minutes=effective_age)

    deleted: list[str] = []
    skipped: list[str] = []

    for directory in [paths.commands_dir, paths.responses_dir]:
        if not directory.is_dir():
            continue
        for f in directory.glob("*.json"):
            file_mtime = datetime.fromtimestamp(f.stat().st_mtime, tz=timezone.utc)
            if effective_age == 0 or file_mtime < cutoff:
                if dry_run:
                    deleted.append(str(f))
                else:
                    try:
                        f.unlink()
                        deleted.append(str(f))
                    except OSError:
                        skipped.append(str(f))
            else:
                skipped.append(str(f))

    return CommandResult(
        success=True,
        data={
            "deleted": len(deleted),
            "skipped": len(skipped),
            "dry_run": dry_run,
            "files": deleted,
        },
    )


async def version() -> CommandResult:
    """Return CLI, bridge, and Python version information."""
    from unity_bridge import __version__ as cli_version

    bridge_ver = "unknown"
    try:
        from install_bridge import BRIDGE_VERSION
        bridge_ver = BRIDGE_VERSION
    except ImportError:
        pass

    return CommandResult(
        success=True,
        data={
            "cli_version": cli_version,
            "bridge_version": bridge_ver,
            "python_version": platform.python_version(),
            "platform": sys.platform,
        },
    )


# ---------------------------------------------------------------------------
# Typer CLI wrappers
# ---------------------------------------------------------------------------

lifecycle_app = typer.Typer(name="lifecycle", help="Bridge lifecycle commands.")


@lifecycle_app.command("install")
def install_cli(
    ctx: typer.Context,
    project: Annotated[
        Path | None,
        typer.Option("--project", help="Unity project root path."),
    ] = None,
    check: Annotated[
        bool,
        typer.Option("--check", help="Check status without making changes."),
    ] = False,
    force: Annotated[
        bool,
        typer.Option("--force", help="Force reinstall."),
    ] = False,
) -> None:
    """Install or update the C# bridge files."""
    from unity_bridge.core.output import print_result

    effective_root = project or (ctx.obj.config.project_root if ctx.obj else None)
    result = asyncio.run(install(effective_root, check, force))
    print_result(result, ctx.obj.formatter)


@lifecycle_app.command("init")
def init_cli(
    ctx: typer.Context,
    project: Annotated[
        Path | None,
        typer.Option("--project", help="Unity project root path."),
    ] = None,
) -> None:
    """Create the .claude/unity/ directory structure."""
    from unity_bridge.core.output import print_result

    state = ctx.obj
    root = project or state.project_root
    result = asyncio.run(init(root))
    print_result(result, state.formatter)


@lifecycle_app.command("clean")
def clean_cli(
    ctx: typer.Context,
    age: Annotated[
        int,
        typer.Option("--age", help="Delete files older than N minutes."),
    ] = 5,
    all_files: Annotated[
        bool,
        typer.Option("--all", help="Delete all orphaned files."),
    ] = False,
    dry_run: Annotated[
        bool,
        typer.Option("--dry-run", help="Show what would be deleted."),
    ] = False,
) -> None:
    """Remove orphaned command/response files."""
    from unity_bridge.core.output import print_result

    state = ctx.obj
    root = state.project_root
    result = asyncio.run(clean(root, age, all_files, dry_run))
    print_result(result, state.formatter)


@lifecycle_app.command("version")
def version_cli(ctx: typer.Context) -> None:
    """Show CLI, bridge, and Python version information."""
    from unity_bridge.core.output import print_result

    result = asyncio.run(version())
    print_result(result, ctx.obj.formatter)
