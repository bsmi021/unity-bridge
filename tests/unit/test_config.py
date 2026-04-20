"""Unit tests for core/config.py — BridgeConfig, load/save config file."""

from __future__ import annotations

import json
import os
from pathlib import Path
from unittest.mock import patch


from unity_bridge.core.config import BridgeConfig, load_config_file, save_config_file


# ---------------------------------------------------------------------------
# BridgeConfig defaults
# ---------------------------------------------------------------------------


class TestBridgeConfigDefaults:

    def test_default_values(self) -> None:
        config = BridgeConfig()
        assert config.project_root is None
        assert config.log_level == "ERROR"
        assert config.output_format == "json"
        assert config.default_timeout == 30
        assert config.color is True

    def test_custom_values(self) -> None:
        config = BridgeConfig(
            project_root=Path("/my/project"),
            log_level="DEBUG",
            output_format="human",
            default_timeout=60,
            color=False,
        )
        assert config.project_root == Path("/my/project")
        assert config.log_level == "DEBUG"
        assert config.output_format == "human"
        assert config.default_timeout == 60
        assert config.color is False


# ---------------------------------------------------------------------------
# Config precedence: CLI > env > file > defaults
# ---------------------------------------------------------------------------


class TestConfigPrecedence:

    def test_cli_flags_override_env_vars(self) -> None:
        env = {"UNITY_BRIDGE_TIMEOUT": "100", "UNITY_BRIDGE_LOG_LEVEL": "INFO"}
        with patch.dict(os.environ, env, clear=False):
            config = BridgeConfig.resolve(cli_timeout=42, cli_verbose=True)
        assert config.default_timeout == 42
        assert config.log_level == "DEBUG"  # verbose -> DEBUG

    def test_env_vars_override_defaults(self) -> None:
        env = {
            "UNITY_BRIDGE_TIMEOUT": "120",
            "UNITY_BRIDGE_LOG_LEVEL": "WARNING",
        }
        with patch.dict(os.environ, env, clear=False):
            config = BridgeConfig.resolve()
        assert config.default_timeout == 120
        assert config.log_level == "WARNING"

    def test_no_color_env_via_from_env(self) -> None:
        """NO_COLOR env var disables color in from_env()."""
        with patch.dict(os.environ, {"NO_COLOR": "1"}, clear=False):
            config = BridgeConfig.from_env()
        assert config.color is False

    def test_cli_no_color_flag(self) -> None:
        config = BridgeConfig.resolve(cli_no_color=True)
        assert config.color is False

    def test_quiet_flag_sets_critical(self) -> None:
        config = BridgeConfig.resolve(cli_quiet=True)
        # Quiet should suppress most output — typically maps to CRITICAL or OFF
        assert config.log_level in ("CRITICAL", "OFF")

    def test_from_env_reads_project(self) -> None:
        with patch.dict(os.environ, {"UNITY_BRIDGE_PROJECT": "/some/path"}, clear=False):
            config = BridgeConfig.from_env()
        assert config.project_root == Path("/some/path")


# ---------------------------------------------------------------------------
# Config file loading / saving
# ---------------------------------------------------------------------------


class TestConfigFile:

    def test_load_valid_config_file(self, tmp_path: Path) -> None:
        cfg_file = tmp_path / "unity_bridge_config.json"
        cfg_file.write_text(
            json.dumps({
                "log_level": "DEBUG",
                "default_timeout": 60,
                "color": False,
            }),
            encoding="utf-8",
        )
        data = load_config_file(cfg_file)
        assert data["log_level"] == "DEBUG"
        assert data["default_timeout"] == 60

    def test_load_missing_config_returns_empty(self, tmp_path: Path) -> None:
        missing = tmp_path / "nonexistent.json"
        data = load_config_file(missing)
        assert data == {}

    def test_load_invalid_json_returns_empty(self, tmp_path: Path) -> None:
        bad = tmp_path / "bad.json"
        bad.write_text("{not valid json", encoding="utf-8")
        data = load_config_file(bad)
        assert data == {}

    def test_save_config_file(self, tmp_path: Path) -> None:
        cfg_file = tmp_path / "unity_bridge_config.json"
        ok = save_config_file(
            {"log_level": "INFO", "default_timeout": 45},
            cfg_file,
        )
        assert ok is True
        saved = json.loads(cfg_file.read_text(encoding="utf-8"))
        assert saved["log_level"] == "INFO"
        assert saved["default_timeout"] == 45

    def test_save_creates_parent_dirs(self, tmp_path: Path) -> None:
        nested = tmp_path / "a" / "b" / "config.json"
        ok = save_config_file({"key": "val"}, nested)
        assert ok is True
        assert nested.exists()

    def test_config_file_from_env(self, tmp_path: Path) -> None:
        """UNITY_BRIDGE_CONFIG env var specifies config file path."""
        cfg_file = tmp_path / "custom_config.json"
        cfg_file.write_text(
            json.dumps({"default_timeout": 99}),
            encoding="utf-8",
        )
        with patch.dict(os.environ, {"UNITY_BRIDGE_CONFIG": str(cfg_file)}, clear=False):
            config = BridgeConfig.resolve()
        assert config.default_timeout == 99
