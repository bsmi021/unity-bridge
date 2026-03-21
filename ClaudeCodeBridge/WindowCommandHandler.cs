using System;
using System.Collections.Generic;
using System.Linq;
using UnityEditor;
using UnityEngine;

namespace BWS.Editor.ClaudeCodeBridge
{
    /// <summary>
    /// Command handler for Unity Editor window management.
    ///
    /// SUPPORTED OPERATIONS:
    /// 1. "list" - List all open editor windows
    /// 2. "open" - Open a known editor window by name
    /// 3. "focus" - Focus an existing window
    /// 4. "close" - Close an editor window
    /// </summary>
    public class WindowCommandHandler : ICommandHandler
    {
        public string CommandType => "window-management";

        private static readonly Dictionary<string, Type> KNOWN_WINDOWS =
            BuildKnownWindowTypes();

        public BridgeResponse Execute(BridgeCommand command)
        {
            try
            {
                var parameters = JsonUtility.FromJson<WindowManagementParams>(
                    command.parametersJson ?? "{}");
                if (parameters == null)
                    parameters = new WindowManagementParams();

                var operation = parameters.operation?.ToLower();
                BridgeLogger.LogDebug($"Executing window-management: {operation}");

                switch (operation)
                {
                    case "list":
                        return HandleList(command);
                    case "open":
                        return HandleOpen(command, parameters);
                    case "focus":
                        return HandleFocus(command, parameters);
                    case "close":
                        return HandleClose(command, parameters);
                    default:
                        return BridgeResponse.Error(command.commandId, command.commandType,
                            $"Unknown operation: {parameters.operation}. " +
                            "Supported: list, open, focus, close");
                }
            }
            catch (Exception ex)
            {
                BridgeLogger.LogError($"Window management error: {ex}");
                return BridgeResponse.Error(command.commandId, command.commandType, ex.ToString());
            }
        }

        private BridgeResponse HandleList(BridgeCommand command)
        {
            var windows = Resources.FindObjectsOfTypeAll<EditorWindow>();
            var infos = new List<WindowInfo>();

            foreach (var w in windows)
            {
                if (w == null) continue;
                infos.Add(new WindowInfo
                {
                    title = w.titleContent?.text ?? "",
                    typeName = w.GetType().Name,
                    fullTypeName = w.GetType().FullName,
                    isFocused = w.hasFocus,
                });
            }

            var result = new WindowManagementResult
            {
                success = true,
                operation = "list",
                windows = infos,
                message = $"Found {infos.Count} open windows",
            };
            return BridgeResponse.Success(command.commandId, command.commandType,
                JsonUtility.ToJson(result));
        }

        private BridgeResponse HandleOpen(
            BridgeCommand command, WindowManagementParams parameters)
        {
            if (string.IsNullOrEmpty(parameters.windowName))
            {
                return BridgeResponse.Error(command.commandId, command.commandType,
                    "windowName is required for open operation. Known windows: " +
                    string.Join(", ", KNOWN_WINDOWS.Keys));
            }

            var windowType = ResolveWindowType(parameters.windowName);
            if (windowType == null)
            {
                return BridgeResponse.Error(command.commandId, command.commandType,
                    $"Unknown window: {parameters.windowName}. Known windows: " +
                    string.Join(", ", KNOWN_WINDOWS.Keys));
            }

            var window = EditorWindow.GetWindow(windowType);
            window.Show();
            window.Focus();

            var result = new WindowManagementResult
            {
                success = true,
                operation = "open",
                windowName = window.titleContent?.text ?? parameters.windowName,
                windowType = windowType.FullName,
                message = $"Opened window: {parameters.windowName}",
            };
            return BridgeResponse.Success(command.commandId, command.commandType,
                JsonUtility.ToJson(result));
        }

