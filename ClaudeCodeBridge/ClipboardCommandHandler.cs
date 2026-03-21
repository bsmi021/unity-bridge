using System;
using UnityEditor;
using UnityEngine;

namespace BWS.Editor.ClaudeCodeBridge
{
    /// <summary>
    /// Command handler for system clipboard access via EditorGUIUtility.systemCopyBuffer.
    ///
    /// SUPPORTED OPERATIONS:
    /// 1. "read" - Read current clipboard text
    /// 2. "write" - Write text to the clipboard
    /// </summary>
    public class ClipboardCommandHandler : ICommandHandler
    {
        public string CommandType => "clipboard";

        public BridgeResponse Execute(BridgeCommand command)
        {
            try
            {
                var parameters = JsonUtility.FromJson<ClipboardParams>(
                    command.parametersJson ?? "{}");
                if (parameters == null)
                    parameters = new ClipboardParams();

                var operation = parameters.operation?.ToLower();
                BridgeLogger.LogDebug($"Executing clipboard: {operation}");

                switch (operation)
                {
                    case "read":
                        return HandleRead(command);
                    case "write":
                        return HandleWrite(command, parameters);
                    default:
                        return BridgeResponse.Error(command.commandId, command.commandType,
                            $"Unknown operation: {parameters.operation}. Supported: read, write");
                }
            }
            catch (Exception ex)
            {
                BridgeLogger.LogError($"Clipboard error: {ex}");
                return BridgeResponse.Error(command.commandId, command.commandType, ex.ToString());
            }
        }

        private BridgeResponse HandleRead(BridgeCommand command)
        {
            var text = EditorGUIUtility.systemCopyBuffer ?? "";
            var result = new ClipboardResult
            {
                success = true,
                operation = "read",
                text = text,
                length = text.Length,
            };
            BridgeLogger.LogInfo($"Clipboard read: {text.Length} chars");
            return BridgeResponse.Success(command.commandId, command.commandType,
                JsonUtility.ToJson(result));
        }

        private BridgeResponse HandleWrite(BridgeCommand command, ClipboardParams parameters)
        {
            if (parameters.text == null)
            {
                return BridgeResponse.Error(command.commandId, command.commandType,
                    "text is required for write operation.");
            }

            EditorGUIUtility.systemCopyBuffer = parameters.text;
            var result = new ClipboardResult
            {
                success = true,
                operation = "write",
                text = parameters.text,
                length = parameters.text.Length,
            };
            BridgeLogger.LogInfo($"Clipboard write: {parameters.text.Length} chars");
            return BridgeResponse.Success(command.commandId, command.commandType,
                JsonUtility.ToJson(result));
        }
    }

    #region Clipboard Models

    [Serializable]
    public class ClipboardParams
    {
        public string operation;
        public string text;
    }

    [Serializable]
    public class ClipboardResult
    {
        public bool success;
        public string operation;
        public string text;
        public int length;
    }

    #endregion
}
