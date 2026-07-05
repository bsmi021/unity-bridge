"""Lifecycle commands: install, init, clean, version."""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import os
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
_SKILL_NAME = "unity-bridge-cli"


# ---------------------------------------------------------------------------
# Install helpers
# ---------------------------------------------------------------------------


def _get_bridge_source_dir() -> Path | None:
    """Locate ClaudeCodeBridge/ from source checkout or installed package."""
    # Walk up from this file: commands/ -> unity_bridge/ -> src/ -> repo_root
    repo_root = Path(__file__).resolve().parent.parent.parent.parent
    source_dir = repo_root / "ClaudeCodeBridge"
    if source_dir.is_dir() and (source_dir / "ClaudeUnityBridge.cs").is_file():
        return source_dir

    bundled_dir = Path(__file__).resolve().parent.parent / "_bundled_bridge" / "ClaudeCodeBridge"
    if bundled_dir.is_dir() and (bundled_dir / "ClaudeUnityBridge.cs").is_file():
        return bundled_dir
    return None


def _get_skill_source_dir() -> Path | None:
    """Locate the bundled unity-bridge-cli skill directory."""
    repo_root = Path(__file__).resolve().parent.parent.parent.parent
    source_dir = repo_root / ".agents" / "skills" / _SKILL_NAME
    if (source_dir / "SKILL.md").is_file():
        return source_dir

    bundled_dir = Path(__file__).resolve().parent.parent / "_bundled_skills" / _SKILL_NAME
    if (bundled_dir / "SKILL.md").is_file():
        return bundled_dir
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
    for name, src_file in _source_bridge_files(source_dir).items():
        dest = target_dir / name
        shutil.copy2(src_file, dest)
        checksums[name] = _compute_file_checksum(dest)
    return checksums


def _source_bridge_files(source_dir: Path) -> dict[str, Path]:
    """Return current bridge source files keyed by target file name."""
    files: dict[str, Path] = {}
    for glob in _BRIDGE_FILE_GLOBS:
        for src_file in source_dir.glob(glob):
            files[src_file.name] = src_file
    return files


def _target_bridge_files(target_dir: Path) -> list[Path]:
    """Return bridge-managed target files that match install globs."""
    files: list[Path] = []
    if not target_dir.is_dir():
        return files
    for glob in _BRIDGE_FILE_GLOBS:
        files.extend(path for path in target_dir.glob(glob) if path.is_file())
    return files


def _obsolete_bridge_files(source_dir: Path, target_dir: Path) -> list[Path]:
    """Return installed bridge files that no longer exist in the source bundle."""
    source_names = set(_source_bridge_files(source_dir))
    return [path for path in _target_bridge_files(target_dir) if path.name not in source_names]


def _prune_obsolete_bridge_files(source_dir: Path, target_dir: Path) -> list[str]:
    """Delete obsolete bridge-managed files from the target directory."""
    pruned: list[str] = []
    for path in _obsolete_bridge_files(source_dir, target_dir):
        try:
            path.unlink()
            pruned.append(str(path))
        except OSError as exc:
            logger.warning("Could not prune obsolete bridge file %s: %s", path, exc)
    return pruned


def _get_skill_target_dir(project_root: Path) -> Path:
    """Return the project-local installation path for the bridge skill."""
    return Path(project_root) / ".agents" / "skills" / _SKILL_NAME


def _get_claude_skill_link_dir(project_root: Path) -> Path:
    """Return the Claude Code skill path -- a link, never a separate copy.

    Codex and GitHub Copilot scan ``.agents/skills`` directly, so only
    Claude Code (which scans ``.claude/skills``) needs this.
    """
    return Path(project_root) / ".claude" / "skills" / _SKILL_NAME


def _is_claude_link_up_to_date(link_dir: Path, skill_target_dir: Path) -> bool:
    """Return True when the Claude Code link already points at the canonical skill dir."""
    from unity_bridge.core.skill_links import is_directory_link

    if not is_directory_link(link_dir):
        return False
    try:
        return link_dir.resolve() == skill_target_dir.resolve()
    except OSError:
        return False


def _claude_link_result(included: bool, link_dir: Path, action: str) -> dict[str, object]:
    """Return normalized Claude Code skill-link data."""
    return {"included": included, "action": action, "path": str(link_dir)}


