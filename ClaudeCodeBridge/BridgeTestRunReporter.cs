using System;
using UnityEditor;
using UnityEditor.TestTools.TestRunner.Api;
using UnityEngine;

namespace BWS.Editor.ClaudeCodeBridge
{
    /// <summary>
    /// Reload-surviving Test Runner reporter.
    ///
    /// PlayMode test runs enter play mode, which triggers a domain reload that
    /// wipes any in-memory test-run context and per-run callback registration.
    /// By registering callbacks from [InitializeOnLoad] on every domain load and
    /// persisting the originating bridge command id in SessionState, the final
    /// RunFinished result is still reported back to the correct bridge command
    /// after the reload. EditMode runs (no reload) are reported the same way, so
    /// there is a single code path for both platforms.
    /// </summary>
    [InitializeOnLoad]
    public static class BridgeTestRunReporter
    {
        internal const string CommandIdKey = "UnityBridge.RunTests.CommandId";
        private const string StartTicksKey = "UnityBridge.RunTests.StartTicks";

        private static TestRunnerApi _api;

        static BridgeTestRunReporter()
        {
            // Re-register on every domain load so callbacks survive the
            // play-mode domain reload and still report the in-flight run.
            _api = ScriptableObject.CreateInstance<TestRunnerApi>();
            _api.RegisterCallbacks(new Callbacks());
        }

        /// <summary>
        /// Persist the originating bridge command id and start a test run on the
        /// shared, reload-surviving TestRunnerApi instance.
        /// </summary>
        public static void BeginRunAndExecute(string commandId, Filter filter)
        {
            SessionState.SetString(CommandIdKey, commandId ?? "");
            SessionState.SetString(StartTicksKey, DateTime.UtcNow.Ticks.ToString());
            _api.Execute(new ExecutionSettings(filter));
        }

        private static void Clear()
        {
            SessionState.EraseString(CommandIdKey);
            SessionState.EraseString(StartTicksKey);
        }

        private static double ElapsedSeconds()
        {
            if (long.TryParse(SessionState.GetString(StartTicksKey, ""), out var ticks))
                return (DateTime.UtcNow - new DateTime(ticks, DateTimeKind.Utc)).TotalSeconds;
            return 0.0;
        }

        private class Callbacks : ICallbacks
        {
            public void RunStarted(ITestAdaptor testsToRun) { }
            public void TestStarted(ITestAdaptor test) { }
            public void TestFinished(ITestResultAdaptor result) { }

            public void RunFinished(ITestResultAdaptor result)
            {
                var commandId = SessionState.GetString(CommandIdKey, "");
                if (string.IsNullOrEmpty(commandId))
                    return; // Not a bridge-initiated run; ignore.

                try
                {
                    var parsed = RunTestsCommandHandler.ParseTestResults(result);
                    parsed.durationSeconds = ElapsedSeconds();
                    ClaudeUnityBridge.WriteResponseStatic(
                        BridgeResponse.Success(commandId, "run-tests", JsonUtility.ToJson(parsed)));
                    BridgeLogger.LogInfo($"Tests completed: {parsed.passed}/{parsed.total} passed");
                }
                catch (Exception ex)
                {
                    BridgeLogger.LogError($"Error reporting test results: {ex}");
                    ClaudeUnityBridge.WriteResponseStatic(
                        BridgeResponse.Error(commandId, "run-tests", ex.ToString()));
                }
                finally
                {
                    Clear();
                }
            }
        }
    }
}
