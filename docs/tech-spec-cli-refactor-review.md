# Tech Spec Review: Unity Bridge CLI Refactor

**Reviewer:** Adversarial Tech Spec Reviewer (Claude Code)
**Spec Version:** 1.0.0
**Review Date:** 2026-03-17
**Verdict:** CONDITIONAL APPROVAL -- address Critical and High items before implementation

---

## Summary

The spec is well-structured, has clear goals, and demonstrates strong understanding of the existing codebase. The shared-core architecture (CLI and MCP calling the same `commands/*.py` functions) is the right design. However, there are several gaps that will cause problems during implementation or at runtime.

Severity legend:
- **CRITICAL** -- Will cause build failures, data loss, or broken functionality
- **HIGH** -- Will cause confusion, bugs, or significant rework
- **MEDIUM** -- Design smell or missing detail that should be addressed
- **LOW** -- Nitpick or suggestion

---

## 1. CRITICAL Issues

### 1.1 `script` command: C# implementation is not feasible as specified

**Problem:** The spec says to use `Microsoft.CSharp.CSharpCodeProvider` or "Roslyn scripting API" (Section 9). Neither is available in Unity Editor:

- `CSharpCodeProvider` is part of `System.CodeDom` which is not included in Unity's Mono runtime in a usable form for dynamic compilation.
- Roslyn scripting (`Microsoft.CodeAnalysis.CSharp.Scripting`) is not bundled with Unity and adding it as a dependency to an Editor tool is fragile and version-sensitive.
- Unity's own compilation pipeline (`CompilationPipeline`) compiles assemblies, not expressions.

**Suggested fix:** Use `Mono.CSharp.Evaluator` which IS available in Unity's Mono runtime. It supports expression evaluation and statement execution. The handler would look like:

```csharp
using Mono.CSharp;
// Initialize evaluator with Unity's default assemblies
// Call Evaluator.Evaluate() for expressions, Evaluator.Run() for statements
```

Alternatively, defer `script` to Phase 5 / post-v1 and validate feasibility with a spike first. Document the spike as a prerequisite.

### 1.2 `--json` flag defaults to `true` but is declared as a boolean option

**Problem:** Section 2, Global Flags table says `--json` defaults to `true`. But in Section 4.7, `app.py`, it's declared as:

```python
json_output: Annotated[bool, typer.Option("--json", "-j")] = False
```

This is contradictory. If JSON is the default output format, then `--json` as a flag makes no sense -- it's already on. The spec also has `--human` and `--pretty` as alternatives.

**Suggested fix:** Remove `--json` flag entirely. JSON is the default. Users switch with `--human` or `--pretty`. The config's `output_format` field handles the default. If someone sets `output_format: "human"` in config, they could use `--json` to override back -- but that's a rare case. Simpler: just have `--human` and `--pretty` as opt-in switches.

### 1.3 `asyncio.run()` called per command will break MCP `serve`

**Problem:** In Section 5, the CLI binding pattern uses `asyncio.run(run_tests(...))`:

```python
result = asyncio.run(run_tests(state.bridge, platform, filter_pattern, timeout))
```

This is fine for CLI mode. But MCP `serve` mode already runs inside an asyncio event loop (FastMCP/mcp SDK uses `asyncio.run()` at the top level). If any MCP tool handler calls `asyncio.run()`, it will crash with `RuntimeError: cannot call asyncio.run() inside a running event loop`.

The spec says MCP tools call the same `async def run_tests(...)` function directly (Section 5, MCP Binding), which is correct. But the spec does not explicitly state that MCP tool handlers must `await` the function, not wrap it in `asyncio.run()`. This distinction needs to be crystal clear because a developer might copy the CLI pattern.

**Suggested fix:** Add an explicit note in Section 5 stating: "CLI bindings use `asyncio.run()` because Typer commands are synchronous. MCP bindings `await` the same functions directly because they execute within an existing event loop. Never use `asyncio.run()` inside MCP handlers."

---

## 2. HIGH Issues

### 2.1 `watch` and `log --follow` have unbounded memory growth