def _check_claude_link_status(project_root: Path) -> dict[str, object]:
    """Check Claude Code skill-link status without mutating files."""
    from unity_bridge.core.skill_links import is_directory_link

    link_dir = _get_claude_skill_link_dir(project_root)
    skill_target_dir = _get_skill_target_dir(project_root)
    linked = is_directory_link(link_dir) and _is_claude_link_up_to_date(link_dir, skill_target_dir)
    return {"path": str(link_dir), "linked": linked}


def _copy_skill_files(source_dir: Path, target_dir: Path, project_root: Path) -> dict[str, str]:
    """Replace the project-local skill with the bundled skill files."""
    _validate_skill_target(target_dir, project_root)
    if target_dir.exists():
        shutil.rmtree(target_dir)
    target_dir.mkdir(parents=True, exist_ok=True)

    checksums: dict[str, str] = {}
    for src_file in source_dir.rglob("*"):
        if not src_file.is_file():
            continue
        relative = src_file.relative_to(source_dir)
        dest = target_dir / relative
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src_file, dest)
        checksums[relative.as_posix()] = _compute_file_checksum(dest)
    return checksums


def _validate_skill_target(target_dir: Path, project_root: Path) -> None:
    """Ensure recursive replacement is scoped to the intended project skill path."""
    expected = _get_skill_target_dir(project_root).resolve()
    actual = target_dir.resolve()
    if actual != expected:
        raise ValueError(f"Refusing to replace unexpected skill target: {target_dir}")


def _is_skill_up_to_date(source_dir: Path, target_dir: Path) -> bool:
    """Return True when the target skill mirrors the source skill files."""
    if not (target_dir / "SKILL.md").is_file():
        return False

    source_files = {
        path.relative_to(source_dir).as_posix(): path
        for path in source_dir.rglob("*")
        if path.is_file()
    }
    target_files = {
        path.relative_to(target_dir).as_posix(): path
        for path in target_dir.rglob("*")
        if path.is_file()
    }
    if set(source_files) != set(target_files):
        return False
    return all(
        _compute_file_checksum(source) == _compute_file_checksum(target_files[name])
        for name, source in source_files.items()
    )


def _is_bridge_up_to_date(source_dir: Path, target_dir: Path) -> bool:
    """Return True when every current bridge source file matches the target copy.

    Uses checksum comparison rather than the manifest's version string, so a
    file that goes missing or drifts on disk is detected even when the
    installed version string still equals the current version.
    """
    if not (target_dir / "ClaudeUnityBridge.cs").is_file():
        return False

    source_files = _source_bridge_files(source_dir)
    for target_file in _target_bridge_files(target_dir):
        if target_file.name not in source_files:
            return False
    for name, source_file in source_files.items():
        target_file = target_dir / name
        if not target_file.is_file():
            return False
        if _compute_file_checksum(source_file) != _compute_file_checksum(target_file):
            return False
    return True


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
    include_claude: bool = False,
) -> CommandResult:
    """Install or update the C# bridge files.

    Args:
        project_root: Unity project root (auto-detected if None).
        check: If True, report status without making changes.
        force: If True, force reinstall regardless of version.
        include_claude: If True, additionally link ``.claude/skills/<name>``
            to the canonical ``.agents/skills/<name>`` directory for Claude
            Code, which (unlike Codex and GitHub Copilot) does not scan
            ``.agents/skills`` natively.
    """
    from unity_bridge.core.project import find_unity_project_root, get_bridge_paths
    from unity_bridge.core.skill_links import SkillLinkError, create_directory_link

    bridge_version = _get_bridge_version()
    root = project_root or find_unity_project_root(Path.cwd())
    if root is None:
        return CommandResult(success=False, error="Unity project not found.")

    target_dir = get_bridge_paths(root).editor_bridge_dir
    skill_target_dir = _get_skill_target_dir(root)
    claude_link_dir = _get_claude_skill_link_dir(root)
    skill_source_dir = _get_skill_source_dir()
    source_dir = _get_bridge_source_dir()

    if check:
        return _check_install_status(target_dir, bridge_version, root, skill_source_dir, source_dir)

    if source_dir is None:
        return CommandResult(
            success=False,
            error="ClaudeCodeBridge source directory not found.",
        )
    if skill_source_dir is None:
        return CommandResult(
            success=False,
            error="unity-bridge-cli skill source directory not found.",
        )

    existing = _load_manifest(target_dir)
    bridge_up_to_date = existing is not None and _is_bridge_up_to_date(source_dir, target_dir)
    skill_had_existing = (skill_target_dir / "SKILL.md").is_file()
    skill_up_to_date = _is_skill_up_to_date(skill_source_dir, skill_target_dir)
    claude_link_up_to_date = not include_claude or _is_claude_link_up_to_date(
        claude_link_dir, skill_target_dir
    )
    if not force and bridge_up_to_date and skill_up_to_date and claude_link_up_to_date:
        return CommandResult(
            success=True,
            data={
                "action": "up_to_date",
                "version": bridge_version,
                "skill": _skill_result("up_to_date", skill_target_dir, 0),
                "claude_link": _claude_link_result(
                    include_claude, claude_link_dir, "up_to_date" if include_claude else "skipped"
                ),
            },
        )

    if force:
        manifest_path = target_dir / "bridge_manifest.json"
        if manifest_path.is_file():
            manifest_path.unlink(missing_ok=True)

    checksums: dict[str, str] = {}
    pruned_bridge_files: list[str] = []
    if force or not bridge_up_to_date:
        pruned_bridge_files = _prune_obsolete_bridge_files(source_dir, target_dir)
        checksums = _copy_bridge_files(source_dir, target_dir)
        _save_manifest(target_dir, bridge_version, checksums)

    skill_checksums: dict[str, str] = {}
    if force or not skill_up_to_date:
        skill_checksums = _copy_skill_files(skill_source_dir, skill_target_dir, root)

    claude_link_action = "skipped"
    if include_claude:
        try:
            claude_link_action = create_directory_link(claude_link_dir, skill_target_dir)
        except SkillLinkError as exc:
            return CommandResult(
                success=False,
                error=(
                    "Bridge and skill files installed, but could not link "
                    f".claude/skills/{_SKILL_NAME}: {exc}"
                ),
            )

    action = _install_action(existing is not None, bool(checksums), bool(skill_checksums))
    skill_action = "up_to_date"
    if skill_checksums:
        skill_action = "update" if skill_had_existing else "install"
    return CommandResult(
        success=True,
        data={
            "action": action,
            "version": bridge_version,
            "files_copied": len(checksums),
            "files_pruned": len(pruned_bridge_files),
            "target_dir": str(target_dir),
            "skill": _skill_result(skill_action, skill_target_dir, len(skill_checksums)),
            "claude_link": _claude_link_result(include_claude, claude_link_dir, claude_link_action),
        },
    )


