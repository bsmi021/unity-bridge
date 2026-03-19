"""
Unit tests for health_monitor.py module.

Tests Unity Bridge health monitoring via heartbeat file.
Following TDD Red-Green-Refactor methodology.
"""

import pytest
import json
import asyncio
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any


# Import will fail initially (RED phase) - that's expected in TDD
try:
    from health_monitor import (
        HealthStatus,
        HealthMonitor
    )
except ImportError:
    HealthStatus = None
    HealthMonitor = None


class TestHealthStatus:
    """Test HealthStatus dataclass."""

    def test_health_status_creation_healthy(self):
        """HealthStatus should store health information."""
        status = HealthStatus(
            healthy=True,
            unity_version="2022.3.10f1",
            is_compiling=False,
            is_playing=True,
            commands_processed=42
        )

        assert status.healthy is True
        assert status.unity_version == "2022.3.10f1"
        assert status.is_compiling is False
        assert status.is_playing is True
        assert status.commands_processed == 42

    def test_health_status_creation_unhealthy(self):
        """HealthStatus should support unhealthy state with reason."""
        status = HealthStatus(
            healthy=False,
            reason="Heartbeat file not found"
        )

        assert status.healthy is False
        assert status.reason == "Heartbeat file not found"

    def test_health_status_defaults(self):
        """HealthStatus should have sensible defaults."""
        status = HealthStatus(healthy=True)

        assert status.reason is None
        assert status.unity_version is None
        assert status.is_compiling is False
        assert status.is_playing is False
        assert status.is_paused is False
        assert status.active_scene is None
        assert status.commands_processed == 0
        assert status.uptime_seconds == 0
        assert status.heartbeat_age_seconds == 0.0

    def test_health_status_to_dict(self):
        """HealthStatus should convert to dictionary."""
        status = HealthStatus(
            healthy=True,
            unity_version="2021.3.0f1",
            is_compiling=True,
            is_playing=False,
            active_scene="MainScene",
            commands_processed=100,
            uptime_seconds=3600,
            heartbeat_age_seconds=2.5
        )

        result = status.to_dict()

        assert isinstance(result, dict)
        assert result["healthy"] is True
        assert result["unityVersion"] == "2021.3.0f1"
        assert result["isCompiling"] is True
        assert result["isPlaying"] is False
        assert result["activeScene"] == "MainScene"
        assert result["commandsProcessed"] == 100
        assert result["uptimeSeconds"] == 3600
        assert result["heartbeatAgeSeconds"] == 2.5

    def test_health_status_to_dict_with_reason(self):
        """HealthStatus.to_dict() should include reason when unhealthy."""
        status = HealthStatus(
            healthy=False,
            reason="Unity not responding"
        )

        result = status.to_dict()
        assert result["healthy"] is False
        assert result["reason"] == "Unity not responding"


@pytest.fixture
def tmp_project_root(tmp_path):
    """Fixture providing temporary project root directory."""
    project_root = tmp_path / "unity_project"
    project_root.mkdir()
    return project_root


@pytest.fixture
def health_monitor(tmp_project_root):
    """Fixture providing HealthMonitor instance."""
    return HealthMonitor(tmp_project_root)


@pytest.fixture
def heartbeat_path(tmp_project_root):
    """Fixture providing path to heartbeat file."""
    heartbeat_dir = tmp_project_root / ".claude" / "unity"
    heartbeat_dir.mkdir(parents=True, exist_ok=True)
    return heartbeat_dir / "heartbeat.json"


def write_heartbeat(path: Path, data: Dict[str, Any]):
    """Helper to write heartbeat JSON file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f)


class TestHealthMonitorInitialization:
    """Test HealthMonitor initialization."""

    def test_initialization(self, tmp_project_root):
        """HealthMonitor should initialize with project root."""
        monitor = HealthMonitor(tmp_project_root)

        assert monitor.project_root == tmp_project_root
        assert monitor.heartbeat_path == tmp_project_root / ".claude" / "unity" / "heartbeat.json"

    def test_max_heartbeat_age_constant(self):
        """MAX_HEARTBEAT_AGE_SECONDS should be defined."""
        assert HealthMonitor.MAX_HEARTBEAT_AGE_SECONDS == 15.0


class TestCheckHealthNoHeartbeat:
    """Test health check when heartbeat file doesn't exist."""

    def test_no_heartbeat_file(self, health_monitor):
        """Missing heartbeat file should return unhealthy status."""
        status = health_monitor.check_health()

        assert status.healthy is False
        assert "heartbeat file" in status.reason.lower()
        assert "not found" in status.reason.lower() or "may not be running" in status.reason.lower()


