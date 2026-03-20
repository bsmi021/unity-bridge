using System;
using System.Collections.Generic;
using System.Linq;
using UnityEditor;
using UnityEngine;

namespace BWS.Editor.ClaudeCodeBridge
{
    /// <summary>
    /// Command handler for Unity Editor undo/redo operations.
    ///
    /// PURPOSE:
    /// Provides Claude Code with the ability to manage the Unity Editor undo stack,
    /// enabling safe, reversible automated modifications to scenes and assets.
    ///
    /// SUPPORTED OPERATIONS:
    /// 1. "perform" - Undo the last operation
    /// 2. "redo" - Redo the last undone operation
    /// 3. "history" - List recent undo operations (bridge-tracked only)
    /// 4. "clear" - Clear all undo history (WARNING: affects entire Editor)
    /// 5. "group-name" - Get the current undo group name
    /// 6. "collapse" - Collapse operations from a group index into one undo step
    ///
    /// LIMITATIONS:
    /// - Full undo history enumeration is not supported by Unity's public API
    /// - Only operations tracked since bridge initialization are available in history
    /// - Undo/redo operations are not supported during play mode
    /// </summary>
    public class UndoCommandHandler : ICommandHandler
    {
        public string CommandType => "undo-operation";

        private static readonly List<UndoGroupInfo> _recentOperations = new List<UndoGroupInfo>();
        private static bool _trackingInitialized = false;

        [InitializeOnLoadMethod]
        private static void InitUndoTracking()
        {
            if (_trackingInitialized) return;
            _trackingInitialized = true;

            Undo.undoRedoPerformed += () =>
            {
                var name = Undo.GetCurrentGroupName();
                if (_recentOperations.Count >= 100)
                    _recentOperations.RemoveAt(0);
                _recentOperations.Add(new UndoGroupInfo
                {
                    name = name,
                    id = Undo.GetCurrentGroup()
                });
            };
        }

        public BridgeResponse Execute(BridgeCommand command)
        {
            try
            {
                var parameters = JsonUtility.FromJson<UndoOperationParams>(
                    command.parametersJson ?? "{}");
                if (parameters == null)
                    parameters = new UndoOperationParams();

                var operation = parameters.operation?.ToLower();
                BridgeLogger.LogDebug($"Executing undo operation: {operation}");

                // Guard: no undo operations during compilation
                if (EditorApplication.isCompiling)
                {
                    return BridgeResponse.Error(command.commandId, command.commandType,
                        "Cannot perform undo operations while scripts are compiling.");
                }

                // Guard: mutating undo operations cannot run during play mode
                if (EditorApplication.isPlaying &&
                    operation is "perform" or "redo" or "clear" or "collapse")
                {
                    return BridgeResponse.Error(command.commandId, command.commandType,
                        "Undo operations are not supported during play mode.");
                }

                // Guard: prevent re-entrant undo operations
                if (Undo.isProcessing &&
                    operation is "perform" or "redo")
                {
                    return BridgeResponse.Error(command.commandId, command.commandType,
                        "Undo operation already in progress.");
                }

                switch (operation)
                {
                    case "perform":
                        return PerformUndo(command);
                    case "redo":
                        return PerformRedo(command);
                    case "history":
                        return GetHistory(command, parameters.limit);
                    case "clear":
                        return ClearHistory(command);
                    case "group-name":
                        return GetGroupName(command);
                    case "collapse":
                        return CollapseOperations(command, parameters.groupIndex, parameters.name);
                    default:
                        return BridgeResponse.Error(command.commandId, command.commandType,
                            $"Unknown undo operation: {parameters.operation}. " +
                            "Supported: perform, redo, history, clear, group-name, collapse");
                }
            }
            catch (Exception ex)
            {
                BridgeLogger.LogError($"Undo operation error: {ex}");
                return BridgeResponse.Error(command.commandId, command.commandType, ex.ToString());
            }
        }

        private BridgeResponse PerformUndo(BridgeCommand command)
        {
            var groupName = Undo.GetCurrentGroupName();
            Undo.PerformUndo();
            var result = new UndoOperationResult
            {
                success = true,
                undone = true,
                groupName = groupName
            };
            return BridgeResponse.Success(command.commandId, command.commandType,
                JsonUtility.ToJson(result));
        }

        private BridgeResponse PerformRedo(BridgeCommand command)
        {
            Undo.PerformRedo();
            var groupName = Undo.GetCurrentGroupName();
            var result = new UndoOperationResult
            {
                success = true,
                redone = true,
                groupName = groupName
            };
            return BridgeResponse.Success(command.commandId, command.commandType,
                JsonUtility.ToJson(result));
        }

        private BridgeResponse GetHistory(BridgeCommand command, int limit)
        {
            var currentName = Undo.GetCurrentGroupName();
            var count = Math.Min(limit, _recentOperations.Count);
            var recent = _recentOperations
                .Skip(Math.Max(0, _recentOperations.Count - count))
                .ToList();

            var result = new UndoOperationResult
            {
                success = true,
                currentGroupName = currentName,
                recentOperations = recent,
                count = recent.Count,
                note = "Only includes operations tracked since bridge initialization. " +
                       "Full undo history enumeration is not supported by Unity's public API."
            };
            return BridgeResponse.Success(command.commandId, command.commandType,
                JsonUtility.ToJson(result));
        }

        private BridgeResponse ClearHistory(BridgeCommand command)
        {
            Undo.ClearAll();
            _recentOperations.Clear();

            var result = new UndoOperationResult
            {
                success = true,
                cleared = true,
                warning = "All undo history has been cleared, including non-bridge operations."
            };
            return BridgeResponse.Success(command.commandId, command.commandType,
                JsonUtility.ToJson(result));
        }

        private BridgeResponse GetGroupName(BridgeCommand command)
        {
            var groupName = Undo.GetCurrentGroupName();
            var result = new UndoOperationResult
            {
                success = true,
                groupName = groupName
            };
            return BridgeResponse.Success(command.commandId, command.commandType,
                JsonUtility.ToJson(result));
        }

        private BridgeResponse CollapseOperations(BridgeCommand command, int groupIndex, string name)
        {
            if (groupIndex < 0)
            {
                return BridgeResponse.Error(command.commandId, command.commandType,
                    $"Invalid groupIndex: {groupIndex}. Must be non-negative.");
            }

            if (!string.IsNullOrEmpty(name))
                Undo.SetCurrentGroupName(name);

            Undo.CollapseUndoOperations(groupIndex);

            var result = new UndoOperationResult
            {
                success = true,
                collapsed = true,
                groupIndex = groupIndex,
                name = name ?? Undo.GetCurrentGroupName()
            };
            return BridgeResponse.Success(command.commandId, command.commandType,
                JsonUtility.ToJson(result));
        }
    }
}
