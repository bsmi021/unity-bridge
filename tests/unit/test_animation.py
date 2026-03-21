"""Unit tests for commands/animation.py — Animation clip operations."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock


from unity_bridge.core.bridge import CommandResult


def _import_animation():
    from unity_bridge.commands import animation

    return animation


# ---------------------------------------------------------------------------
# create
# ---------------------------------------------------------------------------


class TestCreate:
    async def test_sends_correct_command_type(self, mock_bridge: MagicMock) -> None:
        mod = _import_animation()
        await mod.animation_create(mock_bridge, "Assets/Anim/Walk.anim")
        assert (
            _extract_command_type(mock_bridge.send_command_with_retry.call_args) == "animation-clip"
        )

    async def test_sends_correct_parameters(self, mock_bridge: MagicMock) -> None:
        mod = _import_animation()
        await mod.animation_create(mock_bridge, "Assets/Anim/Walk.anim", frame_rate=30.0)
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert params["operation"] == "create"
        assert params["clipPath"] == "Assets/Anim/Walk.anim"
        assert params["frameRate"] == 30.0

    async def test_returns_command_result(self, mock_bridge: MagicMock) -> None:
        mod = _import_animation()
        expected = CommandResult(
            success=True,
            data={"operation": "create", "clipPath": "Assets/Anim/Walk.anim", "success": True},
        )
        mock_bridge.send_command_with_retry.return_value = expected
        result = await mod.animation_create(mock_bridge, "Assets/Anim/Walk.anim")
        assert result.success is True


# ---------------------------------------------------------------------------
# get-info
# ---------------------------------------------------------------------------


class TestGetInfo:
    async def test_sends_correct_parameters(self, mock_bridge: MagicMock) -> None:
        mod = _import_animation()
        await mod.animation_get_info(mock_bridge, "Assets/Anim/Walk.anim")
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert params == {"operation": "get-info", "clipPath": "Assets/Anim/Walk.anim"}

    async def test_returns_clip_info(self, mock_bridge: MagicMock) -> None:
        mod = _import_animation()
        expected = CommandResult(
            success=True,
            data={
                "operation": "get-info",
                "length": 1.5,
                "frameRate": 30.0,
                "isLooping": True,
                "curveCount": 4,
                "eventCount": 1,
                "success": True,
            },
        )
        mock_bridge.send_command_with_retry.return_value = expected
        result = await mod.animation_get_info(mock_bridge, "Assets/Anim/Walk.anim")
        assert result.data["length"] == 1.5
        assert result.data["curveCount"] == 4


# ---------------------------------------------------------------------------
# get-curves
# ---------------------------------------------------------------------------


class TestGetCurves:
    async def test_sends_correct_parameters(self, mock_bridge: MagicMock) -> None:
        mod = _import_animation()
        await mod.animation_get_curves(mock_bridge, "Assets/Anim/Walk.anim")
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert params == {"operation": "get-curves", "clipPath": "Assets/Anim/Walk.anim"}


# ---------------------------------------------------------------------------
# set-curve
# ---------------------------------------------------------------------------


class TestSetCurve:
    async def test_sends_keyframes(self, mock_bridge: MagicMock) -> None:
        mod = _import_animation()
        kfs = [{"time": 0.0, "value": 0.0}, {"time": 1.0, "value": 1.0}]
        await mod.animation_set_curve(
            mock_bridge, "Assets/Anim/Walk.anim", "m_LocalPosition.y", kfs
        )
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert params["operation"] == "set-curve"
        assert params["propertyName"] == "m_LocalPosition.y"
        assert len(params["keyframes"]) == 2


# ---------------------------------------------------------------------------
# add-event
# ---------------------------------------------------------------------------


class TestAddEvent:
    async def test_sends_event_data(self, mock_bridge: MagicMock) -> None:
        mod = _import_animation()
        await mod.animation_add_event(
            mock_bridge, "Assets/Anim/Walk.anim", time=0.5, function_name="FootStep"
        )
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert params["operation"] == "add-event"
        assert params["eventTime"] == 0.5
        assert params["eventFunction"] == "FootStep"


# ---------------------------------------------------------------------------
# set-properties
# ---------------------------------------------------------------------------


class TestSetProperties:
    async def test_sends_looping(self, mock_bridge: MagicMock) -> None:
        mod = _import_animation()
        await mod.animation_set_properties(mock_bridge, "Assets/Anim/Walk.anim", looping=True)
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert params["operation"] == "set-properties"
        assert params["looping"] is True
        assert params["setLooping"] is True

    async def test_sends_wrap_mode(self, mock_bridge: MagicMock) -> None:
        mod = _import_animation()
        await mod.animation_set_properties(mock_bridge, "Assets/Anim/Walk.anim", wrap_mode="Loop")
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert params["wrapMode"] == "Loop"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _extract_parameters(call_args: Any) -> dict:
    if call_args.kwargs.get("parameters") is not None:
        return call_args.kwargs["parameters"]
    if len(call_args.args) >= 2:
        return call_args.args[1]
    return {}


def _extract_command_type(call_args: Any) -> str:
    if "command_type" in call_args.kwargs:
        return call_args.kwargs["command_type"]
    return call_args.args[0]


def _extract_kwarg(call_args: Any, key: str) -> Any:
    if key in call_args.kwargs:
        return call_args.kwargs[key]
    return None
