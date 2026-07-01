"""
HealthMonitor — monitor Unity Bridge health via heartbeat file.

Migrated from health_monitor.py. Reads the heartbeat JSON written by
Unity Editor to determine if the bridge is alive and responsive.
"""

import json
import logging
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from unity_bridge.core.timeutil import (
    optional_int as _optional_int,
    parse_iso_datetime as _parse_datetime,
)

logger = logging.getLogger("unity_bridge.health")


@dataclass
class HealthStatus:
    """Health status of the Unity Bridge.

    Attributes:
        healthy: Whether the bridge is operational.
        ready: Whether the editor can accept bridge commands now.
        reason: Explanation if unhealthy, None if healthy.
        unity_version: Unity Editor version string.
        is_compiling: Whether Unity is currently compiling.
        is_updating: Whether Unity is importing or refreshing assets.
        is_reloading_assemblies: Whether Unity is reloading assemblies.
        is_playing_or_will_change_playmode: Whether play mode is transitioning.
        busy_reason: Editor busy reason when healthy but not ready.
        editor_busy_age_seconds: Age of last editor busy signal, if known.
        domain_generation: Monotonic editor-domain generation, if heartbeat provides it.
        last_reload_timestamp: Last editor reload timestamp, if heartbeat provides it.
        is_playing: Whether Unity is in play mode.
        is_paused: Whether play mode is paused.
        active_scene: Name of the currently active scene.
        commands_processed: Total commands processed since startup.
        uptime_seconds: Unity Editor uptime in seconds.
        heartbeat_age_seconds: Age of the last heartbeat in seconds.
    """

    healthy: bool
    ready: bool | None = None
    reason: str | None = None
    unity_version: str | None = None
    is_compiling: bool = False
    is_updating: bool = False
    is_reloading_assemblies: bool = False
    is_playing_or_will_change_playmode: bool = False
    busy_reason: str | None = None
    editor_busy_age_seconds: float | None = None
    domain_generation: int | None = None
    last_reload_timestamp: str | None = None
    is_playing: bool = False
    is_paused: bool = False
    active_scene: str | None = None
    commands_processed: int = 0
    uptime_seconds: int = 0
    heartbeat_age_seconds: float = 0.0

    def __post_init__(self) -> None:
        """Derive readiness and busy reason when callers omit them."""
        if self.busy_reason is None:
            self.busy_reason = self._infer_busy_reason()
        if self.ready is None:
            self.ready = self.healthy and self.busy_reason is None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary with camelCase keys for bridge compatibility."""
        return {
            "healthy": self.healthy,
            "ready": self.ready,
            "reason": self.reason,
            "unityVersion": self.unity_version,
            "isCompiling": self.is_compiling,
            "isUpdating": self.is_updating,
            "isReloadingAssemblies": self.is_reloading_assemblies,
            "isPlayingOrWillChangePlaymode": self.is_playing_or_will_change_playmode,
            "busyReason": self.busy_reason,
            "editorBusyAgeSeconds": (
                round(self.editor_busy_age_seconds, 2)
                if self.editor_busy_age_seconds is not None
                else None
            ),
            "domainGeneration": self.domain_generation,
            "lastReloadTimestamp": self.last_reload_timestamp,
            "isPlaying": self.is_playing,
            "isPaused": self.is_paused,
            "activeScene": self.active_scene,
            "commandsProcessed": self.commands_processed,
            "uptimeSeconds": self.uptime_seconds,
            "heartbeatAgeSeconds": round(self.heartbeat_age_seconds, 2),
        }

    def _infer_busy_reason(self) -> str | None:
        """Return the first active editor-busy reason."""
        if self.is_compiling:
            return "compiling"
        if self.is_updating:
            return "updating"
        if self.is_reloading_assemblies:
            return "reloading_assemblies"
        if self.is_playing_or_will_change_playmode:
            return "playmode_transition"
        return None


class HealthMonitor:
    """Monitor Unity Bridge health via heartbeat file.

    Reads and analyzes heartbeat files written by Unity Editor.
    The heartbeat contains periodic status updates indicating
    Unity is running and responsive.
    """

    MAX_HEARTBEAT_AGE_SECONDS: float = 15.0
    BUSY_STALE_GRACE_SECONDS: float = 120.0

    def __init__(self, project_root: Path) -> None:
        self.project_root = project_root
        self._heartbeat_path = project_root / ".claude" / "unity" / "heartbeat.json"

    @property
    def heartbeat_path(self) -> Path:
        """Path to the heartbeat.json file."""
        return self._heartbeat_path

    def check_health(self) -> HealthStatus:
        """Check if Unity Bridge is healthy by reading the heartbeat file.

        Returns:
            HealthStatus with current bridge health information.
        """
        if not self.heartbeat_path.exists():
            return HealthStatus(
                healthy=False,
                reason="No heartbeat file found. Unity Bridge may not be running.",
            )

        try:
            with open(self.heartbeat_path, "r", encoding="utf-8") as f:
                heartbeat = json.load(f)
        except json.JSONDecodeError as exc:
            return HealthStatus(healthy=False, reason=f"Invalid heartbeat JSON: {exc}")
        except IOError as exc:
            return HealthStatus(healthy=False, reason=f"Failed to read heartbeat: {exc}")

        return self._evaluate_heartbeat(heartbeat)

    def wait_for_healthy(
        self,
        timeout_seconds: float = 30.0,
        poll_interval: float = 0.5,
    ) -> HealthStatus:
        """Wait for Unity Bridge to become healthy.

        Args:
            timeout_seconds: Maximum time to wait.
            poll_interval: Seconds between health checks.

        Returns:
            HealthStatus when healthy, or last status on timeout.
        """
        start = time.time()
        last_status: HealthStatus | None = None

        while time.time() - start < timeout_seconds:
            status = self.check_health()
            last_status = status
            if status.healthy:
                logger.info("Unity Bridge healthy after %.1fs", time.time() - start)
                return status
            logger.debug("Waiting for healthy: %s", status.reason)
            time.sleep(poll_interval)

        logger.warning("Timeout waiting for healthy after %.0fs", timeout_seconds)
        return last_status or HealthStatus(
            healthy=False,
            reason=f"Timeout waiting for healthy status after {timeout_seconds}s",
        )

    def wait_for_ready(
        self,
        timeout_seconds: float = 180.0,
        poll_interval: float = 0.5,
    ) -> HealthStatus:
        """Wait for Unity Editor to be healthy and command-ready.

        Unlike wait_for_healthy(), this treats compiling, importing, and
        reload windows as live-but-not-ready and waits through them.
        """
        start = time.time()
        last_status: HealthStatus | None = None

        while time.time() - start < timeout_seconds:
            status = self.check_health()
            last_status = status
            if status.ready:
                logger.info("Unity Editor ready after %.1fs", time.time() - start)
                return status
            if not status.healthy and status.busy_reason is None:
                return status
            logger.debug("Waiting for editor readiness: %s", status.busy_reason)
            time.sleep(poll_interval)

        logger.warning("Timeout waiting for editor readiness after %.0fs", timeout_seconds)
        return last_status or HealthStatus(
            healthy=False,
            ready=False,
            reason=f"Timeout waiting for editor readiness after {timeout_seconds}s",
        )

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _evaluate_heartbeat(self, heartbeat: dict[str, Any]) -> HealthStatus:
        """Parse heartbeat data and determine health status."""
        timestamp_str = heartbeat.get("timestamp", "")
        try:
            ts = _parse_datetime(timestamp_str)
            age = (datetime.now(timezone.utc) - ts).total_seconds()
        except (ValueError, TypeError) as exc:
            return HealthStatus(
                healthy=False,
                reason=f"Invalid heartbeat timestamp: {timestamp_str} ({exc})",
            )

        busy_reason = _heartbeat_busy_reason(heartbeat, include_last_busy=False)
        busy_age = _busy_age_seconds(heartbeat)

        if age > self.MAX_HEARTBEAT_AGE_SECONDS:
            stale_busy_reason = _heartbeat_busy_reason(heartbeat, include_last_busy=True)
            if stale_busy_reason and _is_within_busy_grace(busy_age):
                return HealthStatus(
                    healthy=False,
                    ready=False,
                    reason=f"Heartbeat is stale after editor busy state ({age:.1f}s old).",
                    is_compiling=heartbeat.get("isCompiling", False),
                    is_updating=heartbeat.get("isUpdating", False),
                    is_reloading_assemblies=heartbeat.get("isReloadingAssemblies", False),
                    is_playing_or_will_change_playmode=heartbeat.get(
                        "isPlayingOrWillChangePlaymode", False
                    ),
                    busy_reason=stale_busy_reason,
                    editor_busy_age_seconds=busy_age,
                    domain_generation=_optional_int(heartbeat.get("domainGeneration")),
                    last_reload_timestamp=heartbeat.get("lastReloadTimestamp"),
                    heartbeat_age_seconds=age,
                )
            return HealthStatus(
                healthy=False,
                reason=f"Heartbeat is stale ({age:.1f}s old). Unity may be frozen or closed.",
                heartbeat_age_seconds=age,
            )

        return HealthStatus(
            healthy=True,
            unity_version=heartbeat.get("unityVersion"),
            is_compiling=heartbeat.get("isCompiling", False),
            is_updating=heartbeat.get("isUpdating", False),
            is_reloading_assemblies=heartbeat.get("isReloadingAssemblies", False),
            is_playing_or_will_change_playmode=heartbeat.get(
                "isPlayingOrWillChangePlaymode", False
            ),
            busy_reason=busy_reason,
            editor_busy_age_seconds=busy_age,
            domain_generation=_optional_int(heartbeat.get("domainGeneration")),
            last_reload_timestamp=heartbeat.get("lastReloadTimestamp"),
            is_playing=heartbeat.get("isPlaying", False),
            is_paused=heartbeat.get("isPaused", False),
            active_scene=heartbeat.get("activeScene"),
            commands_processed=heartbeat.get("commandsProcessed", 0),
            uptime_seconds=heartbeat.get("uptimeSeconds", 0),
            heartbeat_age_seconds=age,
        )


def _heartbeat_busy_reason(
    heartbeat: dict[str, Any],
    include_last_busy: bool,
) -> str | None:
    """Infer busy reason from heartbeat fields."""
    current = heartbeat.get("busyReason")
    if current:
        return _normalize_busy_reason(str(current))
    if heartbeat.get("isCompiling", False):
        return _normalize_busy_reason(str(heartbeat.get("lastBusyReason") or "compiling"))
    if heartbeat.get("isUpdating", False):
        return _normalize_busy_reason(str(heartbeat.get("lastBusyReason") or "updating"))
    if heartbeat.get("isReloadingAssemblies", False):
        return _normalize_busy_reason(
            str(heartbeat.get("lastBusyReason") or "reloading_assemblies")
        )
    if heartbeat.get("isPlayingOrWillChangePlaymode", False):
        return _normalize_busy_reason(str(heartbeat.get("lastBusyReason") or "playmode_transition"))
    if include_last_busy and heartbeat.get("lastBusyReason"):
        return _normalize_busy_reason(str(heartbeat.get("lastBusyReason")))
    return None


def _busy_age_seconds(heartbeat: dict[str, Any]) -> float | None:
    """Return age of last busy timestamp when heartbeat provides it."""
    timestamp = heartbeat.get("lastBusyTimestamp") or heartbeat.get("busyTimestamp")
    if not timestamp:
        return None
    try:
        ts = _parse_datetime(str(timestamp))
    except (ValueError, TypeError):
        return None
    return (datetime.now(timezone.utc) - ts).total_seconds()


def _is_within_busy_grace(busy_age: float | None) -> bool:
    """Whether stale heartbeat should remain classified as editor busy."""
    return busy_age is None or busy_age <= HealthMonitor.BUSY_STALE_GRACE_SECONDS


def _normalize_busy_reason(reason: str) -> str:
    """Normalize C# and Python busy reason names to one public vocabulary."""
    normalized = reason.strip().lower()
    aliases = {
        "assembly_reload": "reloading_assemblies",
        "assembly reload": "reloading_assemblies",
        "reload": "reloading_assemblies",
        "compilation": "compiling",
        "asset_database_update": "updating",
        "assetdatabase_update": "updating",
    }
    return aliases.get(normalized, normalized)
