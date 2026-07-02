using System;
using System.IO;
using System.Reflection;
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
        private const string RunGuidKey = "UnityBridge.RunTests.RunGuid";
        private const string StartTicksKey = "UnityBridge.RunTests.StartTicks";
        private const string StartedCountKey = "UnityBridge.RunTests.StartedCount";
        private const string FinishedCountKey = "UnityBridge.RunTests.FinishedCount";
        private const string PassedCountKey = "UnityBridge.RunTests.PassedCount";
        private const string FailedCountKey = "UnityBridge.RunTests.FailedCount";
        private const string SkippedCountKey = "UnityBridge.RunTests.SkippedCount";
        private const string InconclusiveCountKey = "UnityBridge.RunTests.InconclusiveCount";
        private const string CurrentTestKey = "UnityBridge.RunTests.CurrentTest";

        private static TestRunnerApi _api;

        static BridgeTestRunReporter()
        {
            // Re-register on every domain load so callbacks survive the
            // play-mode domain reload and still report the in-flight run.
            _api = ScriptableObject.CreateInstance<TestRunnerApi>();
            RegisterCallbacks();
            Diag($"ctor: registered callbacks; pendingCmdId='{SessionState.GetString(CommandIdKey, "")}'");
        }

        private static void RegisterCallbacks()
        {
            var callbacks = new Callbacks();
            var staticMethod = FindRegistrationMethod(
                typeof(TestRunnerApi),
                "RegisterTestCallback",
                BindingFlags.Public | BindingFlags.Static);
            if (staticMethod is not null)
            {
                InvokeRegistrationMethod(staticMethod, null, callbacks);
                return;
            }

            var instanceMethod = FindRegistrationMethod(
                typeof(TestRunnerApi),
                "RegisterCallbacks",
                BindingFlags.Public | BindingFlags.Instance);
            if (instanceMethod is not null)
            {
                InvokeRegistrationMethod(instanceMethod, _api, callbacks);
                return;
            }

            BridgeLogger.LogWarning("No Unity Test Runner callback registration API was found.");
        }

        private static MethodInfo FindRegistrationMethod(
            Type apiType, string methodName, BindingFlags flags)
        {
            foreach (var method in apiType.GetMethods(flags))
            {
                if (method.Name != methodName)
                    continue;
                var parameters = method.GetParameters();
                if (parameters.Length >= 1 && parameters.Length <= 2)
                    return method;
            }
            return null;
        }

        private static void InvokeRegistrationMethod(
            MethodInfo method, object target, Callbacks callbacks)
        {
            if (method.ContainsGenericParameters)
                method = method.MakeGenericMethod(typeof(Callbacks));
            var parameters = method.GetParameters();
            var args = parameters.Length == 2
                ? new object[] { callbacks, 0 }
                : new object[] { callbacks };
            method.Invoke(target, args);
        }

        // --- TEMP diagnostics: file-based lifecycle log that survives reloads ---
        private static void Diag(string message)
        {
            try
            {
                var root = Directory.GetParent(Application.dataPath).FullName;
                var path = Path.Combine(root, ".claude", "unity", "diagnostics", "test-reporter.log");
                Directory.CreateDirectory(Path.GetDirectoryName(path));
                File.AppendAllText(path, $"{DateTime.UtcNow:O} | {message}{Environment.NewLine}");
            }
            catch { }
        }

        /// <summary>
        /// Persist the originating bridge command id and start a test run on the
        /// shared, reload-surviving TestRunnerApi instance.
        /// </summary>
        public static void BeginRunAndExecute(string commandId, Filter filter)
        {
            SessionState.SetString(CommandIdKey, commandId ?? "");
            SessionState.SetString(StartTicksKey, DateTime.UtcNow.Ticks.ToString());
            ResetProgressState();
            Diag($"BeginRunAndExecute: cmdId={commandId}; mode={filter?.testMode}");
            var runGuid = _api.Execute(new ExecutionSettings(filter));
            SessionState.SetString(RunGuidKey, runGuid ?? "");
            Diag($"BeginRunAndExecute: Execute() returned runGuid={runGuid}");
        }

        public static CancelTestsResult CancelRun(string targetCommandId = null)
        {
            var commandId = SessionState.GetString(CommandIdKey, "");
            var runGuid = SessionState.GetString(RunGuidKey, "");
            if (string.IsNullOrEmpty(commandId))
                return CancelResult(targetCommandId, runGuid, false, false, "No bridge test run is active");
            if (!string.IsNullOrEmpty(targetCommandId) && targetCommandId != commandId)
                return CancelResult(commandId, runGuid, false, false, "No matching bridge test run is active");
            if (string.IsNullOrEmpty(runGuid))
                return CancelResult(commandId, runGuid, false, false, "Active test run has no Unity run guid");

            var cancelRequested = TestRunnerApi.CancelTestRun(runGuid);
            var activeRun = cancelRequested;
            var message = cancelRequested
                ? "Unity test run cancellation requested"
                : "Unity test run was not active or was already canceling";
            if (cancelRequested)
                WriteTestProgress(commandId, "cancel_requested", SessionState.GetString(CurrentTestKey, ""));
            return CancelResult(commandId, runGuid, activeRun, cancelRequested, message);
        }

        private static CancelTestsResult CancelResult(
            string commandId,
            string runGuid,
            bool activeRun,
            bool cancelRequested,
            string message)
        {
            return new CancelTestsResult
            {
                targetCommandId = commandId,
                runGuid = runGuid,
                activeRun = activeRun,
                cancelRequested = cancelRequested,
                message = message
            };
        }

        private static void Clear()
        {
            SessionState.EraseString(CommandIdKey);
            SessionState.EraseString(RunGuidKey);
            SessionState.EraseString(StartTicksKey);
            SessionState.EraseInt(StartedCountKey);
            SessionState.EraseInt(FinishedCountKey);
            SessionState.EraseInt(PassedCountKey);
            SessionState.EraseInt(FailedCountKey);
            SessionState.EraseInt(SkippedCountKey);
            SessionState.EraseInt(InconclusiveCountKey);
            SessionState.EraseString(CurrentTestKey);
        }

        private static double ElapsedSeconds()
        {
            if (long.TryParse(SessionState.GetString(StartTicksKey, ""), out var ticks))
                return (DateTime.UtcNow - new DateTime(ticks, DateTimeKind.Utc)).TotalSeconds;
            return 0.0;
        }

        private class Callbacks : ICallbacks
        {
            public void RunStarted(ITestAdaptor testsToRun)
            {
                var commandId = SessionState.GetString(CommandIdKey, "");
                Diag($"RunStarted; pendingCmdId='{commandId}'");
                WriteTestProgress(commandId, "started", testsToRun?.FullName);
            }

            public void TestStarted(ITestAdaptor test)
            {
                if (IsSuiteTest(test)) return;
                var commandId = SessionState.GetString(CommandIdKey, "");
                if (string.IsNullOrEmpty(commandId)) return;
                SessionState.SetString(CurrentTestKey, test?.FullName ?? "");
                Increment(StartedCountKey);
                WriteTestProgress(commandId, "running", test?.FullName);
            }

            public void TestFinished(ITestResultAdaptor result)
            {
                if (IsSuiteResult(result)) return;
                var commandId = SessionState.GetString(CommandIdKey, "");
                if (string.IsNullOrEmpty(commandId)) return;
                Increment(FinishedCountKey);
                IncrementStatus(result?.TestStatus);
                WriteTestProgress(commandId, "running", result?.Test?.FullName, result);
            }

            public void RunFinished(ITestResultAdaptor result)
            {
                var commandId = SessionState.GetString(CommandIdKey, "");
                Diag($"RunFinished; pendingCmdId='{commandId}'");
                if (string.IsNullOrEmpty(commandId))
                    return; // Not a bridge-initiated run; ignore.

                try
                {
                    var parsed = RunTestsCommandHandler.ParseTestResults(result);
                    parsed.durationSeconds = ElapsedSeconds();
                    WriteTestResultArtifact(commandId, parsed);
                    WriteTestProgress(commandId, "finished", null, result);
                    ClaudeUnityBridge.WriteResponseStatic(
                        BridgeResponse.Success(commandId, "run-tests", JsonUtility.ToJson(parsed)));
                    Diag($"RunFinished: wrote success response ({parsed.passed}/{parsed.total} passed)");
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

        private static void ResetProgressState()
        {
            SessionState.SetInt(StartedCountKey, 0);
            SessionState.SetInt(FinishedCountKey, 0);
            SessionState.SetInt(PassedCountKey, 0);
            SessionState.SetInt(FailedCountKey, 0);
            SessionState.SetInt(SkippedCountKey, 0);
            SessionState.SetInt(InconclusiveCountKey, 0);
            SessionState.SetString(CurrentTestKey, "");
        }

        private static void WriteTestResultArtifact(string commandId, RunTestsResult result)
        {
            try
            {
                var root = Directory.GetParent(Application.dataPath).FullName;
                var dir = Path.Combine(root, ".claude", "unity", "test-results");
                var artifact = new TestResultArtifact
                {
                    commandId = commandId,
                    writtenAt = DateTime.UtcNow.ToString("O"),
                    result = result
                };
                var json = JsonUtility.ToJson(artifact, true);
                BridgeOperationLedger.WriteAtomic(Path.Combine(dir, $"{commandId}.json"), json);
                BridgeOperationLedger.WriteAtomic(Path.Combine(dir, "latest.json"), json);
            }
            catch (Exception ex)
            {
                BridgeLogger.LogWarning($"Failed to write test result artifact: {ex.Message}");
            }
        }

        private static void WriteTestProgress(
            string commandId, string state, string currentTest, ITestResultAdaptor result = null)
        {
            if (string.IsNullOrEmpty(commandId)) return;
            try
            {
                var root = Directory.GetParent(Application.dataPath).FullName;
                var dir = Path.Combine(root, ".claude", "unity", "test-progress");
                var artifact = BuildProgress(commandId, state, currentTest);
                var json = JsonUtility.ToJson(artifact, true);
                BridgeOperationLedger.WriteAtomic(Path.Combine(dir, $"{commandId}.json"), json);
                BridgeOperationLedger.WriteAtomic(Path.Combine(dir, "latest.json"), json);
                AppendProgressEvent(dir, artifact, result);
            }
            catch (Exception ex)
            {
                BridgeLogger.LogWarning($"Failed to write test progress artifact: {ex.Message}");
            }
        }

        private static TestProgressArtifact BuildProgress(
            string commandId, string state, string currentTest)
        {
            return new TestProgressArtifact
            {
                commandId = commandId,
                writtenAt = DateTime.UtcNow.ToString("O"),
                state = state,
                currentTest = currentTest ?? SessionState.GetString(CurrentTestKey, ""),
                started = SessionState.GetInt(StartedCountKey, 0),
                finished = SessionState.GetInt(FinishedCountKey, 0),
                passed = SessionState.GetInt(PassedCountKey, 0),
                failed = SessionState.GetInt(FailedCountKey, 0),
                skipped = SessionState.GetInt(SkippedCountKey, 0),
                inconclusive = SessionState.GetInt(InconclusiveCountKey, 0),
                durationSeconds = ElapsedSeconds()
            };
        }

        private static void AppendProgressEvent(
            string dir, TestProgressArtifact artifact, ITestResultAdaptor result)
        {
            var evt = new TestProgressEvent
            {
                commandId = artifact.commandId,
                timestamp = artifact.writtenAt,
                state = artifact.state,
                testName = artifact.currentTest,
                status = result?.TestStatus.ToString(),
                durationSeconds = result?.Duration ?? 0.0,
                message = result?.Message
            };
            Directory.CreateDirectory(dir);
            File.AppendAllText(
                Path.Combine(dir, $"{artifact.commandId}.events.jsonl"),
                JsonUtility.ToJson(evt) + Environment.NewLine);
        }

        private static void IncrementStatus(TestStatus? status)
        {
            if (status == TestStatus.Passed) Increment(PassedCountKey);
            else if (status == TestStatus.Failed) Increment(FailedCountKey);
            else if (status == TestStatus.Skipped) Increment(SkippedCountKey);
            else if (status == TestStatus.Inconclusive) Increment(InconclusiveCountKey);
        }

        private static void Increment(string key)
        {
            SessionState.SetInt(key, SessionState.GetInt(key, 0) + 1);
        }

        private static bool IsSuiteTest(ITestAdaptor test)
        {
            try { return test?.IsSuite == true; }
            catch { return false; }
        }

        private static bool IsSuiteResult(ITestResultAdaptor result)
        {
            try { return result?.Test?.IsSuite == true; }
            catch { return false; }
        }

        [Serializable]
        private class TestResultArtifact
        {
            public string commandId;
            public string writtenAt;
            public RunTestsResult result;
        }

        [Serializable]
        private class TestProgressArtifact
        {
            public string commandId;
            public string writtenAt;
            public string state;
            public string currentTest;
            public int started;
            public int finished;
            public int passed;
            public int failed;
            public int skipped;
            public int inconclusive;
            public double durationSeconds;
        }

        [Serializable]
        private class TestProgressEvent
        {
            public string commandId;
            public string timestamp;
            public string state;
            public string testName;
            public string status;
            public double durationSeconds;
            public string message;
        }
    }
}
