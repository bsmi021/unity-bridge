using System;
using System.Collections.Generic;
using System.Linq;
using UnityEditor;
using UnityEditor.TestTools.TestRunner.Api;
using UnityEngine;

namespace BWS.Editor.ClaudeCodeBridge
{
    /// <summary>
    /// Command handler for running Unity tests using the TestRunner API.
    ///
    /// This handler executes Unity tests directly within the open Unity Editor,
    /// providing fast feedback without requiring Unity restart.
    ///
    /// Command JSON format:
    /// {
    ///   "commandId": "guid",
    ///   "commandType": "run-tests",
    ///   "timestamp": "2025-10-05T17:00:00Z",
    ///   "parametersJson": "{\"testFilter\":\"CombatControllerTests\",\"testPlatform\":\"EditMode\"}"
    /// }
    /// </summary>
    public class RunTestsCommandHandler : ICommandHandler
    {
        public string CommandType => "run-tests";

        public BridgeResponse Execute(BridgeCommand command)
        {
            try
            {
                // Parse parameters
                var parameters = JsonUtility.FromJson<RunTestsParams>(command.parametersJson ?? "{}");
                if (parameters == null)
                    parameters = new RunTestsParams();

                BridgeLogger.LogDebug($"Executing tests with filter: {parameters.testFilter ?? "all"}, platform: {parameters.testPlatform}");

                // Determine test mode
                var testMode = parameters.testPlatform == "PlayMode" ? TestMode.PlayMode : TestMode.EditMode;

                // Build filter
                var filter = new Filter
                {
                    testMode = testMode
                };

                if (!string.IsNullOrEmpty(parameters.testFilter))
                {
                    filter.testNames = new[] { parameters.testFilter };
                }

                // Start the run via the reload-surviving reporter. It persists the
                // command id in SessionState and writes the terminal response when
                // RunFinished fires — even across the play-mode domain reload.
                BridgeTestRunReporter.BeginRunAndExecute(command.commandId, filter);

                // Return "running" immediately; results are written on completion.
                return BridgeResponse.Running(
                    command.commandId,
                    command.commandType,
                    $"{{\"message\":\"Tests started at {DateTime.UtcNow:O}\"}}"
                );
            }
            catch (Exception ex)
            {
                BridgeLogger.LogError($"Error: {ex}");
                return BridgeResponse.Error(command.commandId, command.commandType, ex.ToString());
            }
        }

        /// <summary>
        /// Parse Unity test results from TestRunner API into an NUnit-style
        /// summary, including per-test breakdown so callers don't have to
        /// re-parse the raw log. Public so the reload-surviving reporter can
        /// reuse it.
        /// </summary>
        public static RunTestsResult ParseTestResults(ITestResultAdaptor testResults)
        {
            var result = new RunTestsResult();
            var allResults = CollectAllResults(testResults).ToList();
            var cases = allResults.Where(r => r.Test.IsSuite == false).ToList();

            result.total = cases.Count;
            result.passed = cases.Count(r => r.TestStatus == TestStatus.Passed);
            result.failed = cases.Count(r => r.TestStatus == TestStatus.Failed);
            result.skipped = cases.Count(r => r.TestStatus == TestStatus.Skipped);
            result.inconclusive = cases.Count(r => r.TestStatus == TestStatus.Inconclusive);
            result.resultState = testResults.ResultState ?? testResults.TestStatus.ToString();
            result.testSuite = testResults.Test?.FullName;

            foreach (var c in cases)
            {
                string assembly = null;
                string categories = null;
                try
                {
                    assembly = c.Test?.TypeInfo?.Assembly?.GetName()?.Name;
                }
                catch { }
                try
                {
                    if (c.Test?.Categories != null && c.Test.Categories.Length > 0)
                        categories = string.Join(";", c.Test.Categories);
                }
                catch { }

                result.testCases.Add(new TestCaseInfo
                {
                    fullName = c.Test?.FullName,
                    status = c.TestStatus.ToString(),
                    durationSeconds = c.Duration,
                    assembly = assembly,
                    categories = categories,
                });

                if (c.TestStatus == TestStatus.Failed)
                {
                    result.failures.Add(new TestFailureInfo
                    {
                        testName = c.Test?.FullName,
                        errorMessage = c.Message ?? "No message",
                        stackTrace = c.StackTrace ?? ""
                    });
                }
            }

            return result;
        }

        /// <summary>
        /// Recursively collect all test results.
        /// </summary>
        private static IEnumerable<ITestResultAdaptor> CollectAllResults(ITestResultAdaptor result)
        {
            yield return result;

            if (result.HasChildren)
            {
                foreach (var child in result.Children)
                {
                    foreach (var childResult in CollectAllResults(child))
                    {
                        yield return childResult;
                    }
                }
            }
        }

    }
}
