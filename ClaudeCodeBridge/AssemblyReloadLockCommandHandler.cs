using System;
using UnityEditor;
using UnityEngine;

namespace BWS.Editor.ClaudeCodeBridge
{
    /// <summary>
    /// Command handler for locking and unlocking assembly reload.
    ///
    /// PURPOSE:
    /// Prevents domain reloads during batch operations by calling
    /// EditorApplication.LockReloadAssemblies() / UnlockReloadAssemblies().
    /// Lock before making multiple script changes, unlock when done.
    ///
    /// SUPPORTED OPERATIONS:
    /// 1. "lock" - Lock assembly reloading
    /// 2. "unlock" - Unlock assembly reloading
    /// 3. "status" - Check if reloading is currently locked
    ///
    /// COMMAND JSON:
    /// {
    ///   "commandId": "guid",
    ///   "commandType": "assembly-reload-lock",
    ///   "parametersJson": "{\"operation\":\"lock\"}"
    /// }
    /// </summary>
    public class AssemblyReloadLockCommandHandler : ICommandHandler
    {
        public string CommandType => "assembly-reload-lock";

        private static bool _isLocked = false;
        private static int _lockDepth = 0;

        public BridgeResponse Execute(BridgeCommand command)
        {
            try
            {
                var parameters = JsonUtility.FromJson<AssemblyReloadLockParams>(
                    command.parametersJson ?? "{}");
                if (parameters == null)
                    parameters = new AssemblyReloadLockParams();

                var operation = parameters.operation?.ToLower();
                BridgeLogger.LogDebug($"Assembly reload lock operation: {operation}");

                switch (operation)
                {
                    case "lock":
                        return HandleLock(command);
                    case "unlock":
                        return HandleUnlock(command);
                    case "status":
                        return HandleStatus(command);
                    default:
                        return BridgeResponse.Error(command.commandId, command.commandType,
                            $"Unknown operation: {parameters.operation}. Supported: lock, unlock, status");
                }
            }
            catch (Exception ex)
            {
                BridgeLogger.LogError($"Assembly reload lock error: {ex}");
                return BridgeResponse.Error(command.commandId, command.commandType, ex.ToString());
            }
        }

        private BridgeResponse HandleLock(BridgeCommand command)
        {
            EditorApplication.LockReloadAssemblies();
            _isLocked = true;
            _lockDepth++;

            var result = new AssemblyReloadLockResult
            {
                operation = "lock",
                isLocked = true,
                lockDepth = _lockDepth,
                success = true,
                message = $"Assembly reloading locked (depth: {_lockDepth}). " +
                    "Remember to unlock when done."
            };

            BridgeLogger.LogInfo(result.message);
            return BridgeResponse.Success(
                command.commandId, command.commandType,
                JsonUtility.ToJson(result));
        }

        private BridgeResponse HandleUnlock(BridgeCommand command)
        {
            if (_lockDepth <= 0)
            {
                var noLockResult = new AssemblyReloadLockResult
                {
                    operation = "unlock",
                    isLocked = false,
                    lockDepth = 0,
                    success = true,
                    message = "Assembly reloading was not locked."
                };
                return BridgeResponse.Success(
                    command.commandId, command.commandType,
                    JsonUtility.ToJson(noLockResult));
            }

            EditorApplication.UnlockReloadAssemblies();
            _lockDepth--;
            _isLocked = _lockDepth > 0;

            var result = new AssemblyReloadLockResult
            {
                operation = "unlock",
                isLocked = _isLocked,
                lockDepth = _lockDepth,
                success = true,
                message = _isLocked
                    ? $"Assembly reload unlocked one level (remaining depth: {_lockDepth})"
                    : "Assembly reloading fully unlocked."
            };

            BridgeLogger.LogInfo(result.message);
            return BridgeResponse.Success(
                command.commandId, command.commandType,
                JsonUtility.ToJson(result));
        }

        private BridgeResponse HandleStatus(BridgeCommand command)
        {
            var result = new AssemblyReloadLockResult
            {
                operation = "status",
                isLocked = _isLocked,
                lockDepth = _lockDepth,
                success = true,
                message = _isLocked
                    ? $"Assembly reloading is locked (depth: {_lockDepth})"
                    : "Assembly reloading is unlocked."
            };

            BridgeLogger.LogInfo(result.message);
            return BridgeResponse.Success(
                command.commandId, command.commandType,
                JsonUtility.ToJson(result));
        }
    }

    #region Assembly Reload Lock Models

    [Serializable]
    public class AssemblyReloadLockParams
    {
        public string operation; // "lock", "unlock", "status"
    }

    [Serializable]
    public class AssemblyReloadLockResult
    {
        public string operation;
        public bool isLocked;
        public int lockDepth;
        public bool success;
        public string message;
    }

    #endregion
}
