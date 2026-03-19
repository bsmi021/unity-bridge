"""Core modules for Unity Bridge: bridge communication, health, cache, retry, config."""

from unity_bridge.core.bridge import CommandResult, DirectBridge
from unity_bridge.core.health import HealthMonitor, HealthStatus
from unity_bridge.core.cache import ResponseCache, get_cache
from unity_bridge.core.retry import RetryConfig, retry_async
from unity_bridge.core.config import BridgeConfig, load_config_file, save_config_file
from unity_bridge.core.project import BridgePaths, detect_unity_project, get_bridge_paths
from unity_bridge.core.protocol import (
    TIMEOUT_DEFAULTS,
    PARALLEL_SAFE_COMMANDS,
    get_timeout,
)
from unity_bridge.core.output import OutputFormatter, print_result

__all__ = [
    "CommandResult",
    "DirectBridge",
    "HealthMonitor",
    "HealthStatus",
    "ResponseCache",
    "get_cache",
    "RetryConfig",
    "retry_async",
    "BridgeConfig",
    "load_config_file",
    "save_config_file",
    "BridgePaths",
    "detect_unity_project",
    "get_bridge_paths",
    "TIMEOUT_DEFAULTS",
    "PARALLEL_SAFE_COMMANDS",
    "get_timeout",
    "OutputFormatter",
    "print_result",
]
