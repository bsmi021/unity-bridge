"""Main Typer application for the ``unity-bridge`` CLI.

Creates the top-level Typer app, defines global flags, registers all
command groups, and wires up the ``AppState`` context object so that
every sub-command can access the shared bridge and formatter.
"""

from __future__ import annotations

import signal
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Annotated

import typer

from unity_bridge.core.config import BridgeConfig
from unity_bridge.core.output import OutputFormatter

# ---------------------------------------------------------------------------
# Application state
# ---------------------------------------------------------------------------


@dataclass
class AppState:
    """Shared state passed to every sub-command via ``ctx.obj``."""

    config: BridgeConfig
    formatter: OutputFormatter
    _bridge: object | None = field(default=None, repr=False)

    @property
    def project_root(self) -> Path:
        """Resolve the Unity project root (auto-detect if not configured)."""
        if self.config.project_root is not None:
            return self.config.project_root
        from unity_bridge.core.project import detect_unity_project

        resolved = detect_unity_project()
        self.config.project_root = resolved
        return resolved

    @property
    def bridge(self) -> object:
        """Lazy-init DirectBridge on first access.

        Returns:
            A ``DirectBridge`` instance connected to the resolved project.
        """
        if self._bridge is None:
            from unity_bridge.core.bridge import DirectBridge

            self._bridge = DirectBridge(self.project_root)
        return self._bridge


# ---------------------------------------------------------------------------
# Typer app
# ---------------------------------------------------------------------------

app = typer.Typer(
    name="unity-bridge",
    help="CLI for Unity Editor automation via file-based bridge.",
    no_args_is_help=True,
    rich_markup_mode="markdown",
)


def _handle_sigint(signum: int, frame: object) -> None:
    """Exit cleanly on Ctrl+C with conventional exit code 130."""
    sys.exit(130)


@app.callback()
def main(
    ctx: typer.Context,
    project: Annotated[
        Path | None,
        typer.Option(
            "--project",
            "-p",
            help="Path to Unity project root. Auto-detected if omitted.",
        ),
    ] = None,
    pretty: Annotated[
        bool,
        typer.Option("--pretty", help="Indent JSON output for readability."),
    ] = False,
    human: Annotated[
        bool,
        typer.Option("--human", "-H", help="Human-readable output instead of JSON."),
    ] = False,
    verbose: Annotated[
        bool,
        typer.Option("--verbose", "-v", help="Enable verbose (DEBUG) logging."),
    ] = False,
    quiet: Annotated[
        bool,
        typer.Option("--quiet", "-q", help="Suppress all non-error output."),
    ] = False,
    timeout: Annotated[
        int | None,
        typer.Option("--timeout", "-t", help="Default command timeout in seconds."),
    ] = None,
    no_color: Annotated[
        bool,
        typer.Option("--no-color", help="Disable coloured output."),
    ] = False,
) -> None:
    """Configure global state from CLI flags."""
    signal.signal(signal.SIGINT, _handle_sigint)

    output_format = _resolve_format(pretty=pretty, human=human)

    config = BridgeConfig.resolve(
        cli_project=project,
        cli_format=output_format,
        cli_verbose=verbose,
        cli_quiet=quiet,
        cli_timeout=timeout,
        cli_no_color=no_color,
    )

    formatter = OutputFormatter(
        format=config.output_format,
        color=config.color,
    )

    ctx.ensure_object(dict)
    ctx.obj = AppState(config=config, formatter=formatter)


def _resolve_format(*, pretty: bool, human: bool) -> str | None:
    """Determine the output format string from boolean flags.

    Returns:
        ``"human"`` if *human* is set, ``"pretty"`` if *pretty* is set,
        or ``None`` to use the config/env default (plain JSON).
    """
    if human:
        return "human"
    if pretty:
        return "pretty"
    return None


# ---------------------------------------------------------------------------
# Command registration
# ---------------------------------------------------------------------------


def _register_commands() -> None:
    """Import and register all command sub-apps and top-level commands.

    Wrapped in a function so imports happen at registration time, not at
    module-import time.  This keeps ``app`` importable even when optional
    command dependencies are missing.
    """
    from unity_bridge.commands.testing import test_app
    from unity_bridge.commands.hierarchy import component_app, hierarchy_app
    from unity_bridge.commands.scene import scene_app
    from unity_bridge.commands.prefab import prefab_app
    from unity_bridge.commands.console import console_app

    # Sub-command groups
    app.add_typer(test_app, name="test")
    app.add_typer(component_app, name="component")
    app.add_typer(hierarchy_app, name="hierarchy")
    app.add_typer(scene_app, name="scene")
    app.add_typer(prefab_app, name="prefab")
    app.add_typer(console_app, name="console")

    # Top-level commands from existing modules
    _register_optional_commands()


