"""
Unit tests for bridge_utils.py module.

Tests Unity Bridge utility functions including heartbeat-based Unity detection
and orphaned file cleanup.
Following TDD Red-Green-Refactor methodology.
"""

import pytest
import json
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path
from unittest.mock import patch, MagicMock
import sys
import os
import tempfile
import shutil

# Add scripts directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from bridge_utils import (
    _check_heartbeat,
    test_unity_bridge_ready,
    clear_orphaned_bridge_files,
    get_commands_path,
    get_responses_path,
)


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
        assert "missing timestamp" in result["error"]


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

        assert test_unity_bridge_ready(str(tmp_path)) is True

    def test_not_ready_without_heartbeat(self, tmp_path):
        """Returns False when no heartbeat file exists."""
        assert test_unity_bridge_ready(str(tmp_path)) is False

    def test_not_ready_with_stale_heartbeat(self, tmp_path):
        """Returns False when heartbeat is stale."""
        heartbeat_dir = tmp_path / ".claude" / "unity"
        heartbeat_dir.mkdir(parents=True)
        old_time = datetime.now(timezone.utc) - timedelta(seconds=60)
        (heartbeat_dir / "heartbeat.json").write_text(json.dumps({
            "timestamp": old_time.isoformat()
        }))

        assert test_unity_bridge_ready(str(tmp_path)) is False


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

        deleted = clear_orphaned_bridge_files(
            older_than_minutes=5, project_root=str(tmp_path)
        )
        assert deleted >= 1
        assert not old_file.exists()

    def test_keeps_recent_files(self, tmp_path):
        """Keeps files newer than the cutoff."""
        commands_dir = tmp_path / ".claude" / "unity" / "commands"
        commands_dir.mkdir(parents=True)

        recent_file = commands_dir / "recent-command.json"
        recent_file.write_text("{}")

        deleted = clear_orphaned_bridge_files(
            older_than_minutes=5, project_root=str(tmp_path)
        )
        assert deleted == 0
        assert recent_file.exists()

    def test_handles_missing_directories(self, tmp_path):
        """Returns 0 when directories don't exist."""
        deleted = clear_orphaned_bridge_files(project_root=str(tmp_path))
        assert deleted == 0
