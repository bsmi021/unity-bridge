# Unity Bridge Agent Instructions

Last updated: 2026-07-05

Unity Bridge is a CLI-first Unity Editor automation project. The Python package
ships a Typer CLI plus a managed C# Editor bridge that communicates through
files under each Unity project's `.claude/unity/` directory.

## Current Interface Contract

- `unity-bridge` CLI is the supported interface.
- The old internal MCP server is retired. Do not add a `src/unity_bridge/mcp/`
  package, `unity-bridge serve`, MCP schemas/tools, or a `[mcp]` packaging extra.
- If stale source comments or docs mention CLI/MCP sharing, verify against the
  live CLI and README before carrying that wording forward.
- Treat `uv run unity-bridge --help` and targeted command help as authoritative
  for the live command surface.

## Common Commands

Run these from the repository root in PowerShell:

```powershell
# Inspect the live CLI surface
uv run unity-bridge --help
uv run unity-bridge version

# Validate code
uv run ruff check src/ tests/
uv run ruff format src/ tests/
uv run pytest tests/unit/
uv run pytest tests/
uv run pytest tests --cov=unity_bridge --cov-report=term-missing --cov-fail-under=90

# Unity-facing checks when a Unity project/editor is available
uv run unity-bridge --project "C:/Path/To/UnityProject" status
uv run unity-bridge --project "C:/Path/To/UnityProject" doctor
uv run unity-bridge --project "C:/Path/To/UnityProject" test compile --wait --timeout 600
```

Use `pip install -e ".[dev]"` only as an environment bootstrap step when the
editable install is missing. Prefer `uv run ...` for commands executed by Codex.

## Configuration And Output

- Global CLI flags include `--project/-p`, `--pretty`, `--human/-H`,
  `--verbose/-v`, `--quiet/-q`, `--timeout/-t`, and `--no-color`.
- Configuration precedence is CLI flags, then environment variables, then config
  file, then defaults.
- Config file search order is `$UNITY_BRIDGE_CONFIG`,
  `<project_root>/unity_bridge_config.json`, then
  `<project_root>/.claude/unity_bridge_config.json`.
- CLI output is JSON to stdout by default. Use `--human` for formatted text and
  `--pretty` for indented JSON.
- CLI output keys are `snake_case`; bridge protocol payloads use `camelCase`.
- Command types sent to Unity use kebab-case.

## Architecture Invariants

- Keep CLI wrappers thin. Command modules expose async core functions that
  return `CommandResult`, and Typer wrappers call them through `asyncio.run()`.
- Use `DirectBridge` for file-based Unity communication, `BridgeConfig` for
  config resolution, and `AppState` for lazy CLI state.
- Use `asyncio.get_running_loop()` inside async code, never
  `asyncio.get_event_loop()`.
- Use `datetime.now(timezone.utc)`, never `datetime.utcnow()`.
- Use Python 3.10+ syntax, including `X | Y` unions instead of `Optional[X]`
  or `Union[X, Y]`.
- Use dataclasses for structured Python data where practical.
- Keep source files under 500 LOC and functions/methods under 50 LOC excluding
  comments and whitespace.
- Keep command timeout defaults in `src/unity_bridge/core/protocol.py`.
  `PARALLEL_SAFE_COMMANDS` in that file is the source of truth for read-only
  batch parallelism.

## C# Bridge Rules

- Source C# bridge files live in `ClaudeCodeBridge/`.
- `unity-bridge install` copies managed bridge files into a Unity project at
  `Assets/Scripts/Editor/ClaudeCodeBridge/`.
- Preserve Unity `.meta` files when adding, renaming, or deleting C# bridge
  assets.
- Large handlers should be split into focused `*CommandHandler.cs`, `*Models.cs`,
  and `*Helpers.cs` files.
- The Editor bridge runs from `ClaudeUnityBridge.cs` via
  `EditorApplication.update` and writes responses back to the file protocol.
- Do not bypass the install/update path when validating deployed bridge changes;
  source correctness and deployed Unity compile correctness are separate proof
  points.

## Testing And Validation

- Use TDD for behavior changes unless the task is docs-only, formatting-only,
  generated-only, or a pure refactor already covered by green tests.
- Unit tests mock `DirectBridge` and must not require Unity.
- Integration tests are marked `@pytest.mark.integration` and may require a
  running Unity Editor.
- For skill/docs changes, verify the live command surface first when command
  text is involved.
- Do not treat a focused test as publish-ready proof. Before push, run the full
  practical suite plus lint. If the repository-wide coverage gate is blocked by
  existing baseline debt, report the exact command and result and do not push
  without explicit approval.
- After compile errors in tests, rebuild or rerun the relevant setup before
  trusting subsequent results.

## Codex Routing

- Repo skill source is `.agents/skills/unity-bridge-cli/`.
- `unity-bridge install` ships that skill into target Unity projects.
- After editing the skill, run:

```powershell
uv run python C:/Users/bsmi0/.codex/skills/.system/skill-creator/scripts/quick_validate.py .agents/skills/unity-bridge-cli
uv run pytest tests/unit/test_skill_docs.py
```

- Project-scoped custom agents live in `.codex/agents/`.
- Use `unity_bridge_explorer` for read-only CLI/docs/handler surface mapping.
- Use `unity_bridge_reviewer` for read-only command contract, packaging, test,
  and install drift review.
- If Codex does not see a changed skill or agent file, start a fresh Codex
  session before debugging bridge behavior.

## Documentation

- Keep `README.md` as the user-facing command and architecture reference.
- Keep detailed plans, audits, and research under `docs/`; `docs/index.md` is
  the entry point.
- Update `CHANGELOG.md` for user-facing or architectural changes.
- Use Markdown for durable agent-facing docs and plans. Use HTML only for
  polished human review reports.
- Do not duplicate long command catalogs in this file. Link or point to README
  and docs instead.

## Nested Guidance Policy

- Add nested `AGENTS.md` files only when a directory has durable rules that
  differ materially from this root guidance.
- Good candidates are directories with different languages, deployment proof,
  generated/managed assets, or validation gates.
- Do not add nested guidance just to restate command lists, README content, or
  generic Python/C# style rules.
- When adding nested guidance, keep it short and limited to rules that should
  override or specialize this root file for that subtree.
- Current intentional nested files:
  - `src/unity_bridge/commands/AGENTS.md` for Python command wrapper/protocol
    mapping and registration parity.
  - `tests/AGENTS.md` for pytest fixture, Unity-integration, and stale test-doc
    rules.
  - `ClaudeCodeBridge/AGENTS.md` for managed C# bridge bundle, `.meta`, and
    Unity Editor callback rules.
  - `docs/AGENTS.md` for documentation freshness, research, and proof-boundary
    rules.
