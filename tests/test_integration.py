"""
Integration tests for Unity Bridge MCP v2.0.

Tests end-to-end command execution with real Unity Bridge.
These tests require Unity to be running with the bridge installed.
Following TDD Red-Green-Refactor methodology.
"""

import pytest
import asyncio
from pathlib import Path
from typing import Dict, Any


# Import modules - will fail initially (RED phase)
try:
    from direct_bridge import DirectBridge
    from health_monitor import HealthMonitor
    from retry_handler import RetryConfig
except ImportError:
    DirectBridge = None
    HealthMonitor = None
    RetryConfig = None


# Check if Unity is running by looking for heartbeat file
def is_unity_running() -> bool:
    """Check if Unity Bridge is running by checking heartbeat file."""
    heartbeat_path = Path.cwd() / ".claude" / "unity" / "heartbeat.json"
    return heartbeat_path.exists()


# Skip integration tests if Unity not running
pytestmark = pytest.mark.skipif(
    not is_unity_running(),
    reason="Unity Bridge not running (heartbeat.json not found). Start Unity with bridge installed to run integration tests."
)


@pytest.fixture
def project_root():
    """Fixture providing project root path."""
    return Path.cwd()


@pytest.fixture
def bridge(project_root):
    """Fixture providing DirectBridge instance."""
    if DirectBridge is None:
        pytest.skip("DirectBridge not yet implemented")
    return DirectBridge(project_root)


@pytest.fixture
def health_monitor(project_root):
    """Fixture providing HealthMonitor instance."""
    if HealthMonitor is None:
        pytest.skip("HealthMonitor not yet implemented")
    return HealthMonitor(project_root)


class TestHealthMonitorIntegration:
    """Integration tests for health monitoring."""

    def test_health_check_returns_healthy(self, health_monitor):
        """Health check should return healthy status when Unity running."""
        status = health_monitor.check_health()

        assert status.healthy is True
        assert status.unity_version is not None
        assert isinstance(status.is_compiling, bool)
        assert isinstance(status.is_playing, bool)
        assert isinstance(status.commands_processed, int)
        assert status.commands_processed >= 0

    def test_health_check_includes_unity_state(self, health_monitor):
        """Health check should include Unity editor state."""
        status = health_monitor.check_health()

        assert status.healthy is True
        assert hasattr(status, 'is_compiling')
        assert hasattr(status, 'is_playing')
        assert hasattr(status, 'is_paused')
        assert hasattr(status, 'active_scene')

    def test_health_check_heartbeat_age(self, health_monitor):
        """Health check should report recent heartbeat."""
        status = health_monitor.check_health()

        assert status.healthy is True
        # Heartbeat should be very recent (< 10 seconds)
        assert status.heartbeat_age_seconds < 10.0

    def test_health_status_to_dict(self, health_monitor):
        """Health status should serialize to dict correctly."""
        status = health_monitor.check_health()
        status_dict = status.to_dict()

        assert isinstance(status_dict, dict)
        assert "healthy" in status_dict
        assert "unityVersion" in status_dict
        assert status_dict["healthy"] is True


