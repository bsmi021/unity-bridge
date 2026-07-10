using System;

namespace BWS.Editor.ClaudeCodeBridge
{
    /// <summary>
    /// A cooperative editor job. Unity invokes one step per Editor update.
    /// A step must return promptly; the bridge cannot preempt code inside Step.
    /// </summary>
    public interface IExecuteScriptJob
    {
        ExecuteScriptJobStep Step();
    }

    /// <summary>Optional cancellation callback invoked between cooperative steps.</summary>
    public interface ICancellableExecuteScriptJob : IExecuteScriptJob
    {
        void Cancel();
    }

    /// <summary>Result of one cooperative job step.</summary>
    public sealed class ExecuteScriptJobStep
    {
        public bool completed;
        public bool success = true;
        public bool resultSet;
        public object result;
        public string message = "";

        public static ExecuteScriptJobStep Continue(string message = "")
        {
            return new ExecuteScriptJobStep { message = message ?? "" };
        }

        public static ExecuteScriptJobStep Complete(object result = null, string message = "")
        {
            return new ExecuteScriptJobStep
            {
                completed = true,
                resultSet = result != null,
                result = result,
                message = message ?? "",
            };
        }

        public static ExecuteScriptJobStep Fail(string message)
        {
            return new ExecuteScriptJobStep
            {
                completed = true,
                success = false,
                message = message ?? "Cooperative job failed.",
            };
        }
    }

    /// <summary>Convenience job backed by step and optional cancellation delegates.</summary>
    public sealed class DelegateExecuteScriptJob : ICancellableExecuteScriptJob
    {
        private readonly Func<ExecuteScriptJobStep> _step;
        private readonly Func<int, ExecuteScriptJobStep> _indexedStep;
        private readonly Action _cancel;
        private int _stepIndex;

        public DelegateExecuteScriptJob(
            Func<ExecuteScriptJobStep> step,
            Action cancel = null)
        {
            _step = step ?? throw new ArgumentNullException(nameof(step));
            _cancel = cancel;
        }

        public DelegateExecuteScriptJob(
            Func<int, ExecuteScriptJobStep> indexedStep,
            Action cancel = null)
        {
            _indexedStep = indexedStep ?? throw new ArgumentNullException(nameof(indexedStep));
            _cancel = cancel;
        }

        public ExecuteScriptJobStep Step()
        {
            return _indexedStep != null ? _indexedStep(_stepIndex++) : _step();
        }

        public void Cancel()
        {
            _cancel?.Invoke();
        }
    }
}
