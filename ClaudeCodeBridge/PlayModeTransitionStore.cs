using System;
using UnityEditor;

namespace BWS.Editor.ClaudeCodeBridge
{
    internal sealed class PersistedPlayModeTransition
    {
        public string CommandId;
        public string Operation;
        public PlayModeStateChange TargetState;
    }

    internal static class PlayModeTransitionStore
    {
        internal const string PendingCommandIdKey = "UnityBridge.PlayMode.CommandId";
        private const string PendingOperationKey = "UnityBridge.PlayMode.Operation";
        private const string PendingTargetStateKey = "UnityBridge.PlayMode.TargetState";

        public static void Persist(
            string commandId,
            string operation,
            PlayModeStateChange targetState)
        {
            SessionState.SetString(PendingCommandIdKey, commandId ?? "");
            SessionState.SetString(PendingOperationKey, operation ?? "");
            SessionState.SetString(PendingTargetStateKey, targetState.ToString());
        }

        public static PersistedPlayModeTransition Restore()
        {
            var commandId = SessionState.GetString(PendingCommandIdKey, "");
            var target = SessionState.GetString(PendingTargetStateKey, "");
            if (string.IsNullOrEmpty(commandId)
                || !Enum.TryParse(target, out PlayModeStateChange targetState))
            {
                return null;
            }
            return new PersistedPlayModeTransition
            {
                CommandId = commandId,
                Operation = SessionState.GetString(PendingOperationKey, ""),
                TargetState = targetState,
            };
        }

        public static void Clear(string commandId)
        {
            if (SessionState.GetString(PendingCommandIdKey, "") != commandId)
                return;
            SessionState.EraseString(PendingCommandIdKey);
            SessionState.EraseString(PendingOperationKey);
            SessionState.EraseString(PendingTargetStateKey);
        }

        public static bool IsSatisfied(PlayModeStateChange targetState)
        {
            return targetState == PlayModeStateChange.EnteredPlayMode
                ? EditorApplication.isPlaying
                : targetState == PlayModeStateChange.EnteredEditMode
                    && !EditorApplication.isPlaying
                    && !EditorApplication.isPlayingOrWillChangePlaymode;
        }
    }
}
