"""Diagnostic commands: status, doctor, profiler."""

from __future__ import annotations

import asyncio
import importlib
import os
import platform
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Annotated, Any

import typer

from unity_bridge.core.bridge import CommandResult, DirectBridge

# ---------------------------------------------------------------------------
# Data types
# ---------------------------------------------------------------------------


@dataclass
class DiagnosticCheck:
    """Result of a single diagnostic check."""

    name: str
    passed: bool
    message: str
    suggestion: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Serialise to a plain dict."""
        result: dict[str, Any] = {
            "name": self.name,
            "passed": self.passed,
            "message": self.message,
        }
        if self.suggestion is not None:
            result["suggestion"] = self.suggestion
        return result


# ---------------------------------------------------------------------------
# Core async functions (CLI + MCP)
# ---------------------------------------------------------------------------


async def status(project_root: Path) -> CommandResult:
    """Quick alive/dead check using HealthMonitor.

    Args:
        project_root: Unity project root directory.
    """
    from unity_bridge.core.health import HealthMonitor

    monitor = HealthMonitor(project_root)
    health = monitor.check_health()
    return CommandResult(
        success=health.healthy,
        data=health.to_dict(),
        error=health.reason if not health.healthy else None,
    )


async def doctor(project_root: Path) -> CommandResult:
    """Run the full 9-check diagnostic suite.

    Args:
        project_root: Unity project root directory.
    """
    checks: list[DiagnosticCheck] = [
        _check_project_structure(project_root),
        _check_bridge_installed(project_root),
        _check_bridge_version(project_root),
        _check_heartbeat(project_root),
        _check_directory_permissions(project_root),
        _check_orphaned_files(project_root),
        _check_dependencies(),
        _check_unity_process(),
        _check_version_compatibility(project_root),
    ]

    all_pass = all(c.passed for c in checks)
    return CommandResult(
        success=all_pass,
        data=[c.to_dict() for c in checks],
    )


async def profiler_sample(
    bridge: DirectBridge,
    memory: bool = False,
    rendering: bool = False,
    cpu: bool = False,
    timeout: float = 30.0,
) -> CommandResult:
    """Capture profiler performance metrics.

    Args:
        bridge: Active bridge connection.
        memory: Include memory statistics.
        rendering: Include rendering statistics.
        cpu: Include CPU statistics.
        timeout: Timeout in seconds.
    """
    params: dict[str, object] = {}
    if memory:
        params["includeMemory"] = True
    if rendering:
        params["includeRendering"] = True
    if cpu:
        params["includeCPU"] = True

    return await bridge.send_command_with_retry(
        command_type="profiler-sample",
        parameters=params,
        timeout=timeout,
    )


# ---------------------------------------------------------------------------
# Diagnostic check helpers
# ---------------------------------------------------------------------------


def _check_project_structure(project_root: Path) -> DiagnosticCheck:
    """Verify Assets/ directory exists."""
    assets_dir = project_root / "Assets"
    if assets_dir.is_dir():
        return DiagnosticCheck("Project structure", True, "Assets/ directory found")
    return DiagnosticCheck(
        "Project structure", False,
        f"Assets/ not found at {project_root}",
        "Ensure you are in a Unity project directory.",
    )


def _check_bridge_installed(project_root: Path) -> DiagnosticCheck:
    """Verify C# bridge files are installed."""
    bridge_dir = project_root / "Assets" / "Scripts" / "Editor" / "ClaudeCodeBridge"
    key_file = bridge_dir / "ClaudeUnityBridge.cs"
    if key_file.is_file():
        return DiagnosticCheck(
            "C# bridge installed", True,
            f"Found at {bridge_dir}",
        )
    return DiagnosticCheck(
        "C# bridge installed", False,
        "ClaudeUnityBridge.cs not found",
        "Run `unity-bridge install` to install bridge files.",
    )


def _check_bridge_version(project_root: Path) -> DiagnosticCheck:
    """Check installed bridge version via manifest."""
    import json

    manifest_path = (
        project_root / "Assets" / "Scripts" / "Editor"
        / "ClaudeCodeBridge" / "bridge_manifest.json"
    )
    if not manifest_path.is_file():
        return DiagnosticCheck(
            "Bridge version", False,
            "No manifest found (legacy install?)",
            "Run `unity-bridge install` to update.",
        )
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        version = manifest.get("version", "unknown")
        return DiagnosticCheck("Bridge version", True, f"v{version}")
    except (json.JSONDecodeError, OSError) as exc:
        return DiagnosticCheck("Bridge version", False, f"Error reading manifest: {exc}")


def _check_heartbeat(project_root: Path) -> DiagnosticCheck:
    """Check heartbeat freshness."""
    from unity_bridge.core.health import HealthMonitor

    monitor = HealthMonitor(project_root)
    health = monitor.check_health()
    if health.healthy:
        age = f"{health.heartbeat_age_seconds:.1f}s"
        return DiagnosticCheck("Heartbeat", True, f"Fresh ({age} old)")
    return DiagnosticCheck(
        "Heartbeat", False,
        health.reason or "Heartbeat stale or missing",
        "Ensure Unity Editor is running with the bridge enabled.",
    )


