"""Shared pytest fixtures for live Unity Editor integration proof."""

from __future__ import annotations

import os

import pytest

from tests.integration.live_unity import (
    LiveFixtureUnavailable,
    LiveUnityTarget,
    require_explicit_guard,
    select_live_unity_environment,
    select_live_unity_role,
    select_live_unity_target,
)


@pytest.fixture(scope="session")
def live_unity_65() -> LiveUnityTarget:
    """Return the environment-selected healthy Unity 6000.5 target or skip."""
    try:
        return select_live_unity_target(os.environ)
    except LiveFixtureUnavailable as exc:
        pytest.skip(str(exc))


def _select_role_or_skip(role_name: str) -> LiveUnityTarget:
    try:
        return select_live_unity_role(role_name, os.environ)
    except LiveFixtureUnavailable as exc:
        pytest.skip(str(exc))


@pytest.fixture(scope="session")
def core_clean_unity_65() -> LiveUnityTarget:
    """Return the required clean-core fixture role or skip exactly."""
    return _select_role_or_skip("core-clean")


@pytest.fixture(scope="session")
def package_rich_unity_65() -> LiveUnityTarget:
    """Return the required package-rich fixture role or skip exactly."""
    return _select_role_or_skip("package-rich")


@pytest.fixture(scope="session")
def playback_build_target_unity_65() -> LiveUnityTarget:
    """Return the required playback/build-target fixture role or skip exactly."""
    return _select_role_or_skip("playback-build-target")


def _select_guarded_target_or_skip(
    project_environment: str,
    guard_environment: str,
    purpose: str,
) -> LiveUnityTarget:
    try:
        require_explicit_guard(os.environ, guard_environment, purpose)
        return select_live_unity_environment(project_environment, os.environ)
    except LiveFixtureUnavailable as exc:
        pytest.skip(str(exc))


@pytest.fixture(scope="session")
def addressables_success_unity_65() -> LiveUnityTarget:
    """Return the isolated, explicitly authorized Addressables success fixture."""
    return _select_guarded_target_or_skip(
        "UNITY_BRIDGE_ADDRESSABLES_SUCCESS_PROJECT",
        "UNITY_BRIDGE_RUN_ADDRESSABLES_SUCCESS_BUILD",
        "Addressables success build",
    )


@pytest.fixture(scope="session")
def addressables_failure_unity_65() -> LiveUnityTarget:
    """Return the isolated, explicitly authorized Addressables failure fixture."""
    return _select_guarded_target_or_skip(
        "UNITY_BRIDGE_ADDRESSABLES_FAILURE_PROJECT",
        "UNITY_BRIDGE_RUN_ADDRESSABLES_FAILURE_BUILD",
        "Addressables failure build",
    )


@pytest.fixture(scope="session")
def reload_probe_unity_65() -> LiveUnityTarget:
    """Return an isolated fixture authorized for a script-compilation reload."""
    return _select_guarded_target_or_skip(
        "UNITY_BRIDGE_RELOAD_PROBE_PROJECT",
        "UNITY_BRIDGE_RUN_RELOAD_PROBE",
        "cooperative job domain-reload probe",
    )