def _register_optional_commands() -> None:
    """Register command modules that may not exist yet.

    Each block is wrapped in a try/except so the CLI remains functional
    even when some command modules have not been implemented.
    """
    _try_register_group("unity_bridge.commands.snapshot", "snapshot_app", "snapshot")
    _try_register_command("unity_bridge.commands.playmode", "playmode_cli", "playmode")
    _try_register_command("unity_bridge.commands.diagnostics", "status_cli", "status")
    _try_register_command("unity_bridge.commands.diagnostics", "doctor_cli", "doctor")
    _try_register_command("unity_bridge.commands.diagnostics", "profiler_cli", "profiler")
    _try_register_command("unity_bridge.commands.lifecycle", "install_cli", "install")
    _try_register_command("unity_bridge.commands.lifecycle", "init_cli", "init")
    _try_register_command("unity_bridge.commands.lifecycle", "clean_cli", "clean")
    _try_register_command("unity_bridge.commands.lifecycle", "version_cli", "version")
    _try_register_command("unity_bridge.commands.workflow", "tdd_cli", "tdd")
    _try_register_command("unity_bridge.commands.scripting", "script_cli", "script")
    _try_register_command("unity_bridge.commands.batch", "batch_cli", "batch")
    _try_register_command("unity_bridge.commands.serve", "serve_cli", "serve")
    _try_register_command("unity_bridge.commands.editor", "selection_cli", "selection")
    _try_register_command("unity_bridge.commands.editor", "refresh_cli", "refresh")
    _try_register_command("unity_bridge.commands.editor", "focus_cli", "focus")
    _try_register_command("unity_bridge.commands.editor", "menu_cli", "menu")
    _try_register_command("unity_bridge.commands.editor", "screenshot_cli", "screenshot")
    _try_register_command("unity_bridge.commands.asset", "asset_cli", "asset")
    _try_register_command("unity_bridge.commands.material", "material_cli", "material")
    _try_register_command("unity_bridge.commands.build", "build_cli", "build")
    _try_register_command("unity_bridge.commands.animator", "animator_cli", "animator")
    _try_register_group("unity_bridge.commands.settings", "settings_app", "settings")
    _try_register_group("unity_bridge.commands.build_profile", "build_profile_app", "profile")
    _try_register_group("unity_bridge.commands.asset_extended", "asset_ext_app", "asset-ext")
    _try_register_group("unity_bridge.commands.package", "package_app", "package")
    _try_register_group("unity_bridge.commands.compile_extended", "compile_ext_app", "compile")
    _try_register_group("unity_bridge.commands.undo", "undo_app", "undo")
    _try_register_group("unity_bridge.commands.lightmap", "lightmap_app", "lightmap")
    _try_register_group("unity_bridge.commands.shader", "shader_app", "shader")
    _try_register_group("unity_bridge.commands.scene_setup", "scene_setup_app", "scene-ext")
    _try_register_group(
        "unity_bridge.commands.import_settings", "import_settings_app", "import-settings"
    )

    # Phase 4: Critical Gaps
    _try_register_group("unity_bridge.commands.select", "select_app", "select")
    _try_register_group("unity_bridge.commands.prefs", "prefs_app", "prefs")
    _try_register_group("unity_bridge.commands.build_scenes", "build_scenes_app", "build-scenes")
    _try_register_group("unity_bridge.commands.transform", "transform_app", "transform")
    _try_register_group("unity_bridge.commands.property", "property_app", "property")
    _try_register_group("unity_bridge.commands.physics_config", "physics_app", "physics")
    _try_register_group("unity_bridge.commands.quality_config", "quality_app", "quality")
    _try_register_group("unity_bridge.commands.tags_layers", "tags_app", "tags")
    _try_register_group("unity_bridge.commands.tags_layers", "layers_app", "layers")
    _try_register_group("unity_bridge.commands.tags_layers", "sorting_layers_app", "sorting-layers")
    _try_register_group("unity_bridge.commands.editor_config", "editor_config_app", "editor-config")


def _try_register_command(module_path: str, attr_name: str, command_name: str) -> None:
    """Import *attr_name* from *module_path* and register as a top-level command."""
    try:
        from importlib import import_module

        mod = import_module(module_path)
        func = getattr(mod, attr_name)
        app.command(command_name)(func)
    except (ImportError, AttributeError):
        pass


def _try_register_group(module_path: str, attr_name: str, group_name: str) -> None:
    """Import a Typer sub-app and register as a command group."""
    try:
        from importlib import import_module

        mod = import_module(module_path)
        sub_app = getattr(mod, attr_name)
        app.add_typer(sub_app, name=group_name)
    except (ImportError, AttributeError):
        pass


# Perform registration on import
_register_commands()
