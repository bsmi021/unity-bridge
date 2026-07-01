"""Unit tests for Localization package commands."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any
from unittest.mock import MagicMock

from typer.testing import CliRunner

from unity_bridge.commands import localization
from unity_bridge.commands.localization import localization_app
from unity_bridge.core.output import OutputFormatter


def _call_args(mock: MagicMock) -> dict[str, Any]:
    call = mock.send_command_with_retry.call_args
    return call.kwargs if call.kwargs else dict(
        zip(["command_type", "parameters", "timeout"], call.args, strict=False)
    )


def _state(mock_bridge: MagicMock) -> SimpleNamespace:
    return SimpleNamespace(bridge=mock_bridge, formatter=OutputFormatter())


def _run(args: list[str], mock_bridge: MagicMock):
    runner = CliRunner()
    return runner.invoke(localization_app, args, obj=_state(mock_bridge))


class TestLocalizationCommands:
    async def test_list_locales_dispatches(self, mock_bridge: MagicMock) -> None:
        await localization.list_locales(mock_bridge)

        args = _call_args(mock_bridge)
        assert args["command_type"] == "localization"
        assert args["parameters"] == {"operation": "list-locales"}

    async def test_add_locale_dispatches(self, mock_bridge: MagicMock) -> None:
        await localization.add_locale(mock_bridge, locale_code="fr")

        args = _call_args(mock_bridge)
        assert args["command_type"] == "localization"
        assert args["parameters"] == {"operation": "add-locale", "localeCode": "fr"}

    async def test_remove_locale_dispatches(self, mock_bridge: MagicMock) -> None:
        await localization.remove_locale(mock_bridge, locale_code="fr")

        args = _call_args(mock_bridge)
        assert args["command_type"] == "localization"
        assert args["parameters"] == {"operation": "remove-locale", "localeCode": "fr"}

    async def test_get_selected_locale_dispatches(self, mock_bridge: MagicMock) -> None:
        await localization.get_selected_locale(mock_bridge)

        args = _call_args(mock_bridge)
        assert args["command_type"] == "localization"
        assert args["parameters"] == {"operation": "get-selected-locale"}

    async def test_set_selected_locale_dispatches(self, mock_bridge: MagicMock) -> None:
        await localization.set_selected_locale(mock_bridge, locale_code="de")

        args = _call_args(mock_bridge)
        assert args["command_type"] == "localization"
        assert args["parameters"] == {"operation": "set-selected-locale", "localeCode": "de"}

    async def test_create_string_table_collection_dispatches(
        self, mock_bridge: MagicMock
    ) -> None:
        await localization.create_string_table_collection(
            mock_bridge, table_collection_name="UI"
        )

        args = _call_args(mock_bridge)
        assert args["command_type"] == "localization"
        assert args["parameters"] == {
            "operation": "create-string-table-collection",
            "tableCollectionName": "UI",
        }

    async def test_get_string_table_collection_dispatches(
        self, mock_bridge: MagicMock
    ) -> None:
        await localization.get_string_table_collection(
            mock_bridge, table_collection_name="UI"
        )

        args = _call_args(mock_bridge)
        assert args["command_type"] == "localization"
        assert args["parameters"] == {
            "operation": "get-string-table-collection",
            "tableCollectionName": "UI",
        }

    async def test_add_entry_dispatches(self, mock_bridge: MagicMock) -> None:
        await localization.add_entry(
            mock_bridge,
            table_collection_name="UI",
            key="greeting",
            value="Hello",
        )

        args = _call_args(mock_bridge)
        assert args["command_type"] == "localization"
        assert args["parameters"] == {
            "operation": "add-entry",
            "tableCollectionName": "UI",
            "key": "greeting",
            "value": "Hello",
        }

    async def test_export_csv_dispatches(self, mock_bridge: MagicMock) -> None:
        await localization.export_csv(
            mock_bridge, table_collection_name="UI", file_path="out.csv"
        )

        args = _call_args(mock_bridge)
        assert args["command_type"] == "localization"
        assert args["parameters"] == {
            "operation": "export-csv",
            "tableCollectionName": "UI",
            "filePath": "out.csv",
        }

    async def test_import_csv_dispatches(self, mock_bridge: MagicMock) -> None:
        await localization.import_csv(
            mock_bridge, table_collection_name="UI", file_path="in.csv"
        )

        args = _call_args(mock_bridge)
        assert args["command_type"] == "localization"
        assert args["parameters"] == {
            "operation": "import-csv",
            "tableCollectionName": "UI",
            "filePath": "in.csv",
        }

    async def test_export_xliff_dispatches(self, mock_bridge: MagicMock) -> None:
        await localization.export_xliff(
            mock_bridge, table_collection_name="UI", file_path="out.xlf"
        )

        args = _call_args(mock_bridge)
        assert args["command_type"] == "localization"
        assert args["parameters"] == {
            "operation": "export-xliff",
            "tableCollectionName": "UI",
            "filePath": "out.xlf",
        }

    async def test_import_xliff_dispatches(self, mock_bridge: MagicMock) -> None:
        await localization.import_xliff(
            mock_bridge, table_collection_name="UI", file_path="in.xlf"
        )

        args = _call_args(mock_bridge)
        assert args["command_type"] == "localization"
        assert args["parameters"] == {
            "operation": "import-xliff",
            "tableCollectionName": "UI",
            "filePath": "in.xlf",
        }


class TestLocalizationCli:
    def test_list_locales_cli(self, mock_bridge: MagicMock) -> None:
        result = _run(["list-locales"], mock_bridge)

        assert result.exit_code == 0
        assert _call_args(mock_bridge)["parameters"] == {"operation": "list-locales"}

    def test_add_locale_cli(self, mock_bridge: MagicMock) -> None:
        result = _run(["add-locale", "fr"], mock_bridge)

        assert result.exit_code == 0
        assert _call_args(mock_bridge)["parameters"] == {
            "operation": "add-locale",
            "localeCode": "fr",
        }

    def test_remove_locale_cli(self, mock_bridge: MagicMock) -> None:
        result = _run(["remove-locale", "fr"], mock_bridge)

        assert result.exit_code == 0
        assert _call_args(mock_bridge)["parameters"] == {
            "operation": "remove-locale",
            "localeCode": "fr",
        }

    def test_get_selected_locale_cli(self, mock_bridge: MagicMock) -> None:
        result = _run(["get-selected-locale"], mock_bridge)

        assert result.exit_code == 0
        assert _call_args(mock_bridge)["parameters"] == {"operation": "get-selected-locale"}

    def test_set_selected_locale_cli(self, mock_bridge: MagicMock) -> None:
        result = _run(["set-selected-locale", "de"], mock_bridge)

        assert result.exit_code == 0
        assert _call_args(mock_bridge)["parameters"] == {
            "operation": "set-selected-locale",
            "localeCode": "de",
        }

    def test_create_string_table_collection_cli(self, mock_bridge: MagicMock) -> None:
        result = _run(["create-string-table-collection", "UI"], mock_bridge)

        assert result.exit_code == 0
        assert _call_args(mock_bridge)["parameters"] == {
            "operation": "create-string-table-collection",
            "tableCollectionName": "UI",
        }

    def test_get_string_table_collection_cli(self, mock_bridge: MagicMock) -> None:
        result = _run(["get-string-table-collection", "UI"], mock_bridge)

        assert result.exit_code == 0
        assert _call_args(mock_bridge)["parameters"] == {
            "operation": "get-string-table-collection",
            "tableCollectionName": "UI",
        }

    def test_add_entry_cli(self, mock_bridge: MagicMock) -> None:
        result = _run(["add-entry", "UI", "greeting", "Hello"], mock_bridge)

        assert result.exit_code == 0
        assert _call_args(mock_bridge)["parameters"] == {
            "operation": "add-entry",
            "tableCollectionName": "UI",
            "key": "greeting",
            "value": "Hello",
        }

    def test_export_csv_cli(self, mock_bridge: MagicMock) -> None:
        result = _run(["export-csv", "UI", "out.csv"], mock_bridge)

        assert result.exit_code == 0
        assert _call_args(mock_bridge)["parameters"] == {
            "operation": "export-csv",
            "tableCollectionName": "UI",
            "filePath": "out.csv",
        }

    def test_import_csv_cli(self, mock_bridge: MagicMock) -> None:
        result = _run(["import-csv", "UI", "in.csv"], mock_bridge)

        assert result.exit_code == 0
        assert _call_args(mock_bridge)["parameters"] == {
            "operation": "import-csv",
            "tableCollectionName": "UI",
            "filePath": "in.csv",
        }

    def test_export_xliff_cli(self, mock_bridge: MagicMock) -> None:
        result = _run(["export-xliff", "UI", "out.xlf"], mock_bridge)

        assert result.exit_code == 0
        assert _call_args(mock_bridge)["parameters"] == {
            "operation": "export-xliff",
            "tableCollectionName": "UI",
            "filePath": "out.xlf",
        }

    def test_import_xliff_cli(self, mock_bridge: MagicMock) -> None:
        result = _run(["import-xliff", "UI", "in.xlf"], mock_bridge)

        assert result.exit_code == 0
        assert _call_args(mock_bridge)["parameters"] == {
            "operation": "import-xliff",
            "tableCollectionName": "UI",
            "filePath": "in.xlf",
        }

    def test_cli_failure_path(self, failing_bridge: MagicMock) -> None:
        result = _run(["list-locales"], failing_bridge)

        assert result.exit_code != 0