**Problem:** Section 8.7, `watch` implementation uses `seen_entries: set[str]` to deduplicate console entries. This set grows forever. In a long development session, this will consume increasing memory and the deduplication key (`timestamp:message[:50]`) could collide for repeated messages.

**Suggested fix:** Use a bounded deque or LRU set with a max size (e.g., 10,000 entries). Or use a monotonically increasing sequence number from Unity's console if available -- check whether the `read-console` response includes entry indices.

### 2.2 No specification for concurrent CLI invocations

**Problem:** What happens when two terminals both run `unity-bridge` commands simultaneously? The file-based protocol uses unique command IDs, so commands won't collide at the file level. But:

1. Will Unity process them sequentially or drop one?
2. Does `_processedCommandFiles` in `ClaudeUnityBridge.cs` handle concurrent writes safely?
3. If two `tdd` commands run simultaneously, the `clear-console` from one could interfere with the other's test results.

**Suggested fix:** Document the concurrency model explicitly. At minimum: "Commands are processed sequentially by Unity's `EditorApplication.update` loop. Multiple concurrent CLI invocations are safe at the file level but may produce interleaved results for compound commands like `tdd`. Users should avoid running multiple `tdd` or `batch` commands simultaneously."

### 2.3 `snapshot save` for large scenes is unspecified

**Problem:** Section 8.10 captures the entire hierarchy up to `depth=5`. For a scene with 10,000+ GameObjects (common in open-world or procedural games), this could produce a multi-megabyte JSON response through the file-based bridge. The C# side writes the entire response as a single JSON file. No pagination, no streaming.

Questions unanswered:
- What is the maximum response size the bridge can handle?
- What happens if Unity's JSON serialization runs out of memory?
- What's the timeout for a 10K-object hierarchy query?

**Suggested fix:** Add a `--max-objects` flag (default: 1000) that truncates the result and includes a `truncated: true` field. Document the practical limits. Consider adding `--root` to scope the snapshot to a subtree.

### 2.4 `test watch` has a hard dependency on `watchfiles` but the import is inside the function

**Problem:** Section 8.9 imports `watchfiles` lazily:

```python
from watchfiles import awatch  # optional dependency
```

If `watchfiles` is not installed, this will raise `ImportError` at runtime with no actionable message. The spec marks it as optional in Section 12 but does not specify what happens when it's missing.

**Suggested fix:** Catch the `ImportError` and raise a `typer.BadParameter` or `click.UsageError` with a message like: `"watchfiles package required for test watch. Install with: pip install unity-bridge[watch]"`

### 2.5 `--timeout` global flag conflicts with per-command `--timeout`

**Problem:** The global `--timeout` flag (Section 2) and command-specific `--timeout` flags (e.g., `run-tests --timeout 300`) create ambiguity. Which wins? The spec says the global flag provides an "override" but individual commands also accept `--timeout`.

Example: `unity-bridge --timeout 60 run-tests --timeout 300` -- what timeout is used?

**Suggested fix:** Define clear precedence: command-specific `--timeout` > global `--timeout` > per-command default from `TIMEOUT_DEFAULTS`. Document this in Section 7 (Configuration) under the precedence chain.

### 2.6 `component set` uses `--field` and `--value` but the existing MCP tool uses `fieldUpdates` array

**Problem:** Section 2, command tree shows:

```
component set <object> <type> --field NAME --value JSON
```

But the existing MCP tool `unity_set_component_data` accepts `fieldUpdates` as an array of `{fieldName, value}` pairs, allowing multiple fields in one call. The CLI spec only allows one field per invocation. This is a capability regression.

**Suggested fix:** Support `--field NAME:VALUE` repeatable (Typer supports `list` options). Or accept a JSON blob: `--updates '[{"fieldName":"hp","value":100}]'`. Or both.

### 2.7 Windows path handling not addressed

**Problem:** The spec does not mention how paths work across WSL2/Windows boundary. The existing `direct_bridge.py` works from WSL2 using `/mnt/c/` paths, but the CLI is also intended for native Windows use (bash on Windows). Questions:

- Does `--project C:\Users\dev\MyGame` work? Forward vs backslashes?
- Does `pathlib.Path` handle both on Windows natively? (Yes, but this should be tested.)
- What about `scene load Assets/Scenes/Main.unity` -- is the path relative to project root? Is it a Unity path (forward slashes)?

