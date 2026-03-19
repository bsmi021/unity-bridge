"""Unit tests for core/health.py — HealthMonitor and HealthStatus."""

from __future__ import annotations

import json
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

import pytest

from unity_bridge.core.health import HealthMonitor, HealthStatus


# ---------------------------------------------------------------------------
# HealthStatus dataclass
# ---------------------------------------------------------------------------


class TestHealthStatus:

    def test_healthy_defaults(self) -> None:
        status = HealthStatus(healthy=True)
        assert status.healthy is True
        assert status.reason is None
        assert status.heartbeat_age_seconds == 0.0

    def test_unhealthy_with_reason(self) -> None:
        status = HealthStatus(healthy=False, reason="stale heartbeat")
        assert not status.healthy
        assert status.reason == "stale heartbeat"

    def test_to_dict_camel_case_keys(self) -> None:
        status = HealthStatus(
            healthy=True,
            unity_version="6000.0.23f1",
            is_compiling=True,
            heartbeat_age_seconds=1.234,
        )
        d = status.to_dict()
        assert d["healthy"] is True
        assert d["unityVersion"] == "6000.0.23f1"
        assert d["isCompiling"] is True
        assert d["heartbeatAgeSeconds"] == 1.23  # rounded to 2 dp


# ---------------------------------------------------------------------------
# HealthMonitor.check_health
# ---------------------------------------------------------------------------


class TestCheckHealth:

    def test_fresh_heartbeat_is_healthy(self, tmp_path: Path) -> None:
        hb_path = tmp_path / ".claude" / "unity" / "heartbeat.json"
        hb_path.parent.mkdir(parents=True)
        hb = {
            "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "unityVersion": "6000.0.23f1",
            "isCompiling": False,
            "isPlaying": False,
            "isPaused": False,
            "activeScene": "Main",
            "commandsProcessed": 5,
            "uptimeSeconds": 60,
        }
        hb_path.write_text(json.dumps(hb), encoding="utf-8")

        monitor = HealthMonitor(tmp_path)
        status = monitor.check_health()
        assert status.healthy is True
        assert status.unity_version == "6000.0.23f1"
        assert status.heartbeat_age_seconds < 5.0

    def test_stale_heartbeat_is_unhealthy(self, tmp_path: Path) -> None:
        hb_path = tmp_path / ".claude" / "unity" / "heartbeat.json"
        hb_path.parent.mkdir(parents=True)
        old_ts = (datetime.now(timezone.utc) - timedelta(seconds=30)).isoformat()
        hb = {"timestamp": old_ts}
        hb_path.write_text(json.dumps(hb), encoding="utf-8")

        monitor = HealthMonitor(tmp_path)
        status = monitor.check_health()
        assert status.healthy is False
        assert "stale" in status.reason.lower()
        assert status.heartbeat_age_seconds > 15.0

    def test_missing_heartbeat_file(self, tmp_path: Path) -> None:
        monitor = HealthMonitor(tmp_path)
        status = monitor.check_health()
        assert status.healthy is False
        assert "no heartbeat" in status.reason.lower()

    def test_invalid_json_heartbeat(self, tmp_path: Path) -> None:
        hb_path = tmp_path / ".claude" / "unity" / "heartbeat.json"
        hb_path.parent.mkdir(parents=True)
        hb_path.write_text("{invalid json", encoding="utf-8")

        monitor = HealthMonitor(tmp_path)
        status = monitor.check_health()
        assert status.healthy is False
        assert "invalid" in status.reason.lower() or "json" in status.reason.lower()

    def test_invalid_timestamp_in_heartbeat(self, tmp_path: Path) -> None:
        hb_path = tmp_path / ".claude" / "unity" / "heartbeat.json"
        hb_path.parent.mkdir(parents=True)
        hb_path.write_text(json.dumps({"timestamp": "not-a-date"}), encoding="utf-8")

        monitor = HealthMonitor(tmp_path)
        status = monitor.check_health()
        assert status.healthy is False
        assert "timestamp" in status.reason.lower()

    def test_compiling_state_propagated(self, tmp_path: Path) -> None:
        hb_path = tmp_path / ".claude" / "unity" / "heartbeat.json"
        hb_path.parent.mkdir(parents=True)
        hb = {
            "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "isCompiling": True,
        }
        hb_path.write_text(json.dumps(hb), encoding="utf-8")

        monitor = HealthMonitor(tmp_path)
        status = monitor.check_health()
        assert status.healthy is True
        assert status.is_compiling is True

    def test_max_heartbeat_age_constant(self) -> None:
        assert HealthMonitor.MAX_HEARTBEAT_AGE_SECONDS == 15.0

    def test_heartbeat_path_property(self, tmp_path: Path) -> None:
        monitor = HealthMonitor(tmp_path)
        assert monitor.heartbeat_path == tmp_path / ".claude" / "unity" / "heartbeat.json"


# ---------------------------------------------------------------------------
# HealthMonitor.wait_for_healthy
# ---------------------------------------------------------------------------


class TestWaitForHealthy:

    def test_returns_immediately_if_healthy(self, tmp_path: Path) -> None:
        hb_path = tmp_path / ".claude" / "unity" / "heartbeat.json"
        hb_path.parent.mkdir(parents=True)
        hb = {
            "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "unityVersion": "6000.0.23f1",
        }
        hb_path.write_text(json.dumps(hb), encoding="utf-8")

        monitor = HealthMonitor(tmp_path)
        start = time.time()
        status = monitor.wait_for_healthy(timeout_seconds=5.0, poll_interval=0.1)
        elapsed = time.time() - start
        assert status.healthy is True
        assert elapsed < 2.0  # Should be near-instant

    def test_times_out_when_unhealthy(self, tmp_path: Path) -> None:
        monitor = HealthMonitor(tmp_path)
        start = time.time()
        status = monitor.wait_for_healthy(timeout_seconds=0.3, poll_interval=0.1)
        elapsed = time.time() - start
        assert status.healthy is False
        assert elapsed >= 0.3
        assert elapsed < 2.0  # Reasonable upper bound

    def test_becomes_healthy_during_wait(self, tmp_path: Path) -> None:
        hb_path = tmp_path / ".claude" / "unity" / "heartbeat.json"
        hb_path.parent.mkdir(parents=True)

        monitor = HealthMonitor(tmp_path)
        call_count = 0
        original_check = monitor.check_health

        def delayed_healthy() -> HealthStatus:
            nonlocal call_count
            call_count += 1
            if call_count >= 3:
                # Write a fresh heartbeat on the 3rd check
                hb = {
                    "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
                    "unityVersion": "6000.0.23f1",
                }
                hb_path.write_text(json.dumps(hb), encoding="utf-8")
            return original_check()

        with patch.object(monitor, "check_health", side_effect=delayed_healthy):
            status = monitor.wait_for_healthy(timeout_seconds=5.0, poll_interval=0.05)

        assert status.healthy is True
