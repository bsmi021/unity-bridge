"""Shared fixtures for Unity Bridge test suite.

Provides mock bridges, fake project structures, and fixture data
loaders used across both unit and integration tests.
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

# ---------------------------------------------------------------------------
# Path setup — ensure src/ is importable
# ---------------------------------------------------------------------------

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_SRC_DIR = _PROJECT_ROOT / "src"
if str(_SRC_DIR) not in sys.path:
    sys.path.insert(0, str(_SRC_DIR))
# Also keep legacy root on path for old modules (response_cache, retry_handler)
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))


FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"


# ---------------------------------------------------------------------------
# Pytest configuration
# ---------------------------------------------------------------------------


def pytest_configure(config: pytest.Config) -> None:
    """Register custom markers."""
    config.addinivalue_line(
        "markers",
        "integration: mark test as integration test (may require Unity running)",
    )
    config.addinivalue_line("markers", "slow: mark test as slow running")


# ---------------------------------------------------------------------------
# Fixture-data loaders
# ---------------------------------------------------------------------------


@pytest.fixture()
def sample_hierarchy() -> dict[str, Any]:
    """Load sample_hierarchy.json fixture."""
    return json.loads((FIXTURES_DIR / "sample_hierarchy.json").read_text(encoding="utf-8"))


@pytest.fixture()
def sample_test_results() -> dict[str, Any]:
    """Load sample_test_results.json fixture."""
    return json.loads(
        (FIXTURES_DIR / "sample_test_results.json").read_text(encoding="utf-8")
    )


@pytest.fixture()
def sample_snapshot() -> dict[str, Any]:
    """Load sample_snapshot.json fixture."""
    return json.loads((FIXTURES_DIR / "sample_snapshot.json").read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# Fake project / heartbeat on disk
# ---------------------------------------------------------------------------


@pytest.fixture()
def fake_project(tmp_path: Path) -> Path:
    """Create a minimal Unity project structure in a temp directory.

    Returns the project root path.
    """
    (tmp_path / "Assets").mkdir()
    (tmp_path / "ProjectSettings").mkdir()
    claude_dir = tmp_path / ".claude" / "unity"
    (claude_dir / "commands").mkdir(parents=True)
    (claude_dir / "responses").mkdir(parents=True)
    return tmp_path


@pytest.fixture()
def fake_heartbeat(tmp_path: Path) -> Path:
    """Create a fresh heartbeat.json in a fake .claude/unity/ dir.

    Returns the path to the heartbeat file.
    """
    claude_dir = tmp_path / ".claude" / "unity"
    claude_dir.mkdir(parents=True, exist_ok=True)
    heartbeat_path = claude_dir / "heartbeat.json"
    heartbeat = {
        "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "unityVersion": "6000.0.23f1",
        "isCompiling": False,
        "isPlaying": False,
        "isPaused": False,
        "activeScene": "TestScene",
        "commandsProcessed": 10,
        "uptimeSeconds": 300,
    }
    heartbeat_path.write_text(json.dumps(heartbeat), encoding="utf-8")
    return heartbeat_path


# ---------------------------------------------------------------------------
# Mock bridges
# ---------------------------------------------------------------------------


def _make_command_result(
    success: bool = True,
    data: Any | None = None,
    error: str | None = None,
    exit_code: int = 0,
) -> Any:
    """Build a CommandResult without importing the real class (avoids
    import errors when core modules are still stubs).
    """
    from unity_bridge.core.bridge import CommandResult

    return CommandResult(
        success=success,
        data=data,
        error=error,
        command_id="test-0000",
        execution_time_ms=42,
        exit_code=exit_code,
        cached=False,
    )


@pytest.fixture()
def mock_bridge(fake_project: Path) -> MagicMock:
    """DirectBridge mock with ``send_command`` and ``send_command_with_retry``
    as AsyncMocks.  Default return is a successful CommandResult.
    """
    bridge = MagicMock()
    bridge.project_root = fake_project
    bridge.commands_path = fake_project / ".claude" / "unity" / "commands"
    bridge.responses_path = fake_project / ".claude" / "unity" / "responses"

    ok = _make_command_result(success=True, data={"status": "ok"})
    bridge.send_command = AsyncMock(return_value=ok)
    bridge.send_command_with_retry = AsyncMock(return_value=ok)
    return bridge


@pytest.fixture()
def healthy_bridge(mock_bridge: MagicMock) -> MagicMock:
    """Bridge mock whose commands always succeed."""
    result = _make_command_result(success=True, data={"healthy": True})
    mock_bridge.send_command.return_value = result
    mock_bridge.send_command_with_retry.return_value = result
    return mock_bridge


@pytest.fixture()
def failing_bridge(mock_bridge: MagicMock) -> MagicMock:
    """Bridge mock whose commands always fail."""
    result = _make_command_result(
        success=False, error="Unity Bridge not healthy", exit_code=2
    )
    mock_bridge.send_command.return_value = result
    mock_bridge.send_command_with_retry.return_value = result
    return mock_bridge