class TestCheckHealthValidHeartbeat:
    """Test health check with valid heartbeat file."""

    def test_valid_heartbeat(self, health_monitor, heartbeat_path):
        """Valid recent heartbeat should return healthy status."""
        heartbeat_data = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "unityVersion": "2022.3.10f1",
            "isCompiling": False,
            "isPlaying": True,
            "isPaused": False,
            "activeScene": "TestScene",
            "commandsProcessed": 50,
            "uptimeSeconds": 1200
        }
        write_heartbeat(heartbeat_path, heartbeat_data)

        status = health_monitor.check_health()

        assert status.healthy is True
        assert status.unity_version == "2022.3.10f1"
        assert status.is_compiling is False
        assert status.is_playing is True
        assert status.is_paused is False
        assert status.active_scene == "TestScene"
        assert status.commands_processed == 50
        assert status.uptime_seconds == 1200
        assert status.heartbeat_age_seconds < 1.0  # Should be very recent

    def test_heartbeat_all_states(self, health_monitor, heartbeat_path):
        """Health check should report all Unity states correctly."""
        heartbeat_data = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "unityVersion": "2021.3.0f1",
            "isCompiling": True,
            "isPlaying": False,
            "isPaused": True,
            "activeScene": "EditorScene",
            "commandsProcessed": 0,
            "uptimeSeconds": 60
        }
        write_heartbeat(heartbeat_path, heartbeat_data)

        status = health_monitor.check_health()

        assert status.healthy is True
        assert status.is_compiling is True
        assert status.is_playing is False
        assert status.is_paused is True


class TestCheckHealthStaleHeartbeat:
    """Test health check with stale/old heartbeat."""

    def test_stale_heartbeat(self, health_monitor, heartbeat_path):
        """Old heartbeat should return unhealthy status."""
        # Heartbeat from 20 seconds ago (exceeds MAX_HEARTBEAT_AGE_SECONDS)
        old_time = datetime.utcnow() - timedelta(seconds=20)
        heartbeat_data = {
            "timestamp": old_time.isoformat() + "Z",
            "unityVersion": "2022.3.10f1",
            "isCompiling": False,
            "isPlaying": False,
            "isPaused": False,
            "activeScene": "Scene",
            "commandsProcessed": 10,
            "uptimeSeconds": 100
        }
        write_heartbeat(heartbeat_path, heartbeat_data)

        status = health_monitor.check_health()

        assert status.healthy is False
        assert "stale" in status.reason.lower()
        assert status.heartbeat_age_seconds > 15.0

    def test_heartbeat_at_boundary(self, health_monitor, heartbeat_path):
        """Heartbeat at exact boundary should be tested."""
        # Exactly at MAX_HEARTBEAT_AGE_SECONDS boundary
        boundary_time = datetime.utcnow() - timedelta(seconds=HealthMonitor.MAX_HEARTBEAT_AGE_SECONDS)
        heartbeat_data = {
            "timestamp": boundary_time.isoformat() + "Z",
            "unityVersion": "2022.3.10f1",
            "isCompiling": False,
            "isPlaying": False,
            "isPaused": False,
            "activeScene": "Scene",
            "commandsProcessed": 0,
            "uptimeSeconds": 0
        }
        write_heartbeat(heartbeat_path, heartbeat_data)

        status = health_monitor.check_health()

        # Should be unhealthy (age > MAX)
        assert status.healthy is False

    def test_heartbeat_just_within_threshold(self, health_monitor, heartbeat_path):
        """Heartbeat just within threshold should be healthy."""
        # 10 seconds old (within 15 second threshold)
        recent_time = datetime.utcnow() - timedelta(seconds=10)
        heartbeat_data = {
            "timestamp": recent_time.isoformat() + "Z",
            "unityVersion": "2022.3.10f1",
            "isCompiling": False,
            "isPlaying": False,
            "isPaused": False,
            "activeScene": "Scene",
            "commandsProcessed": 0,
            "uptimeSeconds": 0
        }
        write_heartbeat(heartbeat_path, heartbeat_data)

        status = health_monitor.check_health()

        assert status.healthy is True
        assert 9.0 < status.heartbeat_age_seconds < 11.0


