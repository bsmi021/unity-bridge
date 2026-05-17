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

        private static Dictionary<string, TestRunContext> _activeTestRuns = new Dictionary<string, TestRunContext>();

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

                // Create test runner
                var testRunnerApi = ScriptableObject.CreateInstance<TestRunnerApi>();

                // Set up callbacks
                var callbacks = new TestRunCallbacks(command.commandId);
                testRunnerApi.RegisterCallbacks(callbacks);

                var context = new TestRunContext
                {
                    CommandId = command.commandId,
                    StartTime = DateTime.UtcNow,
                    TestRunnerApi = testRunnerApi,
                    Callbacks = callbacks
                };

                // Build filter
                var filter = new Filter
                {
                    testMode = testMode
                };

                if (!string.IsNullOrEmpty(parameters.testFilter))
                {
                    filter.testNames = new[] { parameters.testFilter };
                }

                // Store context
                _activeTestRuns[command.commandId] = context;

                // Execute tests asynchronously
                testRunnerApi.Execute(new ExecutionSettings(filter));

                // Return "running" response immediately
                // The actual results will be written when tests complete
                return BridgeResponse.Running(
                    command.commandId,
                    command.commandType,
                    $"{{\"message\":\"Tests started at {context.StartTime:O}\"}}"
                );
            }
            catch (Exception ex)
            {
                BridgeLogger.LogError($"Error: {ex}");
                return BridgeResponse.Error(command.commandId, command.commandType, ex.ToString());
            }
        }

        /// <summary>
        /// Called by TestRunCallbacks when tests complete.
        /// </summary>
        public static void OnTestRunComplete(string commandId, ITestResultAdaptor testResults)
        {
            if (!_activeTestRuns.TryGetValue(commandId, out var context))
            {
                BridgeLogger.LogError($"No context found for command ID: {commandId}");
                return;
            }

            try
            {
                var result = ParseTestResults(testResults);
                var duration = (DateTime.UtcNow - context.StartTime).TotalSeconds;
                result.durationSeconds = duration;

                var resultJson = JsonUtility.ToJson(result);

                BridgeLogger.LogInfo($"Tests completed: {result.passed}/{result.total} passed in {duration:F2}s");

                // Write final success response
                ClaudeUnityBridge.WriteResponseStatic(
                    BridgeResponse.Success(commandId, "run-tests", resultJson)
                );
            }
            catch (Exception ex)
            {
                BridgeLogger.LogError($"Error processing results: {ex}");
                ClaudeUnityBridge.WriteResponseStatic(
                    BridgeResponse.Error(commandId, "run-tests", ex.ToString())
                );
            }
            finally
            {
                // Cleanup
                context.TestRunnerApi.UnregisterCallbacks(context.Callbacks);
                _activeTestRuns.Remove(commandId);
            }
        }

        /// <summary>
        /// Parse Unity test results from TestRunner API into an NUnit-style
        /// summary, including per-test breakdown so callers don't have to
        /// re-parse the raw log.
        /// </summary>
        private static RunTestsResult ParseTestResults(ITestResultAdaptor testResults)
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

        /// <summary>
        /// Context for an active test run.
        /// </summary>
        private class TestRunContext
        {
            public string CommandId;
            public DateTime StartTime;
            public TestRunnerApi TestRunnerApi;
            public TestRunCallbacks Callbacks;
        }

        /// <summary>
        /// Callbacks for TestRunner API.
        /// </summary>
        private class TestRunCallbacks : ICallbacks
        {
            private readonly string _commandId;

            public TestRunCallbacks(string commandId)
            {
                _commandId = commandId;
            }

            public void RunStarted(ITestAdaptor testsToRun)
            {
                BridgeLogger.LogDebug($"Test run started: {testsToRun.FullName}");
            }

            public void RunFinished(ITestResultAdaptor result)
            {
                BridgeLogger.LogDebug("Test run finished");
                OnTestRunComplete(_commandId, result);
            }

            public void TestStarted(ITestAdaptor test)
            {
                // Optional: could report individual test progress
            }

            public void TestFinished(ITestResultAdaptor result)
            {
                // Optional: could report individual test results
            }
        }
    }
}
