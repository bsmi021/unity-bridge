"""CLI for the deterministic command-surface parity gate."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Running this file directly puts ``tools`` rather than the repository root on
# sys.path. Add the root so the same package import works in tests and scripts.
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.command_surface_parity_lib import (  # noqa: E402
    build_surface,
    evaluate_registry,
    render_json,
    seed_registry,
)


def _parse_args(arguments: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("seed", "check"))
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--registry", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    return parser.parse_args(arguments)


def main(arguments: list[str] | None = None) -> int:
    """Run the seed or check command."""
    options = _parse_args(arguments)
    surface = build_surface(options.root)
    if options.action == "seed":
        options.registry.parent.mkdir(parents=True, exist_ok=True)
        options.registry.write_text(render_json(seed_registry(surface)), encoding="utf-8")
        return 0
    registry = json.loads(options.registry.read_text(encoding="utf-8"))
    report = evaluate_registry(surface, registry)
    if options.output:
        options.output.parent.mkdir(parents=True, exist_ok=True)
        options.output.write_text(render_json(report), encoding="utf-8")
    print(render_json(report), end="")
    return 0 if report["is_complete"] else 3


if __name__ == "__main__":
    sys.exit(main())