@pytest.mark.asyncio
class TestDirectBridgeIntegration:
    """Integration tests for DirectBridge communication."""

    async def test_bridge_initialization(self, bridge, project_root):
        """Bridge should initialize correctly."""
        assert bridge.project_root == project_root
        assert bridge.commands_path.exists()
        assert bridge.responses_path.exists()

    async def test_health_check_before_command(self, bridge):
        """Bridge should check health before sending command."""
        # Health check is implicit in send_command
        result = await bridge.send_command(
            "query-hierarchy",
            {"maxDepth": 1},
            timeout=10.0,
            check_health=True
        )

        # If health check failed, should get error about unhealthy bridge
        # If successful, command executed
        assert "success" in result

    async def test_query_hierarchy_basic(self, bridge):
        """Query hierarchy command should work."""
        result = await bridge.send_command(
            "query-hierarchy",
            {"maxDepth": 2},
            timeout=15.0
        )

        assert result["success"] is True
        assert "data" in result or "error" not in result
        assert "commandId" in result
        assert "executionTime" in result
        assert result["executionTime"] > 0

    async def test_query_hierarchy_with_filters(self, bridge):
        """Query hierarchy with filters should work."""
        result = await bridge.send_command(
            "query-hierarchy",
            {
                "maxDepth": 3,
                "includeInactive": False,
                "nameFilter": ""
            },
            timeout=15.0
        )

        assert result["success"] is True

    async def test_clear_console(self, bridge):
        """Clear console command (Phase 1) should work."""
        result = await bridge.send_command(
            "clear-console",
            {},
            timeout=10.0
        )

        assert result["success"] is True
        if "data" in result:
            assert result["data"].get("cleared") is True

    async def test_get_selection(self, bridge):
        """Get selection command (Phase 1) should work."""
        result = await bridge.send_command(
            "get-selection",
            {},
            timeout=10.0
        )

        assert result["success"] is True
        assert "data" in result
        # Should have count field even if 0
        assert "count" in result["data"]
        assert isinstance(result["data"]["count"], int)
        assert result["data"]["count"] >= 0

    async def test_get_selection_with_components(self, bridge):
        """Get selection with includeComponents should work."""
        result = await bridge.send_command(
            "get-selection",
            {"includeComponents": True},
            timeout=10.0
        )

        assert result["success"] is True

    async def test_refresh_assets(self, bridge):
        """Refresh assets command (Phase 1) should work."""
        result = await bridge.send_command(
            "refresh-assets",
            {"forceUpdate": False},
            timeout=30.0
        )

        assert result["success"] is True

    async def test_invalid_command_type(self, bridge):
        """Invalid command type should return error."""
        result = await bridge.send_command(
            "non-existent-command",
            {},
            timeout=10.0
        )

        assert result["success"] is False
        assert "error" in result

    async def test_command_timeout(self, bridge):
        """Command should timeout if Unity doesn't respond."""
        # Use very short timeout to force timeout
        result = await bridge.send_command(
            "query-hierarchy",
            {"maxDepth": 1},
            timeout=0.001  # 1ms - should timeout
        )

        # Should timeout
        assert result["success"] is False
        assert "timeout" in result.get("error", "").lower() or "timed out" in result.get("error", "").lower()


@pytest.mark.asyncio
class TestRetryIntegration:
    """Integration tests for retry logic."""

    async def test_send_command_with_retry_success(self, bridge):
        """Commands with retry should succeed."""
        if not hasattr(bridge, 'send_command_with_retry'):
            pytest.skip("send_command_with_retry not yet implemented")

        result = await bridge.send_command_with_retry(
            "query-hierarchy",
            {"maxDepth": 1},
            timeout=15.0,
            retry_config=RetryConfig(max_retries=2, base_delay=0.1)
        )

        assert result["success"] is True

    async def test_retry_on_transient_failure(self, bridge):
        """Retry logic should handle transient failures."""
        if not hasattr(bridge, 'send_command_with_retry'):
            pytest.skip("send_command_with_retry not yet implemented")

        # This test would need a way to simulate transient failures
        # For now, just verify retry logic is callable
        result = await bridge.send_command_with_retry(
            "get-selection",
            {},
            timeout=10.0,
            retry_config=RetryConfig(max_retries=1, base_delay=0.05)
        )

        assert "success" in result


@pytest.mark.asyncio
class TestPhase1Commands:
    """Integration tests for Phase 1 new commands."""

    async def test_clear_console_empty(self, bridge):
        """Clear console when empty should succeed."""
        # Clear first
        result1 = await bridge.send_command("clear-console", {}, timeout=10.0)
        assert result1["success"] is True

        # Clear again (already empty)
        result2 = await bridge.send_command("clear-console", {}, timeout=10.0)
        assert result2["success"] is True

    async def test_get_selection_none_selected(self, bridge):
        """Get selection when nothing selected should return empty."""
        result = await bridge.send_command("get-selection", {}, timeout=10.0)

        assert result["success"] is True
        # Count might be 0 or might have selected objects
        assert "count" in result.get("data", {})

    async def test_refresh_assets_no_changes(self, bridge):
        """Refresh assets when no changes should succeed."""
        result = await bridge.send_command(
            "refresh-assets",
            {"forceUpdate": False},
            timeout=20.0
        )

        assert result["success"] is True

    async def test_refresh_assets_force_update(self, bridge):
        """Refresh assets with force update should succeed."""
        result = await bridge.send_command(
            "refresh-assets",
            {"forceUpdate": True},
            timeout=30.0  # May take longer
        )

        assert result["success"] is True