def _check_directory_permissions(project_root: Path) -> DiagnosticCheck:
    """Verify commands/ and responses/ are writable."""
    from unity_bridge.core.project import get_bridge_paths

    paths = get_bridge_paths(project_root)
    issues: list[str] = []
    for label, d in [("commands", paths.commands_dir), ("responses", paths.responses_dir)]:
        if not d.exists():
            issues.append(f"{label}/ missing")
        elif not _is_writable(d):
            issues.append(f"{label}/ not writable")

    if issues:
        return DiagnosticCheck(
            "Directory permissions", False,
            "; ".join(issues),
            "Run `unity-bridge init` to create directories.",
        )
    return DiagnosticCheck(
        "Directory permissions", True,
        "commands/ and responses/ writable",
    )


def _is_writable(directory: Path) -> bool:
    """Test write access to a directory."""
    import tempfile

    try:
        fd, tmp = tempfile.mkstemp(dir=directory)
        os.close(fd)
        Path(tmp).unlink()
        return True
    except OSError:
        return False


def _check_orphaned_files(project_root: Path) -> DiagnosticCheck:
    """Count orphaned command/response files."""
    from unity_bridge.core.project import get_bridge_paths

    paths = get_bridge_paths(project_root)
    count = 0
    for d in [paths.commands_dir, paths.responses_dir]:
        if d.is_dir():
            count += sum(1 for _ in d.glob("*.json"))

    if count > 0:
        return DiagnosticCheck(
            "Orphaned files", True,
            f"{count} stale file(s) found",
            "Run `unity-bridge clean` to remove them.",
        )
    return DiagnosticCheck("Orphaned files", True, "No orphaned files")


def _check_dependencies() -> DiagnosticCheck:
    """Verify key Python packages are importable."""
    missing: list[str] = []
    for pkg in ["typer", "aiofiles"]:
        try:
            importlib.import_module(pkg)
        except ImportError:
            missing.append(pkg)

    if missing:
        return DiagnosticCheck(
            "Python dependencies", False,
            f"Missing: {', '.join(missing)}",
            f"Install with: pip install {' '.join(missing)}",
        )
    return DiagnosticCheck("Python dependencies", True, "All required packages installed")


def _check_unity_process() -> DiagnosticCheck:
    """Check if a Unity Editor process is running."""
    try:
        if sys.platform == "win32":
            out = subprocess.check_output(
                ["tasklist", "/FI", "IMAGENAME eq Unity.exe"],
                text=True, timeout=5,
            )
            if "Unity.exe" in out:
                return DiagnosticCheck("Unity process", True, "Unity.exe is running")
        else:
            out = subprocess.check_output(
                ["pgrep", "-x", "Unity"], text=True, timeout=5,
            )
            if out.strip():
                return DiagnosticCheck("Unity process", True, "Unity process found")
    except (subprocess.SubprocessError, FileNotFoundError):
        pass

    return DiagnosticCheck(
        "Unity process", False,
        "Unity Editor process not detected",
        "Start Unity Editor and open your project.",
    )


def _check_version_compatibility(project_root: Path) -> DiagnosticCheck:
    """Check if installed C# version is compatible with the Python package."""
    import json

    manifest_path = (
        project_root / "Assets" / "Scripts" / "Editor"
        / "ClaudeCodeBridge" / "bridge_manifest.json"
    )
    if not manifest_path.is_file():
        return DiagnosticCheck(
            "Version compatibility", False,
            "No manifest — cannot check compatibility",
        )
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        cs_version = manifest.get("version", "0.0.0")
        from unity_bridge import __version__ as py_version

        cs_major = int(cs_version.split(".")[0])
        py_major = int(py_version.split(".")[0])
        if cs_major == py_major:
            return DiagnosticCheck(
                "Version compatibility", True,
                f"C# v{cs_version} compatible with Python v{py_version}",
            )
        return DiagnosticCheck(
            "Version compatibility", False,
            f"Major version mismatch: C# v{cs_version} vs Python v{py_version}",
            "Run `unity-bridge install` to update the C# bridge.",
        )
    except (json.JSONDecodeError, OSError, ValueError) as exc:
        return DiagnosticCheck("Version compatibility", False, str(exc))


# ---------------------------------------------------------------------------
# Typer CLI wrappers
# ---------------------------------------------------------------------------

diagnostics_app = typer.Typer(name="diagnostics", help="Diagnostic commands.")


@diagnostics_app.command("status")
def status_cli(ctx: typer.Context) -> None:
    """Quick alive/dead check for the Unity Bridge."""
    from unity_bridge.core.output import print_result

    state = ctx.obj
    result = asyncio.run(status(state.project_root))
    print_result(result, state.formatter)


@diagnostics_app.command("doctor")
def doctor_cli(ctx: typer.Context) -> None:
    """Run the full diagnostic suite (9 checks)."""
    from unity_bridge.core.output import print_result

    state = ctx.obj
    result = asyncio.run(doctor(state.project_root))
    print_result(result, state.formatter)


@diagnostics_app.command("profiler")
def profiler_cli(
    ctx: typer.Context,
    memory: Annotated[
        bool, typer.Option("--memory", help="Include memory statistics.")
    ] = False,
    rendering: Annotated[
        bool, typer.Option("--rendering", help="Include rendering statistics.")
    ] = False,
    cpu: Annotated[
        bool, typer.Option("--cpu", help="Include CPU statistics.")
    ] = False,
) -> None:
    """Capture Unity profiler metrics."""
    from unity_bridge.core.output import print_result

    state = ctx.obj
    result = asyncio.run(
        profiler_sample(state.bridge, memory, rendering, cpu)
    )
    print_result(result, state.formatter)
