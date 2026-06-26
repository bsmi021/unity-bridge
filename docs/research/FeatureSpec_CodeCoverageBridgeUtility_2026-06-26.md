# FeatureSpec_CodeCoverageBridgeUtility_2026-06-26

Last updated: 2026-06-26

## Feature Overview

Unity Bridge now has an optional Code Coverage utility surface. The bridge can
check whether `com.unity.testtools.codecoverage` is installed, install it through
Unity Package Manager, invoke the package's on-demand recording API when present,
and inspect existing coverage report artifacts.

## Current Scope

- CLI group: `unity-bridge coverage`
- Bridge command type: `code-coverage`
- MCP compatibility tool: `unity_code_coverage`
- Supported operations: `availability`, `install`, `start-recording`,
  `pause-recording`, `resume-recording`, `stop-recording`, `find-reports`,
  and `summarize`

## Optional Package Rule

The C# bridge must not import `UnityEditor.TestTools.CodeCoverage` directly.
Projects without the package must still compile after `unity-bridge install`.
Recording operations use reflection and return a structured unavailable result
when the package API is absent. Availability, report discovery, and report
summarization can run even when the package is missing.

## Evidence Summary

Unity's Code Coverage package exposes on-demand recording through the
`CodeCoverage` scripting API (`StartRecording`, `PauseRecording`,
`UnpauseRecording`, `StopRecording`). The package also supports batchmode test
coverage through `-enableCodeCoverage`, `-coverageResultsPath`, and
`-coverageOptions`, including HTML, badge, additional report, metric, and filter
options. This implementation does not yet wrap batchmode Unity launches; it
creates the in-editor optional utility and artifact inspection layer first.

## Behavioral Rules

- `availability` always returns success and reports `packageAvailable` and
  `apiAvailable`.
- `install` is mutating, serialized by a pending Package Manager request, and
  returns a running response until `Client.Add` completes.
- Recording operations require the Code Coverage API. Missing package/API is an
  expected structured error, not a bridge compile failure.
- `find-reports` scans the requested path, or `CoverageResults` and
  `CodeCoverage` under the Unity project root by default.
- `summarize` prefers `Summary.json`, then `Summary.xml`, then OpenCover
  `TestCoverageResults_*.xml`.

## Follow-On Capabilities

- Add a `test run --coverage` orchestration mode once the preferred in-editor
  coverage preferences and report generation behavior are proven in live Unity.
- Add batchmode coverage command generation for CI-style runs that need
  `-enableCodeCoverage` and `-coverageOptions`.
- Add threshold gates, for example minimum line/method coverage, after report
  parsing is validated across current Unity package versions.
