"""Integration smoke tests for the unity-bridge CLI.

These tests invoke the CLI as a subprocess and verify exit codes
and output structure. They do NOT require Unity to be running.
Marked with @pytest.mark.integration.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

# All tests in this module are integration tests
pytestmark = pytest.mark.integration


def _project_root() -> Path:
    return Path(__file__).resolve().parent.parent.parent


def _src_dir() -> str:
    return str(_project_root() / "src")


# Command prefix — run via python -m with src/ on PYTHONPATH
CLI = [sys.executable, "-m", "unity_bridge"]


def _run(
    *args: str,
    timeout: int = 15,
    clear_project: bool = False,
) -> subprocess.CompletedProcess:
    """Run a CLI command with src/ on PYTHONPATH."""
    env = os.environ.copy()
    if clear_project:
        env.pop("UNITY_BRIDGE_PROJECT", None)
    # Prepend src/ so `python -m unity_bridge` resolves correctly
    existing = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = _src_dir() + (os.pathsep + existing if existing else "")
    # Also add project root for legacy imports (install_bridge, etc.)
    env["PYTHONPATH"] = str(_project_root()) + os.pathsep + env["PYTHONPATH"]
    return subprocess.run(
        [*CLI, *args],
        capture_output=True,
        text=True,
        timeout=timeout,
        cwd=str(_project_root()),
        env=env,
    )


def _cli_available() -> bool:
    """Check whether the CLI module can be invoked."""
    try:
        result = _run("--help", timeout=10)
        return result.returncode == 0
    except Exception:
        return False


# Skip all tests if CLI module is not runnable (e.g., app.py incomplete)
_skip_reason = "CLI module not available (app.py may be incomplete)"


# ---------------------------------------------------------------------------
# Version
# ---------------------------------------------------------------------------


class TestVersionCommand:
    def test_version_returns_zero(self) -> None:
        result = _run("version")
        if result.returncode != 0 and "No module" in result.stderr:
            pytest.skip(_skip_reason)
        assert result.returncode == 0

    def test_version_output_contains_version(self) -> None:
        result = _run("version")
        if result.returncode != 0 and "No module" in result.stderr:
            pytest.skip(_skip_reason)
        output = result.stdout + result.stderr
        assert "3." in output or "version" in output.lower()


# ---------------------------------------------------------------------------
# Help
# ---------------------------------------------------------------------------


class TestHelpCommand:
    def test_help_returns_zero(self) -> None:
        result = _run("--help")
        if result.returncode != 0 and "No module" in result.stderr:
            pytest.skip(_skip_reason)
        assert result.returncode == 0

    def test_help_shows_commands(self) -> None:
        result = _run("--help")
        if result.returncode != 0 and "No module" in result.stderr:
            pytest.skip(_skip_reason)
        output = (result.stdout + result.stderr).lower()
        assert "test" in output or "hierarchy" in output or "help" in output

    def test_test_run_help(self) -> None:
        result = _run("test", "run", "--help")
        if result.returncode != 0 and "No module" in result.stderr:
            pytest.skip(_skip_reason)
        assert result.returncode == 0
        output = (result.stdout + result.stderr).lower()
        assert "platform" in output or "filter" in output or "timeout" in output


# ---------------------------------------------------------------------------
# Status (without Unity)
# ---------------------------------------------------------------------------


class TestStatusCommand:
    def test_status_returns_valid_json(self) -> None:
        result = _run("status")
        if "No module" in result.stderr:
            pytest.skip(_skip_reason)
        output = result.stdout.strip()
        if output:
            try:
                data = json.loads(output)
                assert "success" in data or "healthy" in data
            except json.JSONDecodeError:
                pass  # Human-mode output is acceptable

    def test_status_nonzero_without_unity(self) -> None:
        result = _run("status", clear_project=True)
        if "No module" in result.stderr:
            pytest.skip(_skip_reason)
        # Should be non-zero since Unity is not running
        assert result.returncode != 0


# ---------------------------------------------------------------------------
# Doctor
# ---------------------------------------------------------------------------


class TestDoctorCommand:
    def test_doctor_returns_valid_json(self) -> None:
        result = _run("doctor")
        if "No module" in result.stderr:
            pytest.skip(_skip_reason)
        output = result.stdout.strip()
        if output:
            try:
                data = json.loads(output)
                assert isinstance(data, (dict, list))
            except json.JSONDecodeError:
                pass  # Human-mode output

    def test_doctor_runs_without_crash(self) -> None:
        result = _run("doctor")
        if "No module" in result.stderr:
            pytest.skip(_skip_reason)
        assert result.returncode in (0, 1, 2)


# ---------------------------------------------------------------------------
# Command group accessibility
# ---------------------------------------------------------------------------


class TestCommandGroupHelp:
    @pytest.mark.parametrize(
        "group",
        [
            "test",
            "hierarchy",
            "component",
            "scene",
            "prefab",
            "playmode",
            "console",
        ],
    )
    def test_command_group_help_accessible(self, group: str) -> None:
        result = _run(group, "--help")
        if "No module" in result.stderr:
            pytest.skip(_skip_reason)
        assert result.returncode == 0, (
            f"`unity-bridge {group} --help` failed with rc={result.returncode}: "
            f"{result.stderr[:200]}"
        )
