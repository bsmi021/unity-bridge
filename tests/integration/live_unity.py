"""Environment-selected runner for live Unity 6000.5 integration tests."""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol


MAX_CLI_TIMEOUT_SECONDS = 600
UNITY_6000_5_PATTERN = re.compile(r"^6000\.5(?:\.|$)")
FIXTURE_MATRIX_PATH = (
    Path(__file__).resolve().parents[1] / "fixtures" / "unity65_fixture_matrix.json"
)


class LiveFixtureUnavailable(RuntimeError):
    """Raised when a configured live target cannot provide valid proof."""


@dataclass(frozen=True)
class CliInvocation:
    """Captured subprocess outcome with parsed JSON when available."""

    args: tuple[str, ...]
    returncode: int
    stdout: str
    stderr: str
    payload: dict[str, Any] | None

    def require_success(self) -> Any:
        """Return command data or raise with the exact command diagnostics."""
        success = isinstance(self.payload, dict) and self.payload.get("success") is True
        if self.returncode != 0 or not success:
            command = " ".join(self.args)
            details = self.payload or self.stderr.strip() or self.stdout.strip()
            raise AssertionError(f"unity-bridge {command} failed: {details}")
        return self.payload.get("data")


class UnityCliRunner(Protocol):
    """Callable contract used to substitute CLI execution in unit tests."""

    def __call__(
        self,
        project: Path,
        args: tuple[str, ...],
        *,
        timeout: int,
    ) -> CliInvocation: ...


@dataclass(frozen=True)
class LiveUnityTarget:
    """A healthy Unity 6000.5 target selected only through the environment."""

    project: Path
    unity_version: str
    health: dict[str, Any]
    runner: UnityCliRunner

    def invoke(self, *args: str, timeout: int = 30) -> CliInvocation:
        """Run a bounded CLI command against the selected project."""
        return self.runner(self.project, tuple(args), timeout=timeout)


@dataclass(frozen=True)
class FixtureRole:
    """One required live fixture role and its selecting environment variable."""

    name: str
    environment: str


@dataclass(frozen=True)
class OptionalAdapterProbe:
    """A read-only command that reports an optional Unity adapter's state."""

    name: str
    args: tuple[str, ...]
    availability_key: str | None = None
    failure_fragments: tuple[str, ...] = ()


OPTIONAL_ADAPTER_PROBES = (
    OptionalAdapterProbe("project-auditor", ("project-auditor", "availability"), "api_available"),
    OptionalAdapterProbe("code-coverage", ("coverage", "availability"), "api_available"),
    OptionalAdapterProbe("graph-toolkit", ("graph-toolkit", "availability"), "module_available"),
    OptionalAdapterProbe("entities", ("entities", "availability"), "api_available"),
    OptionalAdapterProbe(
        "adaptive-performance", ("adaptive-performance", "availability"), "api_available"
    ),
    OptionalAdapterProbe(
        "multiplayer-playmode",
        ("multiplayer-playmode", "availability"),
        "current_player_type_present",
    ),
    OptionalAdapterProbe(
        "cinemachine",
        ("cinemachine", "list-cameras"),
        failure_fragments=("cinemachine package not installed",),
    ),
    OptionalAdapterProbe(
        "localization",
        ("localization", "list-locales"),
        failure_fragments=("localization package is not installed",),
    ),
    OptionalAdapterProbe(
        "vfx-graph",
        (
            "vfx",
            "get-info",
            "--asset-path",
            "Assets/UnityBridgeFixtures/Missing.vfx",
        ),
        failure_fragments=(
            "vfx graph package (com.unity.visualeffectgraph) is not installed",
            "no visualeffectasset found",
        ),
    ),
    OptionalAdapterProbe(
        "timeline",
        ("timeline", "get-info", "Assets/UnityBridgeFixtures/Missing.playable"),
        failure_fragments=("timeline package", "timelineasset not found"),
    ),
    OptionalAdapterProbe(
        "input-system",
        ("input-system", "list"),
        failure_fragments=("input system package",),
    ),
    OptionalAdapterProbe(
        "addressables",
        ("addressables", "list-groups"),
        failure_fragments=(
            "addressables package not installed",
            "addressable settings not initialized",
        ),
    ),
)


def run_unity_cli(
    project: Path,
    args: tuple[str, ...],
    *,
    timeout: int,
    execute: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
) -> CliInvocation:
    """Invoke the supported CLI against one explicit Unity project."""
    if timeout < 1 or timeout > MAX_CLI_TIMEOUT_SECONDS:
        raise ValueError("CLI timeout must be between 1 and 600 seconds.")
    root = Path(__file__).resolve().parents[2]
    env = _cli_environment(root)
    command = [
        sys.executable,
        "-m",
        "unity_bridge",
        "--no-color",
        "--project",
        str(project.resolve()),
        *args,
    ]
    completed = execute(
        command,
        capture_output=True,
        text=True,
        timeout=timeout,
        cwd=str(root),
        env=env,
        shell=False,
    )
    return CliInvocation(
        args=args,
        returncode=completed.returncode,
        stdout=completed.stdout,
        stderr=completed.stderr,
        payload=_parse_payload(completed.stdout),
    )