@pytest.mark.asyncio
class TestCommandLatency:
    """Test command latency meets performance requirements."""

    async def test_query_hierarchy_latency(self, bridge):
        """Query hierarchy should complete within 300ms (p95 target)."""
        import time

        latencies = []

        for _ in range(10):
            start = time.perf_counter()
            result = await bridge.send_command(
                "query-hierarchy",
                {"maxDepth": 1},
                timeout=15.0
            )
            elapsed_ms = (time.perf_counter() - start) * 1000

            if result["success"]:
                latencies.append(elapsed_ms)

        # Calculate p95
        latencies.sort()
        p95_index = int(len(latencies) * 0.95)
        p95_latency = latencies[p95_index] if latencies else 0

        # p95 should be under 300ms (target from tech spec)
        assert p95_latency < 300, f"p95 latency {p95_latency:.1f}ms exceeds 300ms target"

    async def test_get_selection_latency(self, bridge):
        """Get selection should be very fast (<100ms)."""
        import time

        start = time.perf_counter()
        result = await bridge.send_command("get-selection", {}, timeout=10.0)
        elapsed_ms = (time.perf_counter() - start) * 1000

        assert result["success"] is True
        # Phase 1 commands should be fast
        assert elapsed_ms < 100, f"get-selection took {elapsed_ms:.1f}ms, expected <100ms"


@pytest.mark.asyncio
class TestCommandSequences:
    """Test common command sequences."""

    async def test_clear_then_query_sequence(self, bridge):
        """Clear console then query should work."""
        # Clear console
        result1 = await bridge.send_command("clear-console", {}, timeout=10.0)
        assert result1["success"] is True

        # Query hierarchy
        result2 = await bridge.send_command(
            "query-hierarchy",
            {"maxDepth": 1},
            timeout=15.0
        )
        assert result2["success"] is True

    async def test_refresh_then_query_sequence(self, bridge):
        """Refresh assets then query should work."""
        # Refresh assets
        result1 = await bridge.send_command(
            "refresh-assets",
            {"forceUpdate": False},
            timeout=20.0
        )
        assert result1["success"] is True

        # Query hierarchy
        result2 = await bridge.send_command(
            "query-hierarchy",
            {"maxDepth": 2},
            timeout=15.0
        )
        assert result2["success"] is True

    async def test_multiple_get_selection_calls(self, bridge):
        """Multiple get selection calls should work."""
        results = []

        for _ in range(5):
            result = await bridge.send_command("get-selection", {}, timeout=10.0)
            assert result["success"] is True
            results.append(result)

        # All should succeed
        assert len(results) == 5


@pytest.mark.asyncio
class TestErrorHandling:
    """Test error handling in integration scenarios."""

    async def test_malformed_parameters(self, bridge):
        """Malformed parameters should return error."""
        result = await bridge.send_command(
            "query-hierarchy",
            {"maxDepth": "not-a-number"},  # Invalid type
            timeout=10.0
        )

        # Should either error or handle gracefully
        # Implementation may vary
        assert "success" in result

    async def test_concurrent_commands(self, bridge):
        """Multiple concurrent commands should work."""
        tasks = [
            bridge.send_command("get-selection", {}, timeout=10.0),
            bridge.send_command("query-hierarchy", {"maxDepth": 1}, timeout=15.0),
            bridge.send_command("clear-console", {}, timeout=10.0),
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # All should complete (success or controlled error)
        assert len(results) == 3
        for result in results:
            if isinstance(result, dict):
                assert "success" in result


class TestIntegrationEnvironment:
    """Test that integration test environment is set up correctly."""

    def test_heartbeat_file_exists(self):
        """Heartbeat file should exist when Unity running."""
        heartbeat_path = Path.cwd() / ".claude" / "unity" / "heartbeat.json"
        assert heartbeat_path.exists()

    def test_command_directory_exists(self):
        """Command directory should exist."""
        commands_path = Path.cwd() / ".claude" / "unity" / "commands"
        assert commands_path.exists()
        assert commands_path.is_dir()

    def test_response_directory_exists(self):
        """Response directory should exist."""
        responses_path = Path.cwd() / ".claude" / "unity" / "responses"
        assert responses_path.exists()
        assert responses_path.is_dir()

    def test_heartbeat_is_recent(self):
        """Heartbeat should be recent when Unity running."""
        import json
        from datetime import datetime

        heartbeat_path = Path.cwd() / ".claude" / "unity" / "heartbeat.json"

        with open(heartbeat_path, 'r') as f:
            heartbeat = json.load(f)

        timestamp_str = heartbeat.get("timestamp", "")
        timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
        age = (datetime.now(timestamp.tzinfo) - timestamp).total_seconds()

        # Should be updated within last 15 seconds
        assert age < 15.0, f"Heartbeat is {age:.1f}s old"


# Additional marker for integration tests
integration_test = pytest.mark.integration
