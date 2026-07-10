using System;
using System.Diagnostics;
using UnityEditor;
using UnityEngine;

namespace BWS.Editor.ClaudeCodeBridge
{
    public sealed class ExecuteScriptJobCommandHandler : ICommandHandler
    {
        public string CommandType => "execute-job";

        public ExecuteScriptJobCommandHandler()
        {
            ExecuteScriptJobCoordinator.EnsureSubscribed();
        }

        public BridgeResponse Execute(BridgeCommand command)
        {
            var parameters = JsonUtility.FromJson<ExecuteScriptParams>(
                command.parametersJson ?? "{}") ?? new ExecuteScriptParams();
            if (!ExecuteScriptCommandHandler.ValidateRequest(parameters, out var message))
                return BridgeResponse.Error(command.commandId, command.commandType, message);
            if (!ExecuteScriptJobCoordinator.TryStart(command, parameters, out message))
                return BridgeResponse.Error(command.commandId, command.commandType, message);
            var status = new ExecuteScriptJobStatus
            {
                targetCommandId = command.commandId,
                state = "prepared",
                timeoutMs = parameters.manifest.timeoutMs,
                cooperative = true,
                preemptible = false,
                message = "Job factory is queued for the next Editor update.",
            };
            return BridgeResponse.Running(
                command.commandId, command.commandType, JsonUtility.ToJson(status));
        }
    }

    [Serializable]
    internal sealed class ExecuteScriptJobStatus
    {
        public string targetCommandId;
        public string state;
        public int timeoutMs;
        public bool cooperative;
        public bool preemptible;
        public string message;
    }

    internal static class ExecuteScriptJobCoordinator
    {
        private static ExecuteScriptPendingJob _active;
        private static bool _subscribed;

        public static bool HasActiveJob => _active != null;

        public static void EnsureSubscribed()
        {
            if (_subscribed)
                return;
            EditorApplication.update += UpdatePendingJob;
            _subscribed = true;
        }

        public static bool BlocksCommand(string commandType)
        {
            return HasActiveJob && commandType != "cancel-execute-job";
        }

        public static bool TryStart(
            BridgeCommand command,
            ExecuteScriptParams parameters,
            out string message)
        {
            if (_active != null)
            {
                message = "Another cooperative execute job is already active.";
                return false;
            }
            if (!ExecuteScriptMutationScope.TryBegin(
                parameters.manifest, out var mutation, out message))
            {
                return false;
            }
            _active = new ExecuteScriptPendingJob(command, parameters, mutation);
            message = "";
            return true;
        }

        public static bool RequestCancellation(string targetCommandId, out string message)
        {
            if (_active == null || _active.CommandId != targetCommandId)
            {
                message = $"No active cooperative execute job matches {targetCommandId}.";
                return false;
            }
            _active.RequestCancellation();
            message = "";
            return true;
        }

        private static void UpdatePendingJob()
        {
            if (_active == null)
                return;
            try
            {
                if (_active.Advance())
                    _active = null;
            }
            catch (Exception ex)
            {
                BridgeLogger.LogError($"Cooperative execute-job update failed: {ex}");
                if (_active.FailUnexpectedly(ex))
                    _active = null;
            }
        }
    }

    internal sealed class ExecuteScriptPendingJob
    {
        private readonly BridgeCommand _command;
        private readonly ExecuteScriptParams _parameters;
        private readonly ExecuteScriptMutationScope _mutation;
        private readonly ExecuteScriptLogCapture _logs = new ExecuteScriptLogCapture();
        private readonly Stopwatch _stopwatch = Stopwatch.StartNew();
        private ExecuteScriptOutcome _outcome;
        private ExecuteScriptJobController _controller;
        private BridgeResponse _terminalResponse;
        private bool _cancellationRequested;
        private bool _resourcesFinalized;

        public string CommandId => _command.commandId;

        public ExecuteScriptPendingJob(
            BridgeCommand command,
            ExecuteScriptParams parameters,
            ExecuteScriptMutationScope mutation)
        {
            _command = command;
            _parameters = parameters;
            _mutation = mutation;
        }

        public void RequestCancellation()
        {
            _cancellationRequested = true;
            _controller?.RequestCancellation();
        }