def _install_action(had_existing: bool, copied_bridge: bool, copied_skill: bool) -> str:
    """Resolve the user-facing aggregate install action."""
    if not copied_bridge and not copied_skill:
        return "up_to_date"
    return "update" if had_existing else "install"


def _skill_result(action: str, target_dir: Path, files_copied: int) -> dict[str, object]:
    """Return normalized skill install data."""
    return {
        "name": _SKILL_NAME,
        "action": action,
        "files_copied": files_copied,
        "target_dir": str(target_dir),
    }


def _check_install_status(
    target_dir: Path,
    bridge_version: str,
    project_root: Path,
    skill_source_dir: Path | None,
    source_dir: Path | None = None,
) -> CommandResult:
    """Check installation status without making changes."""
    key_file = target_dir / "ClaudeUnityBridge.cs"
    skill_status = _check_skill_status(project_root, skill_source_dir)
    if not key_file.is_file():
        return CommandResult(
            success=True,
            data={
                "installed": False,
                "available_version": bridge_version,
                "skill": skill_status,
            },
        )

    manifest = _load_manifest(target_dir)
    installed_version = manifest.get("version", "unknown") if manifest else "unknown"
    if source_dir is not None:
        up_to_date = _is_bridge_up_to_date(source_dir, target_dir)
    else:
        # Source unavailable (e.g. bundled-only install) — fall back to the
        # weaker version-string comparison since files can't be checksummed.
        up_to_date = installed_version == bridge_version
    status = "up_to_date" if up_to_date else "update_available"

    return CommandResult(
        success=True,
        data={
            "installed": True,
            "installed_version": installed_version,
            "available_version": bridge_version,
            "status": status,
            "skill": skill_status,
        },
    )


def _check_skill_status(project_root: Path, skill_source_dir: Path | None) -> dict[str, object]:
    """Check project-local skill installation status without mutating files."""
    target_dir = _get_skill_target_dir(project_root)
    installed = (target_dir / "SKILL.md").is_file()
    if skill_source_dir is None:
        status = "source_missing" if installed else "not_installed"
    elif not installed:
        status = "not_installed"
    else:
        status = (
            "up_to_date"
            if _is_skill_up_to_date(skill_source_dir, target_dir)
            else "update_available"
        )
    return {
        "name": _SKILL_NAME,
        "installed": installed,
        "status": status,
        "target_dir": str(target_dir),
        "claude_link": _check_claude_link_status(project_root),
    }


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