**Suggested fix:** Add a section or note in Section 4.4 (`core/project.py`) stating: "All paths are normalized using `pathlib.Path` which handles both `/` and `\` on Windows. Unity asset paths (scene, prefab, material) are always forward-slash relative paths from the project root (e.g., `Assets/Scenes/Main.unity`)."

---

## 3. MEDIUM Issues

### 3.1 `tdd` does not handle compilation warnings that prevent tests

**Problem:** Section 8.8, `tdd` workflow checks `compile_result.success` but Unity's compile command may return `success: true` even with warnings. Some warnings (like `CS0649: uninitialized field`) are benign, but others may affect test behavior. Also, if compilation "succeeds" but tests fail to discover because of assembly load issues, the error chain is unclear.

**Suggested fix:** Add a `--strict` flag to `tdd` that treats warnings as failures. Include warning count in the `tdd` output data.

### 3.2 `doctor` check list is incomplete

**Problem:** Section 8.2 lists 7 diagnostic checks but misses:

- **Unity Editor process check** -- is a Unity process actually running on Windows?
- **Bridge version mismatch** -- Python CLI version vs C# bridge version compatibility
- **File watcher limit** -- on some systems, the number of file watchers can be exceeded
- **Disk space** -- the commands/responses directories on a nearly-full disk will cause silent failures

**Suggested fix:** Add at minimum: Unity process detection (via `tasklist` on Windows) and version compatibility check.

### 3.3 `serve` command does not pass global flags through

**Problem:** If a user runs `unity-bridge --verbose serve`, the `--verbose` flag is parsed by the Typer callback in `app.py`, but the MCP server implementation (`mcp/server.py`) needs to receive this configuration. The spec does not describe how `BridgeConfig` flows from the CLI's `AppState` into the MCP server.

**Suggested fix:** Have `serve` read `AppState.config` from `ctx.obj` and pass it to `run_mcp_server(config)`. Define this explicitly.

### 3.4 `batch` command lacks specification

**Problem:** Section 2 shows `batch <file.json> [--stop-on-error] [--parallel]` but there is no detailed spec for it anywhere in the document. The existing MCP `unity_batch` tool has batch logic in the monolithic server file. Key questions:

- What is the JSON file format?
- How does `--parallel` work with Unity's single-threaded `EditorApplication.update`?
- What does the output look like (array of results? aggregated status?)?
- How are errors in individual commands reported?

**Suggested fix:** Add a Section 8.x for `batch` with file format, parallel semantics (note: Unity processes commands sequentially, so `--parallel` only affects the Python side sending multiple commands without waiting), and output format.

### 3.5 `prefab delete` is ambiguous

**Problem:** Section 2 command tree: `prefab delete <target>`. What is `<target>`? A prefab asset path? A scene instance? A GameObject name? The existing `prefab-operation` handler supports `unpack` and `apply` but "delete" is not one of the existing operations.

**Suggested fix:** Clarify: is this deleting the prefab asset from disk, or destroying a prefab instance in the scene? If the latter, it should be `gameobject delete`, not `prefab delete`.

### 3.6 `output.py` mixes concerns: formatting AND printing

**Problem:** Section 4.6 has `OutputFormatter` doing formatting and `print_result()` doing printing + exit code handling. But `print_result` decides the exit code based on `CommandResult.success`, while Section 13 defines 5 different exit codes. Who maps error types to exit codes?

**Suggested fix:** `print_result` should accept an explicit exit code, or `CommandResult` should carry an `exit_code` field (which it does not currently have per Section 4.1). Add `exit_code: int = 0` to `CommandResult`.

### 3.7 No signal handling for Ctrl+C during long commands

**Problem:** The spec does not describe what happens when a user presses Ctrl+C during a long-running command (e.g., `run-tests`, `compile`). The command file has already been written to disk. Unity will process it. But the Python side will exit, and no one will read the response.

