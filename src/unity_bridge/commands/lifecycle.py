"""Lifecycle commands: install, init, clean, version."""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import platform
import shutil
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Annotated

import typer

from unity_bridge.core.bridge import CommandResult

logger = logging.getLogger("unity_bridge.lifecycle")

# File patterns to copy from the C# bridge source directory.
_BRIDGE_FILE_GLOBS = ("*.cs", "*.cs.meta", "*.md", "*.md.meta")


# ---------------------------------------------------------------------------
# Install helpers
# ---------------------------------------------------------------------------


def _get_bridge_source_dir() -> Path | None:
    """Locate the ClaudeCodeBridge/ source directory relative to the repo root."""
    # Walk up from this file: commands/ -> unity_bridge/ -> src/ -> repo_root
    repo_root = Path(__file__).resolve().parent.parent.parent.parent
    source_dir = repo_root / "ClaudeCodeBridge"
    if source_dir.is_dir() and (source_dir / "ClaudeUnityBridge.cs").is_file():
        return source_dir
    return None


def _compute_file_checksum(file_path: Path) -> str:
    """Return SHA-256 hex digest of a file's contents."""
    h = hashlib.sha256()
    h.update(file_path.read_bytes())
    return h.hexdigest()


def _load_manifest(target_dir: Path) -> dict | None:
    """Load bridge_manifest.json from target_dir, or None if missing/corrupt."""
    manifest_path = target_dir / "bridge_manifest.json"
    if not manifest_path.is_file():
        return None
    try:
        return json.loads(manifest_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def _save_manifest(target_dir: Path, ver: str, files: dict[str, str]) -> None:
    """Write bridge_manifest.json with version, timestamp, and file checksums."""
    manifest = {
        "version": ver,
        "installed_at": datetime.now(timezone.utc).isoformat(),
        "files": files,
    }
    manifest_path = target_dir / "bridge_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")


def _copy_bridge_files(source_dir: Path, target_dir: Path) -> dict[str, str]:
    """Copy bridge files from source to target, returning {name: sha256} map."""
    target_dir.mkdir(parents=True, exist_ok=True)
    checksums: dict[str, str] = {}
    for glob in _BRIDGE_FILE_GLOBS:
        for src_file in source_dir.glob(glob):
            dest = target_dir / src_file.name
            shutil.copy2(src_file, dest)
            checksums[src_file.name] = _compute_file_checksum(dest)
    return checksums


def _get_bridge_version() -> str:
    """Return the current bridge version (matches the package version)."""
    from unity_bridge import __version__
    return __version__


# ---------------------------------------------------------------------------
# Core async functions (CLI + MCP)
# ---------------------------------------------------------------------------


async def install(
    project_root: Path | None = None,
    check: bool = False,
    force: bool = False,
) -> CommandResult:
    """Install or update the C# bridge files.

    Args:
        project_root: Unity project root (auto-detected if None).
        check: If True, report status without making changes.
        force: If True, force reinstall regardless of version.
    """
    from unity_bridge.core.project import find_unity_project_root, get_bridge_paths

    bridge_version = _get_bridge_version()
    root = project_root or find_unity_project_root(Path.cwd())
    if root is None:
        return CommandResult(success=False, error="Unity project not found.")

    target_dir = get_bridge_paths(root).editor_bridge_dir

    if check:
        return _check_install_status(target_dir, bridge_version)

    source_dir = _get_bridge_source_dir()
    if source_dir is None:
        return CommandResult(
            success=False,
            error="ClaudeCodeBridge source directory not found.",
        )

    existing = _load_manifest(target_dir)
    if not force and existing and existing.get("version") == bridge_version:
        return CommandResult(
            success=True,
            data={"action": "up_to_date", "version": bridge_version},
        )

    if force:
        manifest_path = target_dir / "bridge_manifest.json"
        if manifest_path.is_file():
            manifest_path.unlink(missing_ok=True)

    checksums = _copy_bridge_files(source_dir, target_dir)
    _save_manifest(target_dir, bridge_version, checksums)

    action = "update" if existing else "install"
    return CommandResult(
        success=True,
        data={
            "action": action,
            "version": bridge_version,
            "files_copied": len(checksums),
            "target_dir": str(target_dir),
        },
    )


def _check_install_status(target_dir: Path, bridge_version: str) -> CommandResult:
    """Check installation status without making changes."""
    key_file = target_dir / "ClaudeUnityBridge.cs"
    if not key_file.is_file():
        return CommandResult(
            success=True,
            data={"installed": False, "available_version": bridge_version},
        )

    manifest = _load_manifest(target_dir)
    installed_version = manifest.get("version", "unknown") if manifest else "unknown"
    status = "up_to_date" if installed_version == bridge_version else "update_available"

    return CommandResult(
        success=True,
        data={
            "installed": True,
            "installed_version": installed_version,
            "available_version": bridge_version,
            "status": status,
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

    return CommandResult(
        success=True,
        data={
            "cli_version": cli_version,
            "bridge_version": cli_version,
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