def _cleanup_files_by_age(
    directories: list[Path],
    pattern: str,
    cutoff: datetime,
    delete_all: bool,
    dry_run: bool,
    protected_paths: set[str] | None = None,
) -> tuple[list[str], list[str]]:
    """Delete files matching a pattern when they are stale enough."""
    deleted: list[str] = []
    skipped: list[str] = []
    protected_paths = protected_paths or set()
    for directory in directories:
        if not directory.is_dir():
            continue
        for path in directory.glob(pattern):
            if _path_key(path) in protected_paths:
                skipped.append(str(path))
                continue
            try:
                file_mtime = datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc)
            except OSError:
                skipped.append(str(path))
                continue
            if not delete_all and file_mtime >= cutoff:
                skipped.append(str(path))
                continue
            if dry_run:
                deleted.append(str(path))
                continue
            try:
                path.unlink()
                deleted.append(str(path))
            except OSError:
                skipped.append(str(path))
    return deleted, skipped


def _path_key(path: Path) -> str:
    """Return a normalized path key for cross-process ledger path comparison."""
    try:
        resolved = path.resolve(strict=False)
    except OSError:
        resolved = path.absolute()
    return os.path.normcase(str(resolved))


def _active_operation_file_keys(operation_store: object) -> set[str]:
    """Return command/response path keys referenced by non-terminal operations."""
    protected: set[str] = set()
    for record in operation_store.list_records(include_terminal=False, limit=10_000):
        for raw_path in (record.command_path, record.response_path):
            if raw_path:
                protected.add(_path_key(Path(raw_path)))
    return protected


async def clean(
    project_root: Path,
    age_minutes: int = 5,
    all_files: bool = False,
    dry_run: bool = False,
) -> CommandResult:
    """Remove orphaned command/response files, stale temp files, and old terminal operations.

    Args:
        project_root: Unity project root directory.
        age_minutes: Delete files older than this many minutes.
        all_files: If True, delete all files regardless of age.
        dry_run: If True, list files that would be deleted without deleting.
    """
    from unity_bridge.core.project import get_bridge_paths
    from unity_bridge.core.operation import OperationStore

    paths = get_bridge_paths(project_root)
    operation_store = OperationStore(project_root)
    effective_age = 0 if all_files else age_minutes
    cutoff = datetime.now(timezone.utc) - timedelta(minutes=effective_age)
    delete_all = effective_age == 0
    protected_paths = _active_operation_file_keys(operation_store)

    deleted, skipped = _cleanup_files_by_age(
        [paths.commands_dir, paths.responses_dir],
        "*.json",
        cutoff,
        delete_all,
        dry_run,
        protected_paths,
    )
    temp_deleted, temp_skipped = _cleanup_files_by_age(
        [paths.commands_dir, paths.responses_dir, operation_store.operations_path],
        "*.tmp",
        cutoff,
        delete_all,
        dry_run,
    )
    deleted.extend(temp_deleted)
    skipped.extend(temp_skipped)

    operation_deleted, operation_skipped = operation_store.cleanup_terminal(
        older_than=cutoff,
        dry_run=dry_run,
    )
    deleted.extend(operation_deleted)
    skipped.extend(operation_skipped)

    # Reap response files orphaned by timed-out/terminal operations (B5).
    if not dry_run:
        from unity_bridge.core.bridge import DirectBridge

        deleted.extend(DirectBridge(project_root).reconcile_orphans())

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
    include_claude: Annotated[
        bool,
        typer.Option(
            "--include-claude",
            help=(
                "Also link .claude/skills/unity-bridge-cli to the canonical "
                ".agents/skills copy, for Claude Code. Codex and GitHub "
                "Copilot need no extra step -- both read .agents/skills directly."
            ),
        ),
    ] = False,
) -> None:
    """Install or update the C# bridge files."""
    from unity_bridge.core.output import print_result

    effective_root = project or (ctx.obj.config.project_root if ctx.obj else None)
    result = asyncio.run(install(effective_root, check, force, include_claude))
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
    """Remove orphaned command/response files, stale temp files, and old terminal operations."""
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