**Suggested fix:** Register a signal handler that:
1. Prints a message to stderr: "Interrupted. Command may still be running in Unity."
2. Optionally writes a cancellation file (if the C# bridge supports cancellation)
3. Exits with code 130 (standard for SIGINT)

The orphaned response file will be cleaned up by `unity-bridge clean`.

### 3.8 `--project` auto-detection algorithm not specified

**Problem:** Section 4.4 lists `detect_unity_project()` and `find_unity_project_root()` but does not describe the algorithm. Does it walk up from CWD looking for `Assets/`? What if there are nested Unity projects? What if CWD is inside `Library/`?

**Suggested fix:** Specify: "Walk up from CWD looking for a directory containing `Assets/` and `ProjectSettings/`. Stop at filesystem root. If not found, raise `PROJECT_NOT_FOUND` error."

---

## 4. LOW Issues

### 4.1 Version jump from 2.0.0 to 4.0.0 is unexplained

**Problem:** The existing codebase is v2.0.0. The `pyproject.toml` in Section 14 declares version `4.0.0`. What happened to v3.0.0?

**Suggested fix:** Either start at 3.0.0 or explain the version reasoning.

### 4.2 `datetime.utcnow()` is deprecated in Python 3.12+

**Problem:** Multiple places in the spec use `datetime.utcnow()` (Sections 8.7, 8.10). This is deprecated since Python 3.12 and emits a `DeprecationWarning`.

**Suggested fix:** Use `datetime.now(timezone.utc)` instead.

### 4.3 `log` vs `watch` vs `console read` overlap

**Problem:** Three commands do similar things:
- `console read` -- one-shot console read
- `watch --types error,warning` -- tail console in real-time
- `log --follow --types error,warning` -- also tail console in real-time

What is the difference between `watch` and `log --follow`? The spec does not distinguish them.

**Suggested fix:** Merge `watch` and `log` into a single command: `unity-bridge console read` (one-shot) and `unity-bridge console watch` (follow mode). Remove the top-level `watch` and `log` commands.

### 4.4 `build build` reads awkwardly

**Problem:** Section 2 command tree: `build build|validate --target TARGET`. The command `unity-bridge build build` is redundant.

**Suggested fix:** Make `build` the default action: `unity-bridge build --target StandaloneWindows64` and `unity-bridge build --validate-only --target StandaloneWindows64`.

### 4.5 Testing section uses `datetime.utcnow()` in fixtures

**Problem:** Same as 4.2, the test fixture in Section 11 uses `datetime.utcnow().isoformat()`.

**Suggested fix:** Use `datetime.now(timezone.utc)`.

### 4.6 `pyproject.toml` specifies `requires-python = ">=3.10"` but spec says "Recommended: 3.12+"

**Problem:** The union syntax `X | Y` used throughout the spec (e.g., `dict[str, Any] | None`) requires Python 3.10+ in annotations. This is consistent. But the `match` statement claim in Section 12 is misleading -- the spec does not actually show any `match` statements.

**Suggested fix:** Remove the mention of `match` statements as a reason for the 3.10 minimum. The actual reason is `X | Y` union syntax in type hints.

### 4.7 Missing `--dry-run` on destructive commands

**Problem:** `clean` has `--dry-run` but other destructive commands do not:
- `prefab delete`
- `component set` (modifies data)
- `scene load` without `--save-current`

**Suggested fix:** Consider adding `--dry-run` to `component set` and other mutating commands, or at minimum add confirmation prompts in `--human` mode.

### 4.8 `completions` command exists in Typer already

**Problem:** Typer has built-in `--install-completion` and `--show-completion` flags. The spec creates a separate `completions install` subcommand. This duplicates Typer's built-in functionality.

**Suggested fix:** Use Typer's built-in completion support unless there's a reason to customize it. If keeping the custom command, disable Typer's built-in flags to avoid confusion.

---

## 5. Consistency Issues

### 5.1 Command naming inconsistency

| Pattern | Examples | Issue |
|---------|----------|-------|
| Top-level verb | `compile`, `refresh`, `focus` | OK |
| noun subcommand | `component get`, `scene load`, `prefab validate` | OK |
| Compound noun | `run-tests`, `test watch` | `run-tests` is top-level but `test watch` is nested under `test` |

`run-tests` should be `test run` for consistency with `test watch`. Then the command tree becomes:

```
test run [--platform PLAT] [--filter PAT]
test watch [--platform PLAT] [--filter PAT] [--path DIR]
```

### 5.2 `--platform` vs `--filter` short flags conflict

**Problem:** In `run_tests_cli`, `--platform` uses `-p` but the global `--project` also uses `-p`. Typer will raise an error at registration time.

**Suggested fix:** Use `-P` for `--platform` or drop the short flag for it.

### 5.3 Mixed key casing in output

**Problem:** The error output format (Section 13) uses `snake_case` keys (`exit_code`, `error_code`), while the existing bridge responses use `camelCase` (`commandId`, `executionTime`). The `CommandResult` dataclass (Section 4.1) uses `snake_case` (`execution_time_ms`).

**Suggested fix:** Pick one convention for CLI output. Recommendation: `snake_case` for all CLI output (it's Python convention and easier to use with `jq`). The internal bridge protocol stays `camelCase` (it's C# convention). Document this translation explicitly.

---

## 6. Architecture Observations

### 6.1 `commands/*.py` files will likely exceed 500 LOC

`assets.py` is mapped to handle asset, material, build, and animator operations (Section 3). Each of these has multiple sub-operations. With CLI bindings, core functions, and formatters, this file will easily exceed 500 LOC.

**Suggested fix:** Split `assets.py` into `asset.py`, `material.py`, `build.py`, `animator.py` as separate command modules.

### 6.2 The `formatters/` directory may be premature

For v1, formatters could be simple functions inside the command modules themselves. A dedicated `formatters/` package with 5 files is warranted only if formatters are reused across commands or need independent testing.

**Suggested fix:** Start with formatters as functions in `core/output.py`. Extract to `formatters/` in a later phase if they grow.

### 6.3 `mcp/tools.py` will be a large registration file

All 22+ MCP tools with their schemas, descriptions, and parameter mappings in one file will approach or exceed 500 LOC.

**Suggested fix:** Either auto-generate tool definitions from the command functions (using decorators or introspection), or split `mcp/tools.py` by domain (testing, hierarchy, scene, etc.).

---

## 7. Missing Sections

1. **Logging architecture** -- stderr vs stdout separation is mentioned but not specified. Where does `logging.getLogger()` output go? Is it always stderr? How does `--verbose` change this?

2. **Multiple Unity instances** -- What if two Unity projects are open? The bridge paths are per-project, but auto-detection could pick the wrong one.

3. **Upgrade path** -- How does a user with the current monolithic `unity_bridge_mcp_server.py` upgrade to the new CLI? Is there a migration script? Does `pip install -e .` conflict with the existing `requirements.txt` virtual environment?

4. **Performance benchmarks** -- No baseline metrics for comparison. How fast should `status` be? What's the target latency for passthrough commands?

5. **CI/CD usage** -- The spec mentions "CI pipelines" in the problem statement but never shows how the CLI would work in CI (where Unity might not be running or might be in batch mode).

---

## 8. Questions for the Spec Author

1. Has `Mono.CSharp.Evaluator` been validated to work in Unity 6's editor runtime? This is the linchpin of the `script` command.

2. Is `test watch` actually needed for v1? Unity already recompiles on file save. Running `tdd` manually or via a shell alias (`alias tdd='unity-bridge tdd'`) may be sufficient.

3. Should `snapshot diff` compare component data, or just hierarchy structure? The current spec captures hierarchy only, but component state changes (like a health value changing) would be invisible.

4. The spec says "no divergent implementations" (G2), but the `tdd` and `test watch` commands are CLI-only compound workflows. Should they also be exposed as MCP tools?

---

## Verdict

The spec is solid at the architectural level. The shared-core pattern, the phased migration, and the backward compatibility strategy are all correct. The main risks are:

1. **`script` command feasibility** -- needs a spike before committing to the spec
2. **Output flag confusion** -- `--json` defaulting to true while being a flag is contradictory
3. **Short flag conflicts** -- `-p` for both `--project` and `--platform`
4. **Concurrent CLI and memory growth in watch/log** -- need bounds

Address the 3 CRITICAL items and the top HIGH items before starting implementation. The MEDIUM and LOW items can be resolved during development.

---

REVIEW COMPLETE
