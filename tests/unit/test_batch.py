"""Unit tests for commands/batch.py — parallel-safety classification (B1).

These tests assert that a parallel batch never executes *mutating* commands
concurrently, even when the command type appears in PARALLEL_SAFE_COMMANDS but
the specific operation mutates Unity state (e.g. transform-operation "set").
"""

from __future__ import annotations

import asyncio
from typing import Any

from unity_bridge.commands.batch import batch_execute
from unity_bridge.core.bridge import CommandResult


class _ConcurrencyTrackingBridge:
    """Fake bridge that records the peak number of overlapping commands."""

    def __init__(self) -> None:
        self._active = 0
        self.max_concurrency = 0

    async def send_command(
        self,
        command_type: str,
        parameters: dict[str, Any] | None = None,
        timeout: float = 30.0,
    ) -> CommandResult:
        self._active += 1
        self.max_concurrency = max(self.max_concurrency, self._active)
        try:
            await asyncio.sleep(0.02)  # hold the slot so overlaps are observable
        finally:
            self._active -= 1
        return CommandResult(success=True, data={}, command_id="x")


async def test_parallel_read_only_commands_overlap() -> None:
    bridge = _ConcurrencyTrackingBridge()
    commands = [
        {"type": "transform-operation", "parameters": {"operation": "get"}},
        {"type": "transform-operation", "parameters": {"operation": "get"}},
    ]
    await batch_execute(bridge, commands, parallel=True)
    assert bridge.max_concurrency == 2


async def test_parallel_mutating_transform_runs_sequentially() -> None:
    bridge = _ConcurrencyTrackingBridge()
    commands = [
        {"type": "transform-operation", "parameters": {"operation": "set"}},
        {"type": "transform-operation", "parameters": {"operation": "set"}},
    ]
    await batch_execute(bridge, commands, parallel=True)
    assert bridge.max_concurrency == 1


async def test_parallel_mixed_serialized_property_isolates_writes() -> None:
    bridge = _ConcurrencyTrackingBridge()
    commands = [
        {"type": "serialized-property", "parameters": {"operation": "set"}},
        {"type": "serialized-property", "parameters": {"operation": "set"}},
    ]
    await batch_execute(bridge, commands, parallel=True)
    assert bridge.max_concurrency == 1
