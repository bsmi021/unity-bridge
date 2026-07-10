# Subagent Brief: Unity 6.5 Public Editor API Universe

Last updated: 2026-07-09

## Objective

Determine the authoritative, reproducible universe of public APIs available to
Unity Editor 6.5 (`6000.5`) and organize it into an audit-ready taxonomy that
can be compared with `unity-bridge`.

## Scope

- Use current official Unity 6.5 documentation and official Unity source or
  locally installed `6000.5` assemblies when available.
- Distinguish core Editor APIs, runtime APIs usable in Editor, package-provided
  Editor APIs, obsolete APIs, internal APIs, and UI-only workflows with no
  public API.
- Determine whether official docs expose a machine-readable index or whether
  reflection/API scraping is required.
- Propose a reproducible inventory schema at namespace/type/member and
  capability-family levels.
- Identify version/package/define constraints that affect reachability.

## Non-Goals

- Do not edit repository files.
- Do not treat internal/unsupported reflection as a required public contract.
- Do not infer full API coverage from namespace-level examples.
- Do not use third-party summaries where an official primary source exists.

## Sources

- Official Unity 6.5 Manual and Scripting API.
- Official UnityCsReference or other Unity-owned source repositories.
- Local Unity Hub installation and assemblies, if present.
- `docs/unity-6.5-capability-gap-audit.md` only as a prior hypothesis, not as
  authoritative API inventory.

## Required Output

Return a structured report with:

1. The exact Unity 6.5 version/source baseline used.
2. Official URLs and local paths inspected.
3. Reproducible counts if obtainable, with the extraction method.
4. A complete top-level taxonomy of public API families.
5. A proposed machine-readable inventory record/schema.
6. Known blind spots and why they cannot honestly be called covered.

## Validation

Corroborate documentation-index findings against at least one local assembly or
official source-code representation when possible. Clearly separate verified
facts from proposed methodology.

## Blockers

Report documentation availability, local install absence, package ambiguity,
or version drift explicitly. Do not silently substitute Unity 6.4 or Unity 6.6.
