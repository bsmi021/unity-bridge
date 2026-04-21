"""Structured report extraction helpers.

Phase 7a-2 — the C# bridge now populates NUnit-style per-test detail on
``run-tests`` responses and parsed BuildReport data on ``build-operation``
responses. These helpers normalize the payloads for CLI/MCP consumers
and make the structured fields discoverable from Python without needing
to know the C# field names.
"""

from __future__ import annotations

from typing import Any

from unity_bridge.core.bridge import CommandResult


def extract_test_report(result: CommandResult) -> dict[str, Any] | None:
    """Return a normalized NUnit-style summary from a ``run-tests`` result.

    Returns ``None`` if the result is not a successful run-tests payload.
    The returned dict is safe for downstream JSON serialization.
    """
    if not result.success or result.data is None:
        return None

    data = result.data
    return {
        "total": int(data.get("total", 0)),
        "passed": int(data.get("passed", 0)),
        "failed": int(data.get("failed", 0)),
        "skipped": int(data.get("skipped", 0)),
        "inconclusive": int(data.get("inconclusive", 0)),
        "duration_seconds": float(data.get("durationSeconds", 0.0)),
        "result_state": data.get("resultState"),
        "test_suite": data.get("testSuite"),
        "failures": [
            {
                "test_name": f.get("testName"),
                "error_message": f.get("errorMessage"),
                "stack_trace": f.get("stackTrace"),
            }
            for f in data.get("failures", []) or []
        ],
        "test_cases": [
            {
                "full_name": c.get("fullName"),
                "status": c.get("status"),
                "duration_seconds": float(c.get("durationSeconds", 0.0)),
                "assembly": c.get("assembly"),
                "categories": _split_categories(c.get("categories")),
            }
            for c in data.get("testCases", []) or []
        ],
    }


def extract_build_report(result: CommandResult) -> dict[str, Any] | None:
    """Return a normalized BuildReport snapshot from a build-operation result.

    Populated fields mirror ``BuildReport`` (platform, total size, timing,
    top N slowest steps, top N largest assets, error/warning counts).
    Returns ``None`` when the payload has no summary (validate-only /
    in-progress responses).
    """
    if not result.success or result.data is None:
        return None

    data = result.data
    summary = data.get("summary")
    if summary is None:
        return None

    return {
        "result": summary.get("result"),
        "platform": summary.get("platform"),
        "platform_group": summary.get("platformGroup"),
        "total_size_bytes": int(summary.get("totalSizeBytes", 0)),
        "total_size_mb": float(summary.get("totalSizeMb", 0.0)),
        "total_time_seconds": float(summary.get("totalTimeSeconds", 0.0)),
        "build_started_at": summary.get("buildStartedAt"),
        "build_ended_at": summary.get("buildEndedAt"),
        "output_path": summary.get("outputPath"),
        "build_guid": summary.get("buildGuid"),
        "error_count": int(data.get("errorCount", 0)),
        "warning_count": int(data.get("warningCount", 0)),
        "build_steps": [
            {
                "name": s.get("name"),
                "duration_seconds": float(s.get("durationSeconds", 0.0)),
                "depth": int(s.get("depth", 0)),
                "message_count": int(s.get("messageCount", 0)),
            }
            for s in data.get("buildSteps", []) or []
        ],
        "largest_assets": [
            {
                "asset_path": a.get("assetPath"),
                "size_bytes": int(a.get("sizeBytes", 0)),
                "size_mb": float(a.get("sizeMb", 0.0)),
                "kind": a.get("kind"),
            }
            for a in data.get("largestAssets", []) or []
        ],
    }


def _split_categories(raw: str | None) -> list[str]:
    if not raw:
        return []
    return [c for c in raw.split(";") if c]
