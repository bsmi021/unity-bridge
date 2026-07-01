"""Unit tests for commands/cinemachine.py — Cinemachine camera operations."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock


from unity_bridge.core.bridge import CommandResult


def _import_cinemachine():
    from unity_bridge.commands import cinemachine

    return cinemachine


# ---------------------------------------------------------------------------
# list-cameras
# ---------------------------------------------------------------------------


class TestListCameras:
    async def test_sends_correct_command_type(self, mock_bridge: MagicMock) -> None:
        mod = _import_cinemachine()
        await mod.cinemachine_list_cameras(mock_bridge)
        assert (
            _extract_command_type(mock_bridge.send_command_with_retry.call_args)
            == "cinemachine-operation"
        )

    async def test_sends_correct_parameters(self, mock_bridge: MagicMock) -> None:
        mod = _import_cinemachine()
        await mod.cinemachine_list_cameras(mock_bridge)
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert params == {"operation": "list-cameras"}

    async def test_default_timeout(self, mock_bridge: MagicMock) -> None:
        mod = _import_cinemachine()
        await mod.cinemachine_list_cameras(mock_bridge)
        assert _extract_kwarg(mock_bridge.send_command_with_retry.call_args, "timeout") == 15.0

    async def test_returns_camera_list(self, mock_bridge: MagicMock) -> None:
        mod = _import_cinemachine()
        expected = CommandResult(
            success=True,
            data={
                "operation": "list-cameras",
                "cameras": [
                    {"path": "Main/VCam1", "priority": 10, "enabled": True},
                    {"path": "Main/VCam2", "priority": 5, "enabled": False},
                ],
                "success": True,
            },
        )
        mock_bridge.send_command_with_retry.return_value = expected
        result = await mod.cinemachine_list_cameras(mock_bridge)
        assert len(result.data["cameras"]) == 2


# ---------------------------------------------------------------------------
# get-camera-info
# ---------------------------------------------------------------------------


class TestGetCameraInfo:
    async def test_sends_correct_command_type(self, mock_bridge: MagicMock) -> None:
        mod = _import_cinemachine()
        await mod.cinemachine_get_camera_info(mock_bridge, "Main/VCam1")
        assert (
            _extract_command_type(mock_bridge.send_command_with_retry.call_args)
            == "cinemachine-operation"
        )

    async def test_sends_correct_parameters(self, mock_bridge: MagicMock) -> None:
        mod = _import_cinemachine()
        await mod.cinemachine_get_camera_info(mock_bridge, "Main/VCam1")
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert params == {"operation": "get-camera-info", "cameraPath": "Main/VCam1"}

    async def test_default_timeout(self, mock_bridge: MagicMock) -> None:
        mod = _import_cinemachine()
        await mod.cinemachine_get_camera_info(mock_bridge, "Main/VCam1")
        assert _extract_kwarg(mock_bridge.send_command_with_retry.call_args, "timeout") == 15.0

    async def test_returns_camera_info(self, mock_bridge: MagicMock) -> None:
        mod = _import_cinemachine()
        expected = CommandResult(
            success=True,
            data={
                "operation": "get-camera-info",
                "priority": 10,
                "fieldOfView": 60.0,
                "follow": "Player",
                "lookAt": "Player",
                "success": True,
            },
        )
        mock_bridge.send_command_with_retry.return_value = expected
        result = await mod.cinemachine_get_camera_info(mock_bridge, "Main/VCam1")
        assert result.data["priority"] == 10
        assert result.data["follow"] == "Player"


# ---------------------------------------------------------------------------
# set-priority
# ---------------------------------------------------------------------------


class TestSetPriority:
    async def test_sends_correct_command_type(self, mock_bridge: MagicMock) -> None:
        mod = _import_cinemachine()
        await mod.cinemachine_set_priority(mock_bridge, "Main/VCam1", 20)
        assert (
            _extract_command_type(mock_bridge.send_command_with_retry.call_args)
            == "cinemachine-operation"
        )

    async def test_sends_correct_parameters(self, mock_bridge: MagicMock) -> None:
        mod = _import_cinemachine()
        await mod.cinemachine_set_priority(mock_bridge, "Main/VCam1", 20)
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert params == {
            "operation": "set-priority",
            "cameraPath": "Main/VCam1",
            "priority": 20,
        }

    async def test_default_timeout(self, mock_bridge: MagicMock) -> None:
        mod = _import_cinemachine()
        await mod.cinemachine_set_priority(mock_bridge, "Main/VCam1", 20)
        assert _extract_kwarg(mock_bridge.send_command_with_retry.call_args, "timeout") == 15.0


# ---------------------------------------------------------------------------
# set-lens
# ---------------------------------------------------------------------------


class TestSetLens:
    async def test_sends_correct_command_type(self, mock_bridge: MagicMock) -> None:
        mod = _import_cinemachine()
        await mod.cinemachine_set_lens(mock_bridge, "Main/VCam1", field_of_view=50.0)
        assert (
            _extract_command_type(mock_bridge.send_command_with_retry.call_args)
            == "cinemachine-operation"
        )

    async def test_sends_only_provided_field(self, mock_bridge: MagicMock) -> None:
        mod = _import_cinemachine()
        await mod.cinemachine_set_lens(mock_bridge, "Main/VCam1", field_of_view=50.0)
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert params == {
            "operation": "set-lens",
            "cameraPath": "Main/VCam1",
            "fieldOfView": 50.0,
        }

    async def test_sends_all_lens_fields(self, mock_bridge: MagicMock) -> None:
        mod = _import_cinemachine()
        await mod.cinemachine_set_lens(
            mock_bridge,
            "Main/VCam1",
            field_of_view=50.0,
            orthographic_size=5.0,
            near_clip_plane=0.3,
            far_clip_plane=1000.0,
            dutch=15.0,
        )
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert params["fieldOfView"] == 50.0
        assert params["orthographicSize"] == 5.0
        assert params["nearClipPlane"] == 0.3
        assert params["farClipPlane"] == 1000.0
        assert params["dutch"] == 15.0

    async def test_default_timeout(self, mock_bridge: MagicMock) -> None:
        mod = _import_cinemachine()
        await mod.cinemachine_set_lens(mock_bridge, "Main/VCam1", dutch=10.0)
        assert _extract_kwarg(mock_bridge.send_command_with_retry.call_args, "timeout") == 15.0


# ---------------------------------------------------------------------------
# set-follow
# ---------------------------------------------------------------------------


class TestSetFollow:
    async def test_sends_correct_command_type(self, mock_bridge: MagicMock) -> None:
        mod = _import_cinemachine()
        await mod.cinemachine_set_follow(mock_bridge, "Main/VCam1", "Player")
        assert (
            _extract_command_type(mock_bridge.send_command_with_retry.call_args)
            == "cinemachine-operation"
        )

    async def test_sends_correct_parameters(self, mock_bridge: MagicMock) -> None:
        mod = _import_cinemachine()
        await mod.cinemachine_set_follow(mock_bridge, "Main/VCam1", "Player")
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert params == {
            "operation": "set-follow",
            "cameraPath": "Main/VCam1",
            "followPath": "Player",
        }

    async def test_empty_follow_path_clears_target(self, mock_bridge: MagicMock) -> None:
        mod = _import_cinemachine()
        await mod.cinemachine_set_follow(mock_bridge, "Main/VCam1", "")
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert params["followPath"] == ""

    async def test_default_timeout(self, mock_bridge: MagicMock) -> None:
        mod = _import_cinemachine()
        await mod.cinemachine_set_follow(mock_bridge, "Main/VCam1", "Player")
        assert _extract_kwarg(mock_bridge.send_command_with_retry.call_args, "timeout") == 15.0


# ---------------------------------------------------------------------------
# set-lookat
# ---------------------------------------------------------------------------


class TestSetLookAt:
    async def test_sends_correct_command_type(self, mock_bridge: MagicMock) -> None:
        mod = _import_cinemachine()
        await mod.cinemachine_set_lookat(mock_bridge, "Main/VCam1", "Player")
        assert (
            _extract_command_type(mock_bridge.send_command_with_retry.call_args)
            == "cinemachine-operation"
        )

    async def test_sends_correct_parameters(self, mock_bridge: MagicMock) -> None:
        mod = _import_cinemachine()
        await mod.cinemachine_set_lookat(mock_bridge, "Main/VCam1", "Player")
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert params == {
            "operation": "set-lookat",
            "cameraPath": "Main/VCam1",
            "lookAtPath": "Player",
        }

    async def test_empty_lookat_path_clears_target(self, mock_bridge: MagicMock) -> None:
        mod = _import_cinemachine()
        await mod.cinemachine_set_lookat(mock_bridge, "Main/VCam1", "")
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert params["lookAtPath"] == ""

    async def test_default_timeout(self, mock_bridge: MagicMock) -> None:
        mod = _import_cinemachine()
        await mod.cinemachine_set_lookat(mock_bridge, "Main/VCam1", "Player")
        assert _extract_kwarg(mock_bridge.send_command_with_retry.call_args, "timeout") == 15.0


# ---------------------------------------------------------------------------
# get-active-camera
# ---------------------------------------------------------------------------


class TestGetActiveCamera:
    async def test_sends_correct_command_type(self, mock_bridge: MagicMock) -> None:
        mod = _import_cinemachine()
        await mod.cinemachine_get_active_camera(mock_bridge)
        assert (
            _extract_command_type(mock_bridge.send_command_with_retry.call_args)
            == "cinemachine-operation"
        )

    async def test_sends_correct_parameters(self, mock_bridge: MagicMock) -> None:
        mod = _import_cinemachine()
        await mod.cinemachine_get_active_camera(mock_bridge)
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert params == {"operation": "get-active-camera"}

    async def test_default_timeout(self, mock_bridge: MagicMock) -> None:
        mod = _import_cinemachine()
        await mod.cinemachine_get_active_camera(mock_bridge)
        assert _extract_kwarg(mock_bridge.send_command_with_retry.call_args, "timeout") == 15.0

    async def test_returns_active_camera_data(self, mock_bridge: MagicMock) -> None:
        mod = _import_cinemachine()
        expected = CommandResult(
            success=True,
            data={
                "operation": "get-active-camera",
                "activeCameraPath": "Main/VCam1",
                "isBlending": False,
                "success": True,
            },
        )
        mock_bridge.send_command_with_retry.return_value = expected
        result = await mod.cinemachine_get_active_camera(mock_bridge)
        assert result.data["activeCameraPath"] == "Main/VCam1"

    async def test_returns_not_found_when_no_brain(self, mock_bridge: MagicMock) -> None:
        mod = _import_cinemachine()
        expected = CommandResult(
            success=False,
            data={"operation": "get-active-camera"},
            error="No CinemachineBrain found on main camera.",
        )
        mock_bridge.send_command_with_retry.return_value = expected
        result = await mod.cinemachine_get_active_camera(mock_bridge)
        assert result.success is False


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
