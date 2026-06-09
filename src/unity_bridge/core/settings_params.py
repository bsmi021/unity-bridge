"""Shared builder for "set selected fields" bridge command parameters.

Many settings command modules (physics, audio, lightmap, environment, ...)
share the same shape: only the fields the caller actually provided are sent,
each optionally accompanied by a ``setX`` boolean flag, and vector fields map a
single tuple argument onto several component keys. This module centralizes that
mapping so the per-module ``*_set`` functions stay declarative.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class SettingField:
    """Maps one Python keyword argument to its bridge parameter key(s).

    Attributes:
        name: The Python kwarg name (e.g. ``"velocity_iterations"``).
        value_keys: Bridge param key(s) for the value. One key for scalars; for
            vector/color fields, one key per tuple component
            (e.g. ``("gravityX", "gravityY")``).
        set_flag: Optional bridge boolean flag set to True when the field is
            provided (e.g. ``"setGravity"``). None for fields with no set-flag.
    """

    name: str
    value_keys: tuple[str, ...]
    set_flag: str | None = None


def build_set_params(
    operation: str,
    fields: list[SettingField],
    values: dict[str, Any],
) -> dict[str, Any]:
    """Build a ``set`` command parameter dict from provided field values.

    Only fields whose value in ``values`` is not None are included. A field
    with multiple value_keys consumes one tuple value, mapping each component to
    its key in order.

    Args:
        operation: The bridge ``operation`` value (e.g. ``"set"``).
        fields: Field specs describing the kwarg -> bridge-key mapping.
        values: A mapping of kwarg name -> value (typically ``locals()``);
            unrelated keys are ignored.
    """
    params: dict[str, Any] = {"operation": operation}
    for field in fields:
        value = values.get(field.name)
        if value is None:
            continue
        if field.set_flag is not None:
            params[field.set_flag] = True
        if len(field.value_keys) == 1:
            params[field.value_keys[0]] = value
        else:
            for key, component in zip(field.value_keys, value):
                params[key] = component
    return params
