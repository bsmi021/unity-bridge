#if UNITY_6000_0_OR_NEWER
using System.Collections.Generic;
using System.Linq;
using UnityEditor.Build.Reporting;
using UnityEngine;

namespace BWS.Editor.ClaudeCodeBridge
{
    public static class BuildProfileBuildHelpers
    {
        private const int MAX_STEPS = 50;
        private const int MAX_LARGEST_ASSETS = 25;

        public static void PopulateFromReport(BuildProfileOperationResult result, BuildReport report)
        {
            if (result == null || report == null)
                return;

            PopulateSummary(result, report);
            PopulateSteps(result, report);
            PopulateLargestAssets(result, report);
            CountErrorsAndWarnings(result, report);
        }

        private static void PopulateSummary(BuildProfileOperationResult result, BuildReport report)
        {
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
        }

        private static void PopulateSteps(BuildProfileOperationResult result, BuildReport report)
        {
            if (report.steps == null)
                return;

            foreach (var step in report.steps.OrderByDescending(s => s.duration.TotalSeconds)
                         .Take(MAX_STEPS))
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

        private static void PopulateLargestAssets(BuildProfileOperationResult result, BuildReport report)
        {
            var assets = new List<(string path, long size, string kind)>();
            try
            {
                if (report.packedAssets == null)
                    return;

                foreach (var pack in report.packedAssets)
                {
                    if (pack?.contents == null) continue;
                    foreach (var content in pack.contents)
                        assets.Add((content.sourceAssetPath, (long)content.packedSize, content.type?.Name));
                }
            }
            catch
            {
                return;
            }

            foreach (var asset in assets.OrderByDescending(a => a.size).Take(MAX_LARGEST_ASSETS))
            {
                result.largestAssets.Add(new BuildReportAsset
                {
                    assetPath = asset.path,
                    sizeBytes = asset.size,
                    sizeMb = asset.size / (1024.0 * 1024.0),
                    kind = asset.kind,
                });
            }
        }

        private static void CountErrorsAndWarnings(BuildProfileOperationResult result, BuildReport report)
        {
            if (report.steps == null)
                return;

            foreach (var step in report.steps)
            {
                if (step.messages == null) continue;
                foreach (var message in step.messages)
                {
                    if (message.type == LogType.Error ||
                        message.type == LogType.Exception ||
                        message.type == LogType.Assert)
                        result.errorCount++;
                    else if (message.type == LogType.Warning)
                        result.warningCount++;
                }
            }
        }
    }
}
#endif
