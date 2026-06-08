"""
Unit tests for bridge utility behavior.

Tests Unity Bridge utility functions including heartbeat-based Unity detection
and orphaned file cleanup.
Following TDD Red-Green-Refactor methodology.
"""

import json
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path
import os

from unity_bridge.commands.lifecycle import clean
from unity_bridge.core.health import HealthMonitor


class TestCheckHeartbeat:
    """Test heartbeat-based Unity detection."""

    def test_no_heartbeat_file(self, tmp_path):
        """Returns not alive when heartbeat file doesn't exist."""
        result = _check_heartbeat(str(tmp_path))
        assert result["alive"] is False
        assert result["age_seconds"] is None
        assert "No heartbeat" in result["error"]

    def test_stale_heartbeat(self, tmp_path):
        """Returns not alive when heartbeat is older than max_age_seconds."""
        heartbeat_dir = tmp_path / ".claude" / "unity"
        heartbeat_dir.mkdir(parents=True)
        heartbeat_file = heartbeat_dir / "heartbeat.json"

        old_time = datetime.now(timezone.utc) - timedelta(seconds=30)
        heartbeat_file.write_text(json.dumps({
            "timestamp": old_time.isoformat()
        }))

        result = _check_heartbeat(str(tmp_path), max_age_seconds=15.0)
        assert result["alive"] is False
        assert result["age_seconds"] is not None
        assert result["age_seconds"] > 15.0

    def test_fresh_heartbeat(self, tmp_path):
        """Returns alive when heartbeat is within max_age_seconds."""
        heartbeat_dir = tmp_path / ".claude" / "unity"
        heartbeat_dir.mkdir(parents=True)
        heartbeat_file = heartbeat_dir / "heartbeat.json"

        now = datetime.now(timezone.utc)
        heartbeat_file.write_text(json.dumps({
            "timestamp": now.isoformat()
        }))

        result = _check_heartbeat(str(tmp_path), max_age_seconds=15.0)
        assert result["alive"] is True
        assert result["age_seconds"] is not None
        assert result["age_seconds"] < 15.0
        assert result["error"] is None

    def test_invalid_json(self, tmp_path):
        """Returns not alive when heartbeat file contains invalid JSON."""
        heartbeat_dir = tmp_path / ".claude" / "unity"
        heartbeat_dir.mkdir(parents=True)
        heartbeat_file = heartbeat_dir / "heartbeat.json"
        heartbeat_file.write_text("not valid json {{{")

        result = _check_heartbeat(str(tmp_path))
        assert result["alive"] is False
        assert "Invalid" in result["error"]

    def test_missing_timestamp_field(self, tmp_path):
        """Returns not alive when heartbeat JSON has no timestamp field."""
        heartbeat_dir = tmp_path / ".claude" / "unity"
        heartbeat_dir.mkdir(parents=True)
        heartbeat_file = heartbeat_dir / "heartbeat.json"
        heartbeat_file.write_text(json.dumps({"status": "ok"}))

        result = _check_heartbeat(str(tmp_path))
        assert result["alive"] is False
        assert "Invalid heartbeat timestamp" in result["error"]


class TestUnityBridgeReady:
    """Test test_unity_bridge_ready function."""

    def test_ready_with_fresh_heartbeat_and_dirs(self, tmp_path):
        """Returns True when heartbeat is fresh and directories exist."""
        # Create heartbeat
        heartbeat_dir = tmp_path / ".claude" / "unity"
        heartbeat_dir.mkdir(parents=True)
        (heartbeat_dir / "heartbeat.json").write_text(json.dumps({
            "timestamp": datetime.now(timezone.utc).isoformat()
        }))
        # Create command/response dirs
        (heartbeat_dir / "commands").mkdir()
        (heartbeat_dir / "responses").mkdir()

        assert _unity_bridge_ready(str(tmp_path)) is True

    def test_not_ready_without_heartbeat(self, tmp_path):
        """Returns False when no heartbeat file exists."""
        assert _unity_bridge_ready(str(tmp_path)) is False

    def test_not_ready_with_stale_heartbeat(self, tmp_path):
        """Returns False when heartbeat is stale."""
        heartbeat_dir = tmp_path / ".claude" / "unity"
        heartbeat_dir.mkdir(parents=True)
        old_time = datetime.now(timezone.utc) - timedelta(seconds=60)
        (heartbeat_dir / "heartbeat.json").write_text(json.dumps({
            "timestamp": old_time.isoformat()
        }))

        assert _unity_bridge_ready(str(tmp_path)) is False


class TestClearOrphanedBridgeFiles:
    """Test orphaned bridge file cleanup."""

    def test_cleans_old_files(self, tmp_path):
        """Removes files older than the cutoff."""
        commands_dir = tmp_path / ".claude" / "unity" / "commands"
        commands_dir.mkdir(parents=True)

        # Create an old file
        old_file = commands_dir / "old-command.json"
        old_file.write_text("{}")
        # Set modification time to 10 minutes ago
        old_mtime = time.time() - 600
        os.utime(old_file, (old_mtime, old_mtime))

        deleted = clear_orphaned_bridge_files(older_than_minutes=5, project_root=str(tmp_path))
        assert deleted >= 1
        assert not old_file.exists()

    def test_keeps_recent_files(self, tmp_path):
        """Keeps files newer than the cutoff."""
        commands_dir = tmp_path / ".claude" / "unity" / "commands"
        commands_dir.mkdir(parents=True)

        recent_file = commands_dir / "recent-command.json"
        recent_file.write_text("{}")

        deleted = clear_orphaned_bridge_files(older_than_minutes=5, project_root=str(tmp_path))
        assert deleted == 0
        assert recent_file.exists()

    def test_handles_missing_directories(self, tmp_path):
        """Returns 0 when directories don't exist."""
        deleted = clear_orphaned_bridge_files(project_root=str(tmp_path))
        assert deleted == 0


def _check_heartbeat(project_root: str, max_age_seconds: float = 15.0) -> dict:
    monitor = HealthMonitor(Path(project_root))
    original_max_age = monitor.MAX_HEARTBEAT_AGE_SECONDS
    monitor.MAX_HEARTBEAT_AGE_SECONDS = max_age_seconds
    status = monitor.check_health()
    monitor.MAX_HEARTBEAT_AGE_SECONDS = original_max_age
    return {
        "alive": status.healthy,
        "age_seconds": status.heartbeat_age_seconds if status.heartbeat_age_seconds else None,
        "error": status.reason,
    }


def _unity_bridge_ready(project_root: str) -> bool:
    root = Path(project_root)
    unity_dir = root / ".claude" / "unity"
    status = HealthMonitor(root).check_health()
    return (
        status.healthy
        and (unity_dir / "commands").is_dir()
        and (unity_dir / "responses").is_dir()
    )


def clear_orphaned_bridge_files(
    older_than_minutes: int = 5,
    project_root: str = ".",
) -> int:
    result = __import__("asyncio").run(
        clean(Path(project_root), age_minutes=older_than_minutes)
    )
    return int(result.data["deleted"]) if result.data else 0
