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

        // Lock depth must survive domain reloads (a lock taken before a reload is
        // still in effect after it), so it is stored in SessionState rather than
        // a plain static that the reload would reset.
        private const string LockDepthKey = "UnityBridge.AssemblyReloadLock.Depth";

        private static int LockDepth
        {
            get => SessionState.GetInt(LockDepthKey, 0);
            set => SessionState.SetInt(LockDepthKey, value);
        }

        private static bool IsLocked => LockDepth > 0;

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
            LockDepth++;

            var result = new AssemblyReloadLockResult
            {
                operation = "lock",
                isLocked = true,
                lockDepth = LockDepth,
                success = true,
                message = $"Assembly reloading locked (depth: {LockDepth}). " +
                    "Remember to unlock when done."
            };

            BridgeLogger.LogInfo(result.message);
            return BridgeResponse.Success(
                command.commandId, command.commandType,
                JsonUtility.ToJson(result));
        }

        private BridgeResponse HandleUnlock(BridgeCommand command)
        {
            if (LockDepth <= 0)
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
            LockDepth--;

            var result = new AssemblyReloadLockResult
            {
                operation = "unlock",
                isLocked = IsLocked,
                lockDepth = LockDepth,
                success = true,
                message = IsLocked
                    ? $"Assembly reload unlocked one level (remaining depth: {LockDepth})"
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
                isLocked = IsLocked,
                lockDepth = LockDepth,
                success = true,
                message = IsLocked
                    ? $"Assembly reloading is locked (depth: {LockDepth})"
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
