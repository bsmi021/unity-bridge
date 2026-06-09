"""
BridgeConfig — unified configuration with precedence resolution.

Precedence: CLI flags > environment variables > config file > defaults.

Config file locations (searched in order):
1. $UNITY_BRIDGE_CONFIG
2. <project_root>/unity_bridge_config.json
3. <project_root>/.claude/unity_bridge_config.json
"""

import json
import logging
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

logger = logging.getLogger("unity_bridge.config")

VALID_LOG_LEVELS: set[str] = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL", "OFF"}
VALID_OUTPUT_FORMATS: set[str] = {"json", "pretty", "human"}


@dataclass
class BridgeConfig:
    """Unified CLI/library configuration.

    Attributes:
        project_root: Unity project root path (auto-detected if None).
        log_level: Logging level string.
        output_format: Output format — "json", "pretty", or "human".
        default_timeout: Default command timeout in seconds.
        timeout_explicit: Whether default_timeout was explicitly set (via CLI
            flag, env var, or config file) rather than left at its built-in
            default. Lets a global override be distinguished from the default.
        color: Whether to use colored output.
        config_file: Path to config file (auto-detected if None).
    """

    project_root: Path | None = None
    log_level: str = "ERROR"
    output_format: str = "json"
    default_timeout: int = 30
    timeout_explicit: bool = False
    color: bool = True
    config_file: Path | None = None

    @classmethod
    def from_env(cls) -> "BridgeConfig":
        """Create config from environment variables only."""
        config = cls()

        env_project = os.environ.get("UNITY_BRIDGE_PROJECT")
        if env_project:
            config.project_root = Path(env_project)

        env_log = os.environ.get("UNITY_BRIDGE_LOG_LEVEL", "").upper()
        if env_log in VALID_LOG_LEVELS:
            config.log_level = env_log

        env_timeout = _parse_timeout(os.environ.get("UNITY_BRIDGE_TIMEOUT"))
        if env_timeout is not None:
            config.default_timeout = env_timeout
            config.timeout_explicit = True

        env_config = os.environ.get("UNITY_BRIDGE_CONFIG")
        if env_config:
            config.config_file = Path(env_config)

        if os.environ.get("NO_COLOR"):
            config.color = False

        return config

    @classmethod
    def from_file(cls, path: Path) -> "BridgeConfig":
        """Create config from a JSON config file."""
        data = load_config_file(path)
        config = cls(config_file=path)

        if "log_level" in data and data["log_level"].upper() in VALID_LOG_LEVELS:
            config.log_level = data["log_level"].upper()

        if "output_format" in data and data["output_format"] in VALID_OUTPUT_FORMATS:
            config.output_format = data["output_format"]

        if (
            "default_timeout" in data
            and isinstance(data["default_timeout"], int)
            and not isinstance(data["default_timeout"], bool)
            and data["default_timeout"] > 0
        ):
            config.default_timeout = data["default_timeout"]
            config.timeout_explicit = True

        if "color" in data and isinstance(data["color"], bool):
            config.color = data["color"]

        return config

    @classmethod
    def resolve(
        cls,
        cli_project: Path | None = None,
        cli_format: str | None = None,
        cli_verbose: bool = False,
        cli_quiet: bool = False,
        cli_timeout: int | None = None,
        cli_no_color: bool = False,
    ) -> "BridgeConfig":
        """Build config with full precedence resolution.

        CLI flags > env vars > config file > defaults.
        """
        # Start with defaults
        config = cls()

        # Layer: config file
        config_file = _find_config_file(cli_project)
        if config_file:
            file_config = cls.from_file(config_file)
            config = _merge_config(config, file_config)

        # Layer: environment variables
        env_config = cls.from_env()
        config = _merge_config(config, env_config)

        # Layer: CLI flags (highest priority)
        if cli_project is not None:
            config.project_root = cli_project
        if cli_format is not None:
            config.output_format = cli_format
        if cli_verbose:
            config.log_level = "DEBUG"
        if cli_quiet:
            config.log_level = "CRITICAL"
        if cli_timeout is not None:
            config.default_timeout = cli_timeout
            config.timeout_explicit = True
        if cli_no_color:
            config.color = False

        return config


def load_config_file(path: Path | None = None) -> dict[str, Any]:
    """Load a JSON config file. Returns empty dict on error or missing file."""
    if path is None:
        return {}
    path = Path(path)
    if not path.exists():
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError) as exc:
        logger.warning("Failed to load config from %s: %s", path, exc)
        return {}


def save_config_file(config: dict[str, Any], path: Path | None = None) -> bool:
    """Save config dict to JSON file. Returns True on success."""
    if path is None:
        return False
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2)
        logger.info("Config saved to %s", path)
        return True
    except IOError as exc:
        logger.error("Failed to save config to %s: %s", path, exc)
        return False


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _parse_timeout(raw: str | None) -> int | None:
    """Parse a timeout string into a positive int, tolerating whitespace.

    Returns None for missing, malformed, or non-positive values.
    """
    if raw is None:
        return None
    try:
        value = int(raw.strip())
    except (ValueError, AttributeError):
        return None
    return value if value > 0 else None


def _find_config_file(project_root: Path | None = None) -> Path | None:
    """Search for a config file in standard locations."""
    env_path = os.environ.get("UNITY_BRIDGE_CONFIG")
    if env_path:
        p = Path(env_path)
        if p.exists():
            return p

    if project_root is not None:
        for candidate in [
            project_root / "unity_bridge_config.json",
            project_root / ".claude" / "unity_bridge_config.json",
        ]:
            if candidate.exists():
                return candidate

    return None


def _merge_config(base: BridgeConfig, overlay: BridgeConfig) -> BridgeConfig:
    """Merge overlay into base, preferring non-default overlay values."""
    defaults = BridgeConfig()
    result = BridgeConfig(
        project_root=overlay.project_root or base.project_root,
        log_level=overlay.log_level if overlay.log_level != defaults.log_level else base.log_level,
        output_format=(
            overlay.output_format
            if overlay.output_format != defaults.output_format
            else base.output_format
        ),
        default_timeout=(
            overlay.default_timeout if overlay.timeout_explicit else base.default_timeout
        ),
        timeout_explicit=overlay.timeout_explicit or base.timeout_explicit,
        color=overlay.color if overlay.color != defaults.color else base.color,
        config_file=overlay.config_file or base.config_file,
    )
    return result