def select_live_unity_target(
    environ: Mapping[str, str],
    *,
    runner: UnityCliRunner = run_unity_cli,
) -> LiveUnityTarget:
    """Validate the environment-selected project, heartbeat, and Unity version."""
    return _select_configured_target(environ, "UNITY_BRIDGE_PROJECT", runner)


def load_fixture_matrix(path: Path = FIXTURE_MATRIX_PATH) -> tuple[FixtureRole, ...]:
    """Load and validate the required live fixture role manifest."""
    try:
        manifest = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise LiveFixtureUnavailable(f"Fixture matrix is unreadable: {exc}") from exc
    if not isinstance(manifest, dict):
        raise LiveFixtureUnavailable("Fixture matrix must use schema_version 1 and roles.")
    roles = manifest.get("roles")
    if manifest.get("schema_version") != 1 or not isinstance(roles, list):
        raise LiveFixtureUnavailable("Fixture matrix must use schema_version 1 and roles.")
    parsed = tuple(_parse_fixture_role(item) for item in roles)
    expected = ("core-clean", "package-rich", "playback-build-target")
    if tuple(role.name for role in parsed) != expected:
        raise LiveFixtureUnavailable(f"Fixture matrix roles must be {expected!r} in order.")
    if len({role.environment for role in parsed}) != len(parsed):
        raise LiveFixtureUnavailable("Fixture matrix environment variables must be unique.")
    return parsed


def select_live_unity_role(
    role_name: str,
    environ: Mapping[str, str],
    *,
    runner: UnityCliRunner = run_unity_cli,
) -> LiveUnityTarget:
    """Select one manifest role and preserve its exact unavailability reason."""
    roles = {role.name: role for role in load_fixture_matrix()}
    role = roles.get(role_name)
    if role is None:
        raise LiveFixtureUnavailable(f"Unknown live fixture role: {role_name}")
    try:
        return _select_configured_target(environ, role.environment, runner)
    except LiveFixtureUnavailable as exc:
        raise LiveFixtureUnavailable(f"{role.name} fixture role is unavailable: {exc}") from exc


def select_live_unity_environment(
    environment: str,
    environ: Mapping[str, str],
    *,
    runner: UnityCliRunner = run_unity_cli,
) -> LiveUnityTarget:
    """Select a healthy target from an explicit, non-manifest environment."""
    return _select_configured_target(environ, environment, runner)


def require_explicit_guard(
    environ: Mapping[str, str],
    environment: str,
    purpose: str,
) -> None:
    """Require an exact opt-in before a live fixture may be mutated."""
    if environ.get(environment, "").strip() != "1":
        raise LiveFixtureUnavailable(f"{purpose} requires explicit opt-in with {environment}=1.")


def _select_configured_target(
    environ: Mapping[str, str],
    environment: str,
    runner: UnityCliRunner,
) -> LiveUnityTarget:
    """Validate one environment-selected project and healthy Unity heartbeat."""
    configured = environ.get(environment, "").strip()
    if not configured:
        raise LiveFixtureUnavailable(
            f"{environment} is unset; live Unity 6000.5 tests were not run."
        )
    project = Path(configured).expanduser().resolve()
    if not (project / "Assets").is_dir() or not (project / "ProjectSettings").is_dir():
        raise LiveFixtureUnavailable(f"{project} is not a Unity project.")
    try:
        status = runner(project, ("status",), timeout=15)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise LiveFixtureUnavailable(f"Unity status probe failed: {exc}") from exc
    if not isinstance(status.payload, dict):
        raise LiveFixtureUnavailable("Unity status did not return valid JSON.")
    health = status.payload.get("data")
    if not isinstance(health, dict) or health.get("healthy") is not True:
        reason = status.payload.get("error") or "unknown heartbeat failure"
        raise LiveFixtureUnavailable(f"Unity heartbeat is not healthy: {reason}")
    if health.get("ready") is not True:
        reason = health.get("reason") or health.get("busy_reason") or "unknown busy state"
        raise LiveFixtureUnavailable(f"Unity Editor is not command-ready: {reason}")
    version = health.get("unity_version")
    if not isinstance(version, str) or not UNITY_6000_5_PATTERN.match(version):
        raise LiveFixtureUnavailable(
            f"Live fixture requires Unity 6000.5.x; target reported {version!r}."
        )
    return LiveUnityTarget(project, version, health, runner)


def _parse_fixture_role(value: object) -> FixtureRole:
    if not isinstance(value, dict):
        raise LiveFixtureUnavailable("Fixture matrix roles must be objects.")
    name = value.get("name")
    environment = value.get("environment")
    if not isinstance(name, str) or not isinstance(environment, str):
        raise LiveFixtureUnavailable("Fixture matrix roles require name and environment.")
    if not name or not environment.startswith("UNITY_BRIDGE_"):
        raise LiveFixtureUnavailable("Fixture matrix role values are invalid.")
    return FixtureRole(name, environment)


def _parse_payload(stdout: str) -> dict[str, Any] | None:
    try:
        parsed = json.loads(stdout.strip())
    except (json.JSONDecodeError, TypeError):
        return None
    return parsed if isinstance(parsed, dict) else None


def _cli_environment(root: Path) -> dict[str, str]:
    env = os.environ.copy()
    entries = [str(root), str(root / "src")]
    existing = env.get("PYTHONPATH")
    if existing:
        entries.append(existing)
    env["PYTHONPATH"] = os.pathsep.join(entries)
    return env