        public bool Advance()
        {
            if (_terminalResponse != null)
                return MaterializeTerminal();
            if (_cancellationRequested && _controller == null)
                return Finish(Failure("Job cancellation requested before factory evaluation."));
            if (CheckDeadline() && _controller == null)
                return Finish(Failure("Job deadline exceeded before factory evaluation."));
            if (_controller == null)
                return InitializeFactory();

            var advance = _controller.Advance();
            if (advance.kind == ExecuteScriptJobAdvanceKind.Continue)
                return false;
            if (advance.kind == ExecuteScriptJobAdvanceKind.Completed)
                return Finish(CompleteOutcome(advance.step));
            return Finish(Failure(advance.message));
        }

        public bool FailUnexpectedly(Exception exception)
        {
            if (_terminalResponse == null)
            {
                return Finish(Failure(
                    $"Job coordinator threw {exception.GetType().Name}: {exception.Message}"));
            }
            return MaterializeTerminal();
        }

        private bool InitializeFactory()
        {
            _outcome = ExecuteScriptCommandHandler.ExecuteCode(_parameters);
            if (!_outcome.Success)
                return Finish(_outcome);
            if (CheckDeadline())
                return Finish(Failure("Job factory returned after the deadline."));
            if (!(_outcome.Value is IExecuteScriptJob job))
            {
                return Finish(Failure(
                    "Cooperative expression must return an IExecuteScriptJob instance."));
            }
            _controller = new ExecuteScriptJobController(
                job, _parameters.manifest.timeoutMs, () => _stopwatch.ElapsedMilliseconds);
            if (_cancellationRequested)
                _controller.RequestCancellation();
            return false;
        }

        private bool CheckDeadline()
        {
            return _stopwatch.ElapsedMilliseconds >= _parameters.manifest.timeoutMs;
        }

        private ExecuteScriptOutcome CompleteOutcome(ExecuteScriptJobStep step)
        {
            _outcome.Success = true;
            _outcome.Value = step.result;
            _outcome.ResultSet = step.resultSet;
            _outcome.Message = string.IsNullOrEmpty(step.message)
                ? "Cooperative job completed." : step.message;
            return _outcome;
        }

        private ExecuteScriptOutcome Failure(string message)
        {
            _outcome ??= new ExecuteScriptOutcome();
            _outcome.Success = false;
            _outcome.Value = null;
            _outcome.ResultSet = false;
            _outcome.Message = string.IsNullOrEmpty(message)
                ? "Cooperative job failed." : message;
            return _outcome;
        }

        private bool Finish(ExecuteScriptOutcome outcome)
        {
            if (_terminalResponse == null)
                _terminalResponse = BuildTerminal(outcome);
            return MaterializeTerminal();
        }

        private BridgeResponse BuildTerminal(ExecuteScriptOutcome outcome)
        {
            var value = ExecuteScriptCommandHandler.SerializeOutcome(
                outcome, _parameters.manifest.returnSchema);
            var wasSuccessful = outcome.Success;
            if (!_mutation.Complete(outcome.Success, out var governanceError))
            {
                outcome.Success = false;
                if (!string.IsNullOrEmpty(governanceError))
                {
                    outcome.Message = wasSuccessful || string.IsNullOrEmpty(outcome.Message)
                        ? governanceError : $"{outcome.Message} {governanceError}";
                }
            }
            _stopwatch.Stop();
            var result = ExecuteScriptCommandHandler.BuildResult(
                outcome, value, _logs.Entries, _mutation.Report, _stopwatch.ElapsedMilliseconds);
            FinalizeResources();
            return ExecuteScriptCommandHandler.BuildResponse(_command, result);
        }

        private bool MaterializeTerminal()
        {
            if (ExecuteScriptJobTerminalStore.TryCommitAndMaterialize(
                _terminalResponse, out _, out var message))
            {
                return true;
            }
            BridgeLogger.LogWarning(message);
            return false;
        }

        private void FinalizeResources()
        {
            if (_resourcesFinalized)
                return;
            _mutation.Dispose();
            _logs.Dispose();
            _resourcesFinalized = true;
        }
    }
}
