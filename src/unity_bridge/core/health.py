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

logger = logging.getLogger("unity_bridge.health")


@dataclass
class HealthStatus:
    """Health status of the Unity Bridge.

    Attributes:
        healthy: Whether the bridge is operational.
        reason: Explanation if unhealthy, None if healthy.
        unity_version: Unity Editor version string.
        is_compiling: Whether Unity is currently compiling.
        is_playing: Whether Unity is in play mode.
        is_paused: Whether play mode is paused.
        active_scene: Name of the currently active scene.
        commands_processed: Total commands processed since startup.
        uptime_seconds: Unity Editor uptime in seconds.
        heartbeat_age_seconds: Age of the last heartbeat in seconds.
    """

    healthy: bool
    reason: str | None = None
    unity_version: str | None = None
    is_compiling: bool = False
    is_playing: bool = False
    is_paused: bool = False
    active_scene: str | None = None
    commands_processed: int = 0
    uptime_seconds: int = 0
    heartbeat_age_seconds: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary with camelCase keys for bridge compatibility."""
        return {
            "healthy": self.healthy,
            "reason": self.reason,
            "unityVersion": self.unity_version,
            "isCompiling": self.is_compiling,
            "isPlaying": self.is_playing,
            "isPaused": self.is_paused,
            "activeScene": self.active_scene,
            "commandsProcessed": self.commands_processed,
            "uptimeSeconds": self.uptime_seconds,
            "heartbeatAgeSeconds": round(self.heartbeat_age_seconds, 2),
        }


class HealthMonitor:
    """Monitor Unity Bridge health via heartbeat file.

    Reads and analyzes heartbeat files written by Unity Editor.
    The heartbeat contains periodic status updates indicating
    Unity is running and responsive.
    """

    MAX_HEARTBEAT_AGE_SECONDS: float = 15.0

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

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _evaluate_heartbeat(self, heartbeat: dict[str, Any]) -> HealthStatus:
        """Parse heartbeat data and determine health status."""
        timestamp_str = heartbeat.get("timestamp", "")
        try:
            normalized = timestamp_str.replace("Z", "+00:00")
            ts = datetime.fromisoformat(normalized)
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=timezone.utc)
            age = (datetime.now(timezone.utc) - ts).total_seconds()
        except (ValueError, TypeError) as exc:
            return HealthStatus(
                healthy=False,
                reason=f"Invalid heartbeat timestamp: {timestamp_str} ({exc})",
            )

        if age > self.MAX_HEARTBEAT_AGE_SECONDS:
            return HealthStatus(
                healthy=False,
                reason=f"Heartbeat is stale ({age:.1f}s old). Unity may be frozen or closed.",
                heartbeat_age_seconds=age,
            )

        return HealthStatus(
            healthy=True,
            unity_version=heartbeat.get("unityVersion"),
            is_compiling=heartbeat.get("isCompiling", False),
            is_playing=heartbeat.get("isPlaying", False),
            is_paused=heartbeat.get("isPaused", False),
            active_scene=heartbeat.get("activeScene"),
            commands_processed=heartbeat.get("commandsProcessed", 0),
            uptime_seconds=heartbeat.get("uptimeSeconds", 0),
            heartbeat_age_seconds=age,
        )