        private BridgeResponse HandleFocus(
            BridgeCommand command, WindowManagementParams parameters)
        {
            if (string.IsNullOrEmpty(parameters.windowName))
            {
                return BridgeResponse.Error(command.commandId, command.commandType,
                    "windowName is required for focus operation.");
            }

            var windowType = ResolveWindowType(parameters.windowName);
            if (windowType == null)
            {
                return BridgeResponse.Error(command.commandId, command.commandType,
                    $"Unknown window: {parameters.windowName}");
            }

            var existing = Resources.FindObjectsOfTypeAll(windowType);
            if (existing.Length == 0)
            {
                return BridgeResponse.Error(command.commandId, command.commandType,
                    $"Window not open: {parameters.windowName}");
            }

            var window = existing[0] as EditorWindow;
            if (window is not null)
            {
                window.Focus();
            }

            var result = new WindowManagementResult
            {
                success = true,
                operation = "focus",
                windowName = parameters.windowName,
                windowType = windowType.FullName,
                message = $"Focused window: {parameters.windowName}",
            };
            return BridgeResponse.Success(command.commandId, command.commandType,
                JsonUtility.ToJson(result));
        }

        private BridgeResponse HandleClose(
            BridgeCommand command, WindowManagementParams parameters)
        {
            if (string.IsNullOrEmpty(parameters.windowName))
            {
                return BridgeResponse.Error(command.commandId, command.commandType,
                    "windowName is required for close operation.");
            }

            var windowType = ResolveWindowType(parameters.windowName);
            if (windowType == null)
            {
                return BridgeResponse.Error(command.commandId, command.commandType,
                    $"Unknown window: {parameters.windowName}");
            }

            var existing = Resources.FindObjectsOfTypeAll(windowType);
            int closed = 0;
            foreach (var obj in existing)
            {
                var window = obj as EditorWindow;
                if (window is not null)
                {
                    window.Close();
                    closed++;
                }
            }

            var result = new WindowManagementResult
            {
                success = true,
                operation = "close",
                windowName = parameters.windowName,
                closedCount = closed,
                message = closed > 0
                    ? $"Closed {closed} window(s): {parameters.windowName}"
                    : $"No open windows found: {parameters.windowName}",
            };
            return BridgeResponse.Success(command.commandId, command.commandType,
                JsonUtility.ToJson(result));
        }

        private static Type ResolveWindowType(string name)
        {
            var lower = name.ToLower()
                .Replace(" ", "").Replace("-", "").Replace("_", "");

            foreach (var kvp in KNOWN_WINDOWS)
            {
                if (kvp.Key.ToLower().Replace(" ", "").Replace("-", "")
                    .Replace("_", "") == lower)
                    return kvp.Value;
            }
            return null;
        }

        private static Dictionary<string, Type> BuildKnownWindowTypes()
        {
            var map = new Dictionary<string, Type>(StringComparer.OrdinalIgnoreCase);

            // Standard Editor windows
            AddType(map, "Scene", "UnityEditor.SceneView");
            AddType(map, "Game", "UnityEditor.GameView");
            AddType(map, "Inspector", "UnityEditor.InspectorWindow");
            AddType(map, "Console", "UnityEditor.ConsoleWindow");
            AddType(map, "Project", "UnityEditor.ProjectBrowser");
            AddType(map, "Hierarchy", "UnityEditor.SceneHierarchyWindow");
            AddType(map, "Animation", "UnityEditor.AnimationWindow");
            AddType(map, "Animator", "UnityEditor.Graphs.AnimatorControllerTool");
            AddType(map, "Profiler", "UnityEditor.ProfilerWindow");
            AddType(map, "AssetStore", "UnityEditor.AssetStoreWindow");
            AddType(map, "PackageManager", "UnityEditor.PackageManager.UI.PackageManagerWindow");
            AddType(map, "Lighting", "UnityEditor.LightingWindow");

            return map;
        }

        private static void AddType(Dictionary<string, Type> map, string key, string fullName)
        {
            foreach (var asm in AppDomain.CurrentDomain.GetAssemblies())
            {
                var type = asm.GetType(fullName);
                if (type is not null)
                {
                    map[key] = type;
                    return;
                }
            }
        }
    }

    #region Window Management Models

    [Serializable]
    public class WindowManagementParams
    {
        public string operation;
        public string windowName;
    }

    [Serializable]
    public class WindowManagementResult
    {
        public bool success;
        public string operation;
        public string windowName;
        public string windowType;
        public int closedCount;
        public List<WindowInfo> windows = new List<WindowInfo>();
        public string message;
    }

    [Serializable]
    public class WindowInfo
    {
        public string title;
        public string typeName;
        public string fullTypeName;
        public bool isFocused;
    }

    #endregion
}
