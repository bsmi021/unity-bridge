"""Unit tests for commands/tags_layers.py — tags and layers management."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

from unity_bridge.commands.tags_layers import (
    add_layer,
    add_sorting_layer,
    add_tag,
    list_layers,
    list_sorting_layers,
    list_tags,
)


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


# ---------------------------------------------------------------------------
# list-tags
# ---------------------------------------------------------------------------


class TestListTags:
    async def test_sends_correct_command_type(self, mock_bridge: MagicMock) -> None:
        await list_tags(mock_bridge)
        cmd = _extract_command_type(mock_bridge.send_command_with_retry.call_args)
        assert cmd == "tags-layers"

    async def test_sends_list_tags_operation(self, mock_bridge: MagicMock) -> None:
        await list_tags(mock_bridge)
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert params["operation"] == "list-tags"

    async def test_bridge_error_propagated(self, failing_bridge: MagicMock) -> None:
        result = await list_tags(failing_bridge)
        assert result.success is False


# ---------------------------------------------------------------------------
# add-tag
# ---------------------------------------------------------------------------


class TestAddTag:
    async def test_sends_add_tag_operation(self, mock_bridge: MagicMock) -> None:
        await add_tag(mock_bridge, "Enemy")
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert params["operation"] == "add-tag"
        assert params["tagName"] == "Enemy"

    async def test_tag_with_spaces(self, mock_bridge: MagicMock) -> None:
        await add_tag(mock_bridge, "My Custom Tag")
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert params["tagName"] == "My Custom Tag"

    async def test_bridge_error_propagated(self, failing_bridge: MagicMock) -> None:
        result = await add_tag(failing_bridge, "Test")
        assert result.success is False


# ---------------------------------------------------------------------------
# list-layers
# ---------------------------------------------------------------------------


class TestListLayers:
    async def test_sends_list_layers_operation(self, mock_bridge: MagicMock) -> None:
        await list_layers(mock_bridge)
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert params["operation"] == "list-layers"

    async def test_bridge_error_propagated(self, failing_bridge: MagicMock) -> None:
        result = await list_layers(failing_bridge)
        assert result.success is False


# ---------------------------------------------------------------------------
# add-layer
# ---------------------------------------------------------------------------


class TestAddLayer:
    async def test_sends_add_layer_operation(self, mock_bridge: MagicMock) -> None:
        await add_layer(mock_bridge, "Interactable")
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert params["operation"] == "add-layer"
        assert params["layerName"] == "Interactable"

    async def test_with_specific_index(self, mock_bridge: MagicMock) -> None:
        await add_layer(mock_bridge, "Interactable", index=10)
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert params["layerIndex"] == 10

    async def test_without_index(self, mock_bridge: MagicMock) -> None:
        await add_layer(mock_bridge, "Interactable")
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert "layerIndex" not in params

    async def test_bridge_error_propagated(self, failing_bridge: MagicMock) -> None:
        result = await add_layer(failing_bridge, "Test")
        assert result.success is False


# ---------------------------------------------------------------------------
# sorting layers
# ---------------------------------------------------------------------------


class TestListSortingLayers:
    async def test_sends_list_sorting_layers(self, mock_bridge: MagicMock) -> None:
        await list_sorting_layers(mock_bridge)
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert params["operation"] == "list-sorting-layers"


class TestAddSortingLayer:
    async def test_sends_add_sorting_layer(self, mock_bridge: MagicMock) -> None:
        await add_sorting_layer(mock_bridge, "Background")
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert params["operation"] == "add-sorting-layer"
        assert params["sortingLayerName"] == "Background"


# ---------------------------------------------------------------------------
# Adversarial
# ---------------------------------------------------------------------------


class TestTagsLayersAdversarial:
    async def test_all_operations_use_send_command_with_retry(self, mock_bridge: MagicMock) -> None:
        await list_tags(mock_bridge)
        await add_tag(mock_bridge, "T")
        await list_layers(mock_bridge)
        await add_layer(mock_bridge, "L")
        await list_sorting_layers(mock_bridge)
        await add_sorting_layer(mock_bridge, "S")
        assert mock_bridge.send_command_with_retry.call_count == 6
        assert mock_bridge.send_command.call_count == 0

    async def test_all_target_correct_command(self, mock_bridge: MagicMock) -> None:
        await list_tags(mock_bridge)
        cmd = _extract_command_type(mock_bridge.send_command_with_retry.call_args)
        assert cmd == "tags-layers"
