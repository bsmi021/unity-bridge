using System;
using UnityEngine;

namespace BWS.Editor.ClaudeCodeBridge
{
    /// <summary>
    /// Command handler for canceling an active bridge-initiated Unity test run.
    /// </summary>
    public class CancelTestsCommandHandler : ICommandHandler
    {
        public string CommandType => "cancel-tests";

        public BridgeResponse Execute(BridgeCommand command)
        {
            try
            {
                var parameters = JsonUtility.FromJson<CancelTestsParams>(
                    command.parametersJson ?? "{}");
                if (parameters == null)
                    parameters = new CancelTestsParams();

                var result = BridgeTestRunReporter.CancelRun(parameters.targetCommandId);
                return BridgeResponse.Success(
                    command.commandId,
                    command.commandType,
                    JsonUtility.ToJson(result));
            }
            catch (Exception ex)
            {
                BridgeLogger.LogError($"Error canceling tests: {ex}");
                return BridgeResponse.Error(command.commandId, command.commandType, ex.ToString());
            }
        }
    }
}