class TestCheckHealthInvalidHeartbeat:
    """Test health check with malformed heartbeat data."""

    def test_invalid_json(self, health_monitor, heartbeat_path):
        """Malformed JSON should return unhealthy status."""
        heartbeat_path.parent.mkdir(parents=True, exist_ok=True)
        with open(heartbeat_path, 'w') as f:
            f.write("{ invalid json content")

        status = health_monitor.check_health()

        assert status.healthy is False
        assert "invalid" in status.reason.lower() or "json" in status.reason.lower()

    def test_invalid_timestamp_format(self, health_monitor, heartbeat_path):
        """Invalid timestamp format should return unhealthy status."""
        heartbeat_data = {
            "timestamp": "not-a-valid-timestamp",
            "unityVersion": "2022.3.10f1",
            "isCompiling": False,
            "isPlaying": False,
            "isPaused": False,
            "activeScene": "Scene",
            "commandsProcessed": 0,
            "uptimeSeconds": 0
        }
        write_heartbeat(heartbeat_path, heartbeat_data)

        status = health_monitor.check_health()

        assert status.healthy is False
        assert "timestamp" in status.reason.lower() or "invalid" in status.reason.lower()

    def test_missing_timestamp_field(self, health_monitor, heartbeat_path):
        """Missing timestamp field should return unhealthy status."""
        heartbeat_data = {
            "unityVersion": "2022.3.10f1",
            "isCompiling": False
        }
        write_heartbeat(heartbeat_path, heartbeat_data)

        status = health_monitor.check_health()

        assert status.healthy is False

    def test_empty_heartbeat_file(self, health_monitor, heartbeat_path):
        """Empty heartbeat file should return unhealthy status."""
        heartbeat_path.parent.mkdir(parents=True, exist_ok=True)
        heartbeat_path.touch()

        status = health_monitor.check_health()

        assert status.healthy is False


class TestCheckHealthIOErrors:
    """Test health check handling of I/O errors."""

    def test_permission_error(self, health_monitor, heartbeat_path, monkeypatch):
        """Permission errors should be handled gracefully."""
        write_heartbeat(heartbeat_path, {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "unityVersion": "2022.3.10f1"
        })

        # Mock open to raise PermissionError
        original_open = open

        def mock_open(*args, **kwargs):
            if str(heartbeat_path) in str(args[0]):
                raise PermissionError("Access denied")
            return original_open(*args, **kwargs)

        monkeypatch.setattr("builtins.open", mock_open)

        status = health_monitor.check_health()

        assert status.healthy is False
        assert "failed to read" in status.reason.lower() or "access" in status.reason.lower()


class TestWaitForHealthy:
    """Test wait_for_healthy method."""

    def test_wait_for_healthy_immediate(self, health_monitor, heartbeat_path):
        """Should return immediately if already healthy."""
        heartbeat_data = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "unityVersion": "2022.3.10f1",
            "isCompiling": False,
            "isPlaying": False,
            "isPaused": False,
            "activeScene": "Scene",
            "commandsProcessed": 0,
            "uptimeSeconds": 0
        }
        write_heartbeat(heartbeat_path, heartbeat_data)

        status = health_monitor.wait_for_healthy(timeout_seconds=5.0, poll_interval=0.1)

        assert status.healthy is True

    def test_wait_for_healthy_becomes_healthy(self, health_monitor, heartbeat_path):
        """Should wait until healthy."""
        import threading
        import time

        def write_heartbeat_delayed():
            time.sleep(0.2)
            heartbeat_data = {
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "unityVersion": "2022.3.10f1",
                "isCompiling": False,
                "isPlaying": False,
                "isPaused": False,
                "activeScene": "Scene",
                "commandsProcessed": 0,
                "uptimeSeconds": 0
            }
            write_heartbeat(heartbeat_path, heartbeat_data)

        # Start thread to write heartbeat after delay
        thread = threading.Thread(target=write_heartbeat_delayed)
        thread.start()

        status = health_monitor.wait_for_healthy(timeout_seconds=2.0, poll_interval=0.1)

        thread.join()

        assert status.healthy is True

    def test_wait_for_healthy_timeout(self, health_monitor):
        """Should timeout if never becomes healthy."""
        status = health_monitor.wait_for_healthy(timeout_seconds=0.2, poll_interval=0.05)

        assert status.healthy is False
        # Should have a reason - either timeout or last check reason
        assert status.reason is not None
        assert len(status.reason) > 0

    def test_wait_for_healthy_custom_poll_interval(self, health_monitor, heartbeat_path):
        """Should respect custom poll interval."""
        import time

        heartbeat_data = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "unityVersion": "2022.3.10f1",
            "isCompiling": False,
            "isPlaying": False,
            "isPaused": False,
            "activeScene": "Scene",
            "commandsProcessed": 0,
            "uptimeSeconds": 0
        }
        write_heartbeat(heartbeat_path, heartbeat_data)

        start = time.time()
        status = health_monitor.wait_for_healthy(timeout_seconds=1.0, poll_interval=0.05)
        elapsed = time.time() - start

        assert status.healthy is True
        assert elapsed < 0.2  # Should return quickly


