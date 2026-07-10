using System;
using UnityEngine;

namespace BWS.Editor.ClaudeCodeBridge
{
    public sealed class CancelExecuteScriptJobCommandHandler : ICommandHandler
    {
        public string CommandType => "cancel-execute-job";

        public BridgeResponse Execute(BridgeCommand command)
        {
            var parameters = JsonUtility.FromJson<CancelExecuteScriptJobParams>(
                command.parametersJson ?? "{}") ?? new CancelExecuteScriptJobParams();
            if (string.IsNullOrWhiteSpace(parameters.targetCommandId))
                return BridgeResponse.Error(
                    command.commandId, command.commandType, "targetCommandId is required");
            if (!ExecuteScriptJobCoordinator.RequestCancellation(
                parameters.targetCommandId, out var message))
            {
                return BridgeResponse.Error(command.commandId, command.commandType, message);
            }
            var status = new CancelExecuteScriptJobResult
            {
                accepted = true,
                targetCommandId = parameters.targetCommandId,
                targetState = "cancellation-requested",
            };
            return BridgeResponse.Success(
                command.commandId, command.commandType, JsonUtility.ToJson(status));
        }
    }

    [Serializable]
    internal sealed class CancelExecuteScriptJobParams
    {
        public string targetCommandId;
    }

    [Serializable]
    internal sealed class CancelExecuteScriptJobResult
    {
        public bool accepted;
        public string targetCommandId;
        public string targetState;
    }
}
