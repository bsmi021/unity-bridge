# Subagent Brief: Live Unity Bridge Inventory

Last updated: 2026-07-09

## Objective

Produce a read-only, source-backed inventory of the current `unity-bridge` CLI,
Python dispatch layer, C# command registry, handlers, and tests. Determine what
Codex can actually do through the supported CLI today.

## Scope

- Run `uv run unity-bridge --help` and targeted group help as needed.
- Inspect `src/unity_bridge/app.py`, `src/unity_bridge/commands/`,
  `ClaudeCodeBridge/BridgeCommandRegistry.cs`, relevant handlers, and inventory
  or contract tests.
- Identify generic escape hatches such as `script`, `menu`, serialized
  `property`, asset operations, and reflection-backed commands.
- Record direct, indirect, read-only, write, long-running, and package-gated
  capabilities.
- Find registration, documentation, or test drift.

## Non-Goals

- Do not edit files.
- Do not design new commands.
- Do not claim Unity runtime proof without a live Editor command result.
- Do not use the retired internal MCP surface as current functionality.

## Sources

- Root and nested `AGENTS.md` files.
- `.agents/skills/unity-bridge-cli/`.
- `README.md` and `docs/index.md`.
- `src/unity_bridge/`, `ClaudeCodeBridge/`, and `tests/`.
- Live CLI help output.

## Required Output

Return a structured report with:

1. Exact counts for CLI groups, leaf commands, registered C# command types,
   handlers, and relevant tests where reproducibly countable.
2. A capability taxonomy with concrete file and line citations.
3. Generic-coverage mechanisms and their hard limits.
4. Confirmed drift or missing proof, prioritized by impact.
5. Commands run and their outcomes.

## Validation

Cross-check at least two independent representations of the command surface,
for example live help versus Python registration and C# registry versus tests.

## Blockers

Report missing tools, parse ambiguity, or oversized/generated surfaces
explicitly. Keep estimates labeled as estimates.
