using System;

namespace BWS.Editor.ClaudeCodeBridge
{
    internal enum ExecuteScriptJobAdvanceKind
    {
        Continue,
        Completed,
        Failed,
        Cancelled,
        TimedOut,
        AlreadyTerminal,
    }

    internal sealed class ExecuteScriptJobAdvance
    {
        public ExecuteScriptJobAdvanceKind kind;
        public ExecuteScriptJobStep step;
        public string message = "";
        public bool stepOverran;
    }

    /// <summary>Pure cooperative state machine used by the Unity update coordinator.</summary>
    internal sealed class ExecuteScriptJobController
    {
        private readonly IExecuteScriptJob _job;
        private readonly long _timeoutMs;
        private readonly Func<long> _elapsedMilliseconds;
        private bool _cancellationRequested;
        private bool _terminal;

        public ExecuteScriptJobController(
            IExecuteScriptJob job,
            long timeoutMs,
            Func<long> elapsedMilliseconds)
        {
            _job = job ?? throw new ArgumentNullException(nameof(job));
            _timeoutMs = timeoutMs;
            _elapsedMilliseconds = elapsedMilliseconds
                ?? throw new ArgumentNullException(nameof(elapsedMilliseconds));
        }

        public void RequestCancellation()
        {
            _cancellationRequested = true;
        }

        public bool CheckDeadline()
        {
            return _elapsedMilliseconds() >= _timeoutMs;
        }

        public ExecuteScriptJobAdvance Advance()
        {
            if (_terminal)
                return NewAdvance(ExecuteScriptJobAdvanceKind.AlreadyTerminal);
            if (_cancellationRequested)
                return Stop(ExecuteScriptJobAdvanceKind.Cancelled, "Job cancellation requested.");
            if (CheckDeadline())
                return Stop(ExecuteScriptJobAdvanceKind.TimedOut, "Job deadline exceeded.");

            var step = InvokeStep();
            if (step.kind == ExecuteScriptJobAdvanceKind.Failed)
                return Finish(step);
            if (_cancellationRequested)
                return Stop(ExecuteScriptJobAdvanceKind.Cancelled, "Job cancellation requested.");
            if (CheckDeadline())
                return Stop(
                    ExecuteScriptJobAdvanceKind.TimedOut,
                    "Job step returned after the deadline.",
                    stepOverran: true);
            if (!step.step.completed)
                return step;
            step.kind = step.step.success
                ? ExecuteScriptJobAdvanceKind.Completed
                : ExecuteScriptJobAdvanceKind.Failed;
            return Finish(step);
        }

        private ExecuteScriptJobAdvance InvokeStep()
        {
            try
            {
                var step = _job.Step();
                if (step == null)
                    return NewAdvance(
                        ExecuteScriptJobAdvanceKind.Failed,
                        "Cooperative job returned a null step result.");
                return new ExecuteScriptJobAdvance
                {
                    kind = ExecuteScriptJobAdvanceKind.Continue,
                    step = step,
                    message = step.message ?? "",
                };
            }
            catch (Exception ex)
            {
                return NewAdvance(
                    ExecuteScriptJobAdvanceKind.Failed,
                    $"Cooperative job step threw {ex.GetType().Name}: {ex.Message}");
            }
        }

        private ExecuteScriptJobAdvance Stop(
            ExecuteScriptJobAdvanceKind kind,
            string message,
            bool stepOverran = false)
        {
            var cleanupError = InvokeCancel();
            var suffix = string.IsNullOrEmpty(cleanupError) ? "" : $" Cleanup failed: {cleanupError}";
            return Finish(new ExecuteScriptJobAdvance
            {
                kind = kind,
                message = message + suffix,
                stepOverran = stepOverran,
            });
        }

        private string InvokeCancel()
        {
            if (!(_job is ICancellableExecuteScriptJob cancellable))
                return "";
            try
            {
                cancellable.Cancel();
                return "";
            }
            catch (Exception ex)
            {
                return $"{ex.GetType().Name}: {ex.Message}";
            }
        }

        private ExecuteScriptJobAdvance Finish(ExecuteScriptJobAdvance advance)
        {
            _terminal = true;
            return advance;
        }

        private static ExecuteScriptJobAdvance NewAdvance(
            ExecuteScriptJobAdvanceKind kind,
            string message = "")
        {
            return new ExecuteScriptJobAdvance { kind = kind, message = message };
        }
    }
}
