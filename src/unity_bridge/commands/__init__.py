"""Command modules for the unity-bridge CLI.

Each module exposes async core functions and thin synchronous Typer
wrappers that call ``asyncio.run()`` on them.
"""

from unity_bridge.commands.animator import animator_app
from unity_bridge.commands.asset import asset_app
from unity_bridge.commands.batch import batch_app
from unity_bridge.commands.build import build_app
from unity_bridge.commands.console import console_app
from unity_bridge.commands.diagnostics import diagnostics_app
from unity_bridge.commands.editor import editor_app
from unity_bridge.commands.hierarchy import component_app, hierarchy_app
from unity_bridge.commands.lifecycle import lifecycle_app
from unity_bridge.commands.material import material_app
from unity_bridge.commands.playmode import playmode_app
from unity_bridge.commands.prefab import prefab_app
from unity_bridge.commands.scene import scene_app
from unity_bridge.commands.scripting import script_app
from unity_bridge.commands.testing import test_app
from unity_bridge.commands.workflow import snapshot_app, workflow_app

__all__ = [
    "animator_app",
    "asset_app",
    "batch_app",
    "build_app",
    "console_app",
    "component_app",
    "diagnostics_app",
    "editor_app",
    "hierarchy_app",
    "lifecycle_app",
    "material_app",
    "playmode_app",
    "prefab_app",
    "scene_app",
    "script_app",
    "snapshot_app",
    "test_app",
    "workflow_app",
]
