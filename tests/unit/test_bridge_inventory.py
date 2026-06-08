"""Inventory tests for ClaudeCodeBridge C# assets."""

from __future__ import annotations

import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
BRIDGE_DIR = ROOT / "ClaudeCodeBridge"
REGISTRY_FILE = BRIDGE_DIR / "BridgeCommandRegistry.cs"

GUID_PATTERN = re.compile(r"^guid:\s*([0-9a-f]{32})\s*$", re.MULTILINE)
REGISTERED_HANDLER_PATTERN = re.compile(
    r"registerHandler\s*\(\s*new\s+([A-Za-z_][A-Za-z0-9_]*)\s*\("
)


def test_all_bridge_csharp_files_have_meta() -> None:
    # Arrange
    csharp_files = sorted(BRIDGE_DIR.glob("*.cs"))

    # Act
    missing_meta = [
        source_path.name
        for source_path in csharp_files
        if not source_path.with_name(f"{source_path.name}.meta").exists()
    ]

    # Assert
    assert missing_meta == []


def test_bridge_meta_guids_are_present_and_unique() -> None:
    # Arrange
    meta_files = sorted(BRIDGE_DIR.glob("*.meta"))

    # Act
    guid_by_file = {
        meta_file.name: _read_guid(meta_file)
        for meta_file in meta_files
    }
    missing_guid = [
        file_name
        for file_name, guid in guid_by_file.items()
        if guid is None
    ]
    duplicate_guids = sorted({
        guid
        for guid in guid_by_file.values()
        if guid is not None and list(guid_by_file.values()).count(guid) > 1
    })

    # Assert
    assert missing_guid == []
    assert duplicate_guids == []


def test_registered_csharp_handler_files_exist() -> None:
    # Arrange
    registry_text = REGISTRY_FILE.read_text(encoding="utf-8")

    # Act
    handler_names = sorted(set(REGISTERED_HANDLER_PATTERN.findall(registry_text)))
    missing_handlers = [
        handler_name
        for handler_name in handler_names
        if not (BRIDGE_DIR / f"{handler_name}.cs").exists()
    ]

    # Assert
    assert handler_names
    assert missing_handlers == []


def test_unity64_core_package_handlers_are_registered() -> None:
    # Arrange
    registry_text = REGISTRY_FILE.read_text(encoding="utf-8")

    # Act
    registered_handlers = set(REGISTERED_HANDLER_PATTERN.findall(registry_text))

    # Assert
    assert {
        "EntitiesCommandHandler",
        "AdaptivePerformanceCommandHandler",
        "MultiplayerPlayModeCommandHandler",
    } <= registered_handlers


def _read_guid(meta_file: Path) -> str | None:
    match = GUID_PATTERN.search(meta_file.read_text(encoding="utf-8"))
    if match is None:
        return None
    return match.group(1)
