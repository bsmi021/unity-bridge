"""Unit tests for commands/package.py — all 8 package operations."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

import pytest

from unity_bridge.commands.package import package_operation
from unity_bridge.core.bridge import CommandResult


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
# list
# ---------------------------------------------------------------------------


class TestPackageList:
    async def test_sends_correct_command_type(self, mock_bridge: MagicMock) -> None:
        await package_operation(mock_bridge, "list")
        cmd = _extract_command_type(mock_bridge.send_command_with_retry.call_args)
        assert cmd == "package-operation"

    async def test_sends_list_operation(self, mock_bridge: MagicMock) -> None:
        await package_operation(mock_bridge, "list")
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert params["operation"] == "list"

    async def test_offline_mode_included(self, mock_bridge: MagicMock) -> None:
        await package_operation(mock_bridge, "list", offline_mode=True)
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert params["offlineMode"] is True

    async def test_offline_mode_omitted_when_false(self, mock_bridge: MagicMock) -> None:
        await package_operation(mock_bridge, "list", offline_mode=False)
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert "offlineMode" not in params

    async def test_include_indirect_included(self, mock_bridge: MagicMock) -> None:
        await package_operation(mock_bridge, "list", include_indirect=True)
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert params["includeIndirectDependencies"] is True

    async def test_source_filter_included(self, mock_bridge: MagicMock) -> None:
        await package_operation(mock_bridge, "list", source="registry")
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert params["source"] == "registry"

    async def test_returns_command_result(self, mock_bridge: MagicMock) -> None:
        expected = CommandResult(
            success=True, data={"operation": "list", "packages": [], "totalCount": 0}
        )
        mock_bridge.send_command_with_retry.return_value = expected
        result = await package_operation(mock_bridge, "list")
        assert result.success is True
        assert result.data["totalCount"] == 0


# ---------------------------------------------------------------------------
# search
# ---------------------------------------------------------------------------


class TestPackageSearch:
    async def test_sends_search_with_query(self, mock_bridge: MagicMock) -> None:
        await package_operation(mock_bridge, "search", query="textmeshpro")
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert params["operation"] == "search"
        assert params["query"] == "textmeshpro"


# ---------------------------------------------------------------------------
# search-all
# ---------------------------------------------------------------------------


class TestPackageSearchAll:
    async def test_sends_search_all(self, mock_bridge: MagicMock) -> None:
        await package_operation(mock_bridge, "search-all")
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert params["operation"] == "search-all"


# ---------------------------------------------------------------------------
# add
# ---------------------------------------------------------------------------


class TestPackageAdd:
    async def test_sends_add_with_identifier(self, mock_bridge: MagicMock) -> None:
        await package_operation(mock_bridge, "add", identifier="com.unity.textmeshpro@3.0.6")
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert params["operation"] == "add"
        assert params["identifier"] == "com.unity.textmeshpro@3.0.6"

    async def test_add_with_git_url(self, mock_bridge: MagicMock) -> None:
        url = "https://github.com/user/repo.git#v1.0.0"
        await package_operation(mock_bridge, "add", identifier=url)
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert params["identifier"] == url


# ---------------------------------------------------------------------------
# batch
# ---------------------------------------------------------------------------


class TestPackageBatch:
    async def test_sends_batch_with_adds_and_removes(self, mock_bridge: MagicMock) -> None:
        await package_operation(
            mock_bridge,
            "batch",
            packages_to_add=["com.unity.inputsystem@1.7.0"],
            packages_to_remove=["com.unity.timeline"],
        )
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert params["operation"] == "batch"
        assert params["packagesToAdd"] == ["com.unity.inputsystem@1.7.0"]
        assert params["packagesToRemove"] == ["com.unity.timeline"]


# ---------------------------------------------------------------------------
# pack
# ---------------------------------------------------------------------------


class TestPackagePack:
    async def test_sends_pack_paths(self, mock_bridge: MagicMock) -> None:
        await package_operation(
            mock_bridge,
            "pack",
            package_folder="Packages/com.company.tools",
            target_folder="Build/Packages",
        )
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert params["operation"] == "pack"
        assert params["packageFolder"] == "Packages/com.company.tools"
        assert params["targetFolder"] == "Build/Packages"


# ---------------------------------------------------------------------------
# clear-cache
# ---------------------------------------------------------------------------


class TestPackageClearCache:
    async def test_sends_clear_cache_confirmation(self, mock_bridge: MagicMock) -> None:
        await package_operation(mock_bridge, "clear-cache", confirm_clear_cache=True)
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert params["operation"] == "clear-cache"
        assert params["confirmClearCache"] is True


# ---------------------------------------------------------------------------
# remove
# ---------------------------------------------------------------------------


class TestPackageRemove:
    async def test_sends_remove_with_name(self, mock_bridge: MagicMock) -> None:
        await package_operation(mock_bridge, "remove", package_name="com.unity.textmeshpro")
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert params["operation"] == "remove"
        assert params["packageName"] == "com.unity.textmeshpro"


# ---------------------------------------------------------------------------
# info
# ---------------------------------------------------------------------------


class TestPackageInfo:
    async def test_sends_info_with_name(self, mock_bridge: MagicMock) -> None:
        await package_operation(mock_bridge, "info", package_name="com.unity.textmeshpro")
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert params["operation"] == "info"
        assert params["packageName"] == "com.unity.textmeshpro"


# ---------------------------------------------------------------------------
# embed
# ---------------------------------------------------------------------------


class TestPackageEmbed:
    async def test_sends_embed_with_name(self, mock_bridge: MagicMock) -> None:
        await package_operation(mock_bridge, "embed", package_name="com.unity.textmeshpro")
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert params["operation"] == "embed"
        assert params["packageName"] == "com.unity.textmeshpro"


# ---------------------------------------------------------------------------
# resolve
# ---------------------------------------------------------------------------


class TestPackageResolve:
    async def test_sends_resolve(self, mock_bridge: MagicMock) -> None:
        await package_operation(mock_bridge, "resolve")
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert params["operation"] == "resolve"

    async def test_resolve_no_extra_params(self, mock_bridge: MagicMock) -> None:
        await package_operation(mock_bridge, "resolve")
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert len(params) == 1  # only "operation"


# ---------------------------------------------------------------------------
# Validation and general
# ---------------------------------------------------------------------------


class TestPackageValidation:
    async def test_invalid_action_raises(self, mock_bridge: MagicMock) -> None:
        with pytest.raises(ValueError, match="Invalid package action"):
            await package_operation(mock_bridge, "not-a-real-op")

    async def test_action_normalised(self, mock_bridge: MagicMock) -> None:
        await package_operation(mock_bridge, "  LIST  ")
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert params["operation"] == "list"

    async def test_timeout_passed_through(self, mock_bridge: MagicMock) -> None:
        await package_operation(mock_bridge, "list", timeout=120.0)
        timeout = _extract_kwarg(mock_bridge.send_command_with_retry.call_args, "timeout")
        assert timeout == 120.0

    async def test_default_timeout_is_60(self, mock_bridge: MagicMock) -> None:
        await package_operation(mock_bridge, "list")
        timeout = _extract_kwarg(mock_bridge.send_command_with_retry.call_args, "timeout")
        assert timeout == 60.0
