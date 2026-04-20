using System;
using System.Reflection;
using UnityEditor;
using UnityEngine;

namespace BWS.Editor.ClaudeCodeBridge
{
    /// <summary>
    /// Regenerates the Visual Studio / Rider / VS Code solution and project
    /// files for the current Unity project.
    ///
    /// AssetDatabase.Refresh() alone does not always trigger a .sln / .csproj
    /// resync — agents that rely on IDE-driven compilation or code analysis
    /// need an explicit sync after adding scripts or .asmdef changes.
    ///
    /// Tries two entry points in order:
    /// 1. com.unity.ide.visualstudio (modern CodeEditor API) via reflection
    ///    on Unity.CodeEditor.CodeEditor.CurrentEditor.SyncAll().
    /// 2. Legacy internal UnityEditor.SyncVS.SyncSolution() via reflection.
    ///
    /// COMMAND JSON:
    /// {
    ///   "commandId": "guid",
    ///   "commandType": "sync-solution",
    ///   "parametersJson": "{}"
    /// }
    /// </summary>
    public class SyncSolutionCommandHandler : ICommandHandler
    {
        public string CommandType => "sync-solution";

        public BridgeResponse Execute(BridgeCommand command)
        {
            try
            {
                var used = TrySyncViaCodeEditor() ?? TrySyncViaLegacy();

                if (used == null)
                {
                    return BridgeResponse.Error(
                        command.commandId,
                        command.commandType,
                        "Could not locate a SyncSolution entry point. " +
                        "Install com.unity.ide.visualstudio or com.unity.ide.rider.");
                }

                var result = new SyncSolutionResult
                {
                    success = true,
                    method = used,
                    message = $"Solution regenerated via {used}."
                };

                BridgeLogger.LogInfo(result.message);
                return BridgeResponse.Success(
                    command.commandId, command.commandType,
                    JsonUtility.ToJson(result));
            }
            catch (Exception ex)
            {
                BridgeLogger.LogError($"Sync solution error: {ex}");
                return BridgeResponse.Error(command.commandId, command.commandType, ex.ToString());
            }
        }

        private static string TrySyncViaCodeEditor()
        {
            var codeEditorType = Type.GetType("Unity.CodeEditor.CodeEditor, Unity.CodeEditor");
            if (codeEditorType == null) return null;

            var currentProp = codeEditorType.GetProperty(
                "CurrentEditor",
                BindingFlags.Public | BindingFlags.Static);
            if (currentProp == null) return null;

            var currentEditor = currentProp.GetValue(null);
            if (currentEditor == null) return null;

            var syncAll = currentEditor.GetType().GetMethod(
                "SyncAll",
                BindingFlags.Public | BindingFlags.Instance);
            if (syncAll == null) return null;

            syncAll.Invoke(currentEditor, null);
            return "CodeEditor.SyncAll";
        }

        private static string TrySyncViaLegacy()
        {
            var syncVs = typeof(UnityEditor.Editor).Assembly.GetType("UnityEditor.SyncVS");
            if (syncVs == null) return null;

            var method = syncVs.GetMethod(
                "SyncSolution",
                BindingFlags.Public | BindingFlags.Static);
            if (method == null) return null;

            method.Invoke(null, null);
            return "UnityEditor.SyncVS.SyncSolution";
        }
    }

    [Serializable]
    public class SyncSolutionResult
    {
        public bool success;
        public string method;
        public string message;
    }
}