class TestTimestampParsing:
    """Test various timestamp format handling."""

    def test_iso_format_with_z(self, health_monitor, heartbeat_path):
        """Should parse ISO format with Z suffix."""
        heartbeat_data = {
            "timestamp": "2025-01-06T12:30:45.123456Z",
            "unityVersion": "2022.3.10f1",
            "isCompiling": False,
            "isPlaying": False,
            "isPaused": False,
            "activeScene": "Scene",
            "commandsProcessed": 0,
            "uptimeSeconds": 0
        }
        write_heartbeat(heartbeat_path, heartbeat_data)

        status = health_monitor.check_health()

        # Will be unhealthy because timestamp is in the past, but should parse
        assert "invalid" not in status.reason.lower()

    def test_iso_format_with_offset(self, health_monitor, heartbeat_path):
        """Should parse ISO format with timezone offset."""
        heartbeat_data = {
            "timestamp": datetime.utcnow().isoformat() + "+00:00",
            "unityVersion": "2022.3.10f1",
            "isCompiling": False,
            "isPlaying": False,
            "isPaused": False,
            "activeScene": "Scene",
            "commandsProcessed": 0,
            "uptimeSeconds": 0
        }
        write_heartbeat(heartbeat_path, heartbeat_data)

        status = health_monitor.check_health()

        assert status.healthy is True


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_heartbeat_missing_optional_fields(self, health_monitor, heartbeat_path):
        """Should handle missing optional fields gracefully."""
        heartbeat_data = {
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }
        write_heartbeat(heartbeat_path, heartbeat_data)

        status = health_monitor.check_health()

        assert status.healthy is True
        assert status.unity_version is None
        assert status.is_compiling is False  # Defaults
        assert status.commands_processed == 0

    def test_heartbeat_with_extra_fields(self, health_monitor, heartbeat_path):
        """Should ignore extra unknown fields."""
        heartbeat_data = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "unityVersion": "2022.3.10f1",
            "isCompiling": False,
            "isPlaying": False,
            "isPaused": False,
            "activeScene": "Scene",
            "commandsProcessed": 0,
            "uptimeSeconds": 0,
            "extraField": "should be ignored",
            "anotherExtra": 12345
        }
        write_heartbeat(heartbeat_path, heartbeat_data)

        status = health_monitor.check_health()

        assert status.healthy is True

    def test_heartbeat_zero_uptime(self, health_monitor, heartbeat_path):
        """Should handle zero uptime (fresh Unity start)."""
        heartbeat_data = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "unityVersion": "2022.3.10f1",
            "isCompiling": False,
            "isPlaying": False,
            "isPaused": False,
            "activeScene": "",
            "commandsProcessed": 0,
            "uptimeSeconds": 0
        }
        write_heartbeat(heartbeat_path, heartbeat_data)

        status = health_monitor.check_health()

        assert status.healthy is True
        assert status.uptime_seconds == 0

    def test_heartbeat_very_long_uptime(self, health_monitor, heartbeat_path):
        """Should handle very large uptime values."""
        heartbeat_data = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "unityVersion": "2022.3.10f1",
            "isCompiling": False,
            "isPlaying": False,
            "isPaused": False,
            "activeScene": "Scene",
            "commandsProcessed": 999999,
            "uptimeSeconds": 86400 * 7  # 1 week
        }
        write_heartbeat(heartbeat_path, heartbeat_data)

        status = health_monitor.check_health()

        assert status.healthy is True
        assert status.uptime_seconds == 86400 * 7


# Skip all tests if module not yet implemented (TDD RED phase)
pytestmark = pytest.mark.skipif(
    HealthMonitor is None,
    reason="health_monitor module not yet implemented (TDD RED phase)"
)
