# Unity Bridge Documentation Instructions

Last updated: 2026-07-05

This directory contains durable plans, audits, research, and implementation
notes. Keep documentation evidence-backed and explicit about proof boundaries.

## Freshness And Routing

- `docs/index.md` is the documentation entry point.
- Durable human-authored docs should include `Last updated: YYYY-MM-DD` near the
  top unless they are preserved historical artifacts.
- Link new durable docs from `docs/index.md` when they are meant to be found
  later.

## Source And CLI Verification

- Before making current command-surface claims, verify with
  `uv run unity-bridge --help` and targeted command help.
- Before making implementation claims, inspect the source/tests that prove the
  behavior.
- Historical docs may keep old MCP context, but new or refreshed docs must not
  repeat MCP-server guidance as current behavior. The internal MCP interface is
  retired.

## Plans And Research

- Implementation plans must name scope, non-goals, acceptance criteria, test
  gates, and definition of done.
- Research briefs should state sources inspected, proof limits, and whether the
  work is read-only.
- Prefer official Unity docs, local source, and live CLI output for current API
  or command claims.

## Proof Boundaries

- Do not claim implementation completion from a plan, audit, or research note.
- Separate source-level evidence, pytest evidence, package/install evidence, and
  live Unity Editor proof.
- Stale-doc cleanup should be scoped explicitly; do not mix broad documentation
  cleanup into feature phases unless the plan includes it.
