"""Unit tests for core/settings_params.py — build_set_params."""

from __future__ import annotations

from unity_bridge.core.settings_params import SettingField, build_set_params


FIELDS = [
    SettingField("gravity", ("gravityX", "gravityY"), "setGravity"),
    SettingField("velocity_iterations", ("velocityIterations",), "setVelocityIterations"),
    SettingField("skybox_material", ("skyboxMaterial",)),  # no set-flag
    SettingField("ambient_light", ("rR", "rG", "rB"), "setAmbientLight"),
]


def test_only_provided_fields_are_included() -> None:
    params = build_set_params("set", FIELDS, {"velocity_iterations": 8})
    assert params == {
        "operation": "set",
        "setVelocityIterations": True,
        "velocityIterations": 8,
    }


def test_none_values_are_skipped() -> None:
    params = build_set_params(
        "set", FIELDS, {"gravity": None, "velocity_iterations": None}
    )
    assert params == {"operation": "set"}


def test_vector_field_maps_components_in_order() -> None:
    params = build_set_params("set", FIELDS, {"gravity": (0.0, -9.81)})
    assert params == {
        "operation": "set",
        "setGravity": True,
        "gravityX": 0.0,
        "gravityY": -9.81,
    }


def test_field_without_set_flag_emits_value_only() -> None:
    params = build_set_params("set", FIELDS, {"skybox_material": "Assets/Sky.mat"})
    assert params == {"operation": "set", "skyboxMaterial": "Assets/Sky.mat"}


def test_three_component_vector() -> None:
    params = build_set_params("set", FIELDS, {"ambient_light": (0.1, 0.2, 0.3)})
    assert params == {
        "operation": "set",
        "setAmbientLight": True,
        "rR": 0.1,
        "rG": 0.2,
        "rB": 0.3,
    }


def test_false_boolean_is_included_not_skipped() -> None:
    fields = [SettingField("fog", ("fog",), "setFog")]
    params = build_set_params("set", fields, {"fog": False})
    assert params == {"operation": "set", "setFog": True, "fog": False}


def test_unrelated_values_are_ignored() -> None:
    params = build_set_params(
        "set", FIELDS, {"velocity_iterations": 4, "bridge": object(), "timeout": 10.0}
    )
    assert params == {
        "operation": "set",
        "setVelocityIterations": True,
        "velocityIterations": 4,
    }
