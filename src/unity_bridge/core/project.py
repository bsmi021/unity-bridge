"""
Unity project detection and path resolution.

Provides functions to locate a Unity project root by walking up the
directory tree looking for Assets/ and ProjectSettings/ directories.
"""

import logging
import sys
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger("unity_bridge.project")

MAX_SEARCH_DEPTH = 10


@dataclass
class BridgePaths:
    """Standard paths within a Unity project used by the bridge.

    Attributes:
        project_root: Unity project root (contains Assets/).
        commands_dir: Directory for outgoing command JSON files.
        responses_dir: Directory for incoming response JSON files.
        heartbeat_file: Heartbeat JSON written by Unity Editor.
        editor_bridge_dir: Location of the C# bridge scripts.
    """

    project_root: Path
    commands_dir: Path
    responses_dir: Path
    heartbeat_file: Path
    editor_bridge_dir: Path


def detect_unity_project(start_path: Path | None = None) -> Path:
    """Walk up from start_path looking for a Unity project root.

    A Unity project root contains both an ``Assets/`` and a
    ``ProjectSettings/`` directory.

    Args:
        start_path: Directory to start searching from (defaults to cwd).

    Returns:
        Absolute path to the Unity project root.

    Raises:
        SystemExit: If no project is found within MAX_SEARCH_DEPTH levels.
    """
    current = (start_path or Path.cwd()).resolve()

    for _ in range(MAX_SEARCH_DEPTH):
        if _is_unity_project(current):
            logger.debug("Detected Unity project at %s", current)
            return current
        parent = current.parent
        if parent == current:
            break  # filesystem root
        current = parent

    logger.error("No Unity project found (searched %d levels from %s)", MAX_SEARCH_DEPTH, start_path)
    print(
        "ERROR: Could not detect a Unity project. "
        "Use --project to specify the path, or run from inside a Unity project directory.",
        file=sys.stderr,
    )
    raise SystemExit(2)


def find_unity_project_root(start_path: Path) -> Path | None:
    """Walk up looking for a Unity project root.

    Unlike detect_unity_project, this returns None instead of exiting
    if no project is found.
    """
    current = start_path.resolve()
    for _ in range(MAX_SEARCH_DEPTH):
        if _is_unity_project(current):
            return current
        parent = current.parent
        if parent == current:
            break
        current = parent
    return None


def validate_project(project_root: Path) -> list[str]:
    """Validate that a path looks like a valid Unity project.

    Returns:
        List of validation error messages (empty if valid).
    """
    errors: list[str] = []
    root = Path(project_root)

    if not root.exists():
        errors.append(f"Path does not exist: {root}")
        return errors

    if not (root / "Assets").is_dir():
        errors.append(f"Missing Assets/ directory in {root}")

    if not (root / "ProjectSettings").is_dir():
        errors.append(f"Missing ProjectSettings/ directory in {root}")

    return errors


def get_bridge_paths(project_root: Path) -> BridgePaths:
    """Construct standard bridge paths from a project root.

    Args:
        project_root: Unity project root directory.

    Returns:
        BridgePaths with all standard directories and files.
    """
    root = Path(project_root)
    claude_dir = root / ".claude" / "unity"
    return BridgePaths(
        project_root=root,
        commands_dir=claude_dir / "commands",
        responses_dir=claude_dir / "responses",
        heartbeat_file=claude_dir / "heartbeat.json",
        editor_bridge_dir=root / "Assets" / "Scripts" / "Editor" / "ClaudeCodeBridge",
    )


def ensure_bridge_directories(project_root: Path) -> BridgePaths:
    """Create bridge directories if they do not exist.

    Returns:
        BridgePaths with all directories guaranteed to exist.
    """
    paths = get_bridge_paths(project_root)
    paths.commands_dir.mkdir(parents=True, exist_ok=True)
    paths.responses_dir.mkdir(parents=True, exist_ok=True)
    return paths


# ---------------------------------------------------------------------------
# Internal
# ---------------------------------------------------------------------------

def _is_unity_project(path: Path) -> bool:
    """Return True if path contains Assets/ and ProjectSettings/."""
    return (path / "Assets").is_dir() and (path / "ProjectSettings").is_dir()
