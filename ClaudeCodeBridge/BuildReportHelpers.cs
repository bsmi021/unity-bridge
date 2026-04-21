using System;
using System.Collections.Generic;
using System.Linq;
using UnityEditor.Build.Reporting;
using UnityEngine;

namespace BWS.Editor.ClaudeCodeBridge
{
    /// <summary>
    /// Shared helpers that populate structured BuildReport fields on a
    /// <see cref="BuildOperationResult"/>. Phase 7a-2 — callers want the
    /// parsed report data (size, time, per-step breakdown, largest assets)
    /// without re-scraping Editor.log.
    /// </summary>
    public static class BuildReportHelpers
    {
        private const int MAX_STEPS = 50;
        private const int MAX_LARGEST_ASSETS = 25;

        /// <summary>
        /// Fill <see cref="BuildOperationResult.summary"/>, step breakdown,
        /// largest-asset list, and error/warning counts from the BuildReport.
        /// </summary>
        public static void PopulateFromReport(BuildOperationResult result, BuildReport report)
        {
            if (report == null || result == null) return;

            var summary = report.summary;
            result.summary = new BuildReportSummary
            {
                result = summary.result.ToString(),
                platform = summary.platform.ToString(),
                platformGroup = summary.platformGroup.ToString(),
                totalSizeBytes = (long)summary.totalSize,
                totalSizeMb = summary.totalSize / (1024.0 * 1024.0),
                totalTimeSeconds = summary.totalTime.TotalSeconds,
                buildStartedAt = summary.buildStartedAt.ToString("O"),
                buildEndedAt = summary.buildEndedAt.ToString("O"),
                outputPath = summary.outputPath,
                buildGuid = summary.guid.ToString(),
            };

            PopulateSteps(result, report);
            PopulateLargestAssets(result, report);
            CountErrorsAndWarnings(result, report);
        }

        private static void PopulateSteps(BuildOperationResult result, BuildReport report)
        {
            if (report.steps == null) return;
            var steps = report.steps
                .OrderByDescending(s => s.duration.TotalSeconds)
                .Take(MAX_STEPS);

            foreach (var step in steps)
            {
                result.buildSteps.Add(new BuildReportStep
                {
                    name = step.name,
                    durationSeconds = step.duration.TotalSeconds,
                    depth = step.depth,
                    messageCount = step.messages?.Length ?? 0,
                });
            }
        }

        private static void PopulateLargestAssets(BuildOperationResult result, BuildReport report)
        {
            // BuildReport.packedAssets is only available on completed builds and
            // is accessed via GetRoleInfos in newer Unity versions; fall back
            // gracefully if not present.
            var assets = new List<(string path, long size, string kind)>();
            try
            {
                if (report.packedAssets != null)
                {
                    foreach (var pack in report.packedAssets)
                    {
                        if (pack?.contents == null) continue;
                        foreach (var content in pack.contents)
                        {
                            assets.Add((content.sourceAssetPath,
                                        (long)content.packedSize,
                                        content.type?.Name));
                        }
                    }
                }
            }
            catch
            {
                // packedAssets not accessible for this platform / Unity version.
            }

            var ranked = assets
                .OrderByDescending(a => a.size)
                .Take(MAX_LARGEST_ASSETS);
            foreach (var a in ranked)
            {
                result.largestAssets.Add(new BuildReportAsset
                {
                    assetPath = a.path,
                    sizeBytes = a.size,
                    sizeMb = a.size / (1024.0 * 1024.0),
                    kind = a.kind,
                });
            }
        }

        private static void CountErrorsAndWarnings(BuildOperationResult result, BuildReport report)
        {
            if (report.steps == null) return;
            int errors = 0, warnings = 0;
            foreach (var step in report.steps)
            {
                if (step.messages == null) continue;
                foreach (var m in step.messages)
                {
                    if (m.type == LogType.Error || m.type == LogType.Exception || m.type == LogType.Assert)
                        errors++;
                    else if (m.type == LogType.Warning)
                        warnings++;
                }
            }
            result.errorCount = errors;
            result.warningCount = warnings;
        }
    }
}
