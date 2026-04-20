"""Unity Gaming Services configuration lookups.

Exposes Unity Cloud project/organization/user IDs and the linked
environment ID so CI agents can bootstrap UGS workflows without
hard-coding values.
"""

from __future__ import annotations

import asyncio

import typer

from unity_bridge.core.bridge import CommandResult, DirectBridge


async def get_project_id(
    bridge: DirectBridge,
    timeout: float = 10.0,
) -> CommandResult:
    """Return the Unity Cloud project ID, name, and organization."""
    return await bridge.send_command_with_retry(
        command_type="cloud-services",
        parameters={"operation": "get-project-id"},
        timeout=timeout,
    )


async def get_environments(
    bridge: DirectBridge,
    timeout: float = 10.0,
) -> CommandResult:
    """Return all known environments (requires com.unity.services.core)."""
    return await bridge.send_command_with_retry(
        command_type="cloud-services",
        parameters={"operation": "get-environments"},
        timeout=timeout,
    )


async def get_active_environment(
    bridge: DirectBridge,
    timeout: float = 10.0,
) -> CommandResult:
    """Return the currently-linked environment ID and name."""
    return await bridge.send_command_with_retry(
        command_type="cloud-services",
        parameters={"operation": "get-active-environment"},
        timeout=timeout,
    )


cloud_app = typer.Typer(
    name="cloud",
    help="Unity Gaming Services configuration.",
)


@cloud_app.command("project-id")
def project_id_cli(ctx: typer.Context) -> None:
    """Get the linked Unity Cloud project/organization/user IDs."""
    from unity_bridge.core.output import print_result

    state = ctx.obj
    result = asyncio.run(get_project_id(state.bridge))
    print_result(result, state.formatter)


@cloud_app.command("environments")
def environments_cli(ctx: typer.Context) -> None:
    """List environments (requires com.unity.services.core)."""
    from unity_bridge.core.output import print_result

    state = ctx.obj
    result = asyncio.run(get_environments(state.bridge))
    print_result(result, state.formatter)


@cloud_app.command("active-environment")
def active_environment_cli(ctx: typer.Context) -> None:
    """Get the currently-linked environment ID/name."""
    from unity_bridge.core.output import print_result

    state = ctx.obj
    result = asyncio.run(get_active_environment(state.bridge))
    print_result(result, state.formatter)
