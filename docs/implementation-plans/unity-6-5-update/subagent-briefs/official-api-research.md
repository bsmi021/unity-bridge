# Official Unity 6.5 API Research Brief

Last updated: 2026-07-02

## Context

Workspace: `C:\Projects\unity-bridge`
Branch target: `codex/unity-6-5-update`
Primary plan: `docs/implementation-plans/unity-6-5-update/unity-6-5-update-implementation-plan.md`
Execution guide: `docs/implementation-plans/unity-6-5-update/unity-6-5-update-execution-guide.md`

## Task

Perform read-only research for Unity 6.5 migration risks and API shape. Use
official Unity documentation/package API references first, then GitHub only for
comparative examples if official docs are incomplete.

## Questions To Answer

1. What are the Unity 6000.5-safe APIs or guards for Build Profile creation?
2. What lifecycle callback attributes or APIs are additive in Unity 6.5, and
   what legacy fallback should remain?
3. What Test Framework callback APIs are current versus obsolete around
   `RegisterCallbacks`, `RegisterTestCallback<T>`, and list retrieval?
4. What profiler frame APIs should be used for raw/hierarchy frame data, sample
   IDs, allocation info, and obsolete InstanceID replacements?
5. Are Addressables `BuildPlayerContent` overloads/result semantics documented
   clearly enough to prove failure propagation?

## Deliverable

Return a concise report with links, exact API names, recommended guards, and any
uncertainties. Do not edit files.
