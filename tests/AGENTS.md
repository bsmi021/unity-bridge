# Unity Bridge Test Instructions

Last updated: 2026-07-05

This subtree owns pytest coverage for the Python CLI, bridge protocol helpers,
packaged skill metadata, and Unity-facing integration smoke tests.

## Test Entry Points

```powershell
uv run pytest tests/unit/
uv run pytest tests/
uv run pytest tests --cov=unity_bridge --cov-report=term-missing --cov-fail-under=90
```

Use focused tests while developing, but do not treat a focused run as final
publish proof.

## Unit Tests

- Unit tests must not require a running Unity Editor.
- Mock `DirectBridge` or use the shared fake bridge/project fixtures from
  `tests/conftest.py`.
- Use `tmp_path` and fixture JSON instead of real Unity project state.
- Keep Arrange/Act/Assert structure clear when adding behavior tests.

## Integration Tests

- Mark Unity-required tests with `@pytest.mark.integration`.
- State whether a test is a subprocess smoke test, heartbeat/readiness-gated
  bridge test, or real Unity Editor test.
- If Unity is unavailable, report the skipped/blocked proof boundary instead of
  treating it as product validation.

## Stale Test Docs

- `tests/README.md` and `tests/TEST_SUMMARY.md` contain historical MCP-era
  wording. Do not use them as current truth without rechecking source, root
  `AGENTS.md`, and the live CLI help.
- New test guidance should prefer this file, root `AGENTS.md`, `README.md`, and
  executable pytest evidence.
