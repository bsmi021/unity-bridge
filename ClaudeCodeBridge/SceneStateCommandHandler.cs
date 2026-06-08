using System;
using System.Collections;
using System.Collections.Generic;
using System.Reflection;
using UnityEditor;
using UnityEngine;

namespace BWS.Editor.ClaudeCodeBridge
{
    public class SceneStateCommandHandler : ICommandHandler
    {
        public string CommandType => "scene-state";

        public BridgeResponse Execute(BridgeCommand command)
        {
            try
            {
                var p = JsonUtility.FromJson<SceneStateParams>(
                    command.parametersJson ?? "{}") ?? new SceneStateParams();
                var operation = string.IsNullOrEmpty(p.operation)
                    ? "get"
                    : p.operation.ToLowerInvariant();

                switch (operation)
                {
                    case "get":
                        return Success(command, Snapshot("get"));
                    case "set":
                        return Success(command, SetState(command, p));
                    case "reset-snap":
                        EditorSnapSettings.ResetSnapSettings();
                        return Success(command, Snapshot("reset-snap", "Snap settings reset."));
                    case "list-overlays":
                        return Success(command, Snapshot("list-overlays"));
                    default:
                        return Error(command, operation,
                            "Unknown operation. Supported: get, set, reset-snap, list-overlays");
                }
            }
            catch (Exception ex)
            {
                BridgeLogger.LogError($"Scene state error: {ex}");
                return Error(command, "scene-state", ex.ToString());
            }
        }

        private static SceneStateResult SetState(BridgeCommand command, SceneStateParams p)
        {
            ApplySnapFields(command, p);
            ApplyToolFields(command, p);
            ApplyAnnotationFields(command, p);
            ApplySceneViewFields(command, p);
            return Snapshot("set", "Scene/editor state updated.");
        }

        private static void ApplySnapFields(BridgeCommand command, SceneStateParams p)
        {
            if (Has(command, "gridSnapEnabled"))
                EditorSnapSettings.gridSnapEnabled = p.gridSnapEnabled;
            if (Has(command, "snapEnabled"))
                EditorSnapSettings.snapEnabled = p.snapEnabled;
            if (Has(command, "angleSnapEnabled"))
                EditorSnapSettings.angleSnapEnabled = p.angleSnapEnabled;
            if (Has(command, "scaleSnapEnabled"))
                EditorSnapSettings.scaleSnapEnabled = p.scaleSnapEnabled;
            if (Has(command, "gridSize"))
                EditorSnapSettings.gridSize = ToVector3(p.gridSize);
            if (Has(command, "gridPosition"))
                EditorSnapSettings.gridPosition = ToVector3(p.gridPosition);
            if (Has(command, "moveSnap"))
                EditorSnapSettings.move = ToVector3(p.moveSnap);
            if (Has(command, "rotateSnap"))
                EditorSnapSettings.rotate = p.rotateSnap;
            if (Has(command, "scaleSnap"))
                EditorSnapSettings.scale = p.scaleSnap;
        }

        private static void ApplyToolFields(BridgeCommand command, SceneStateParams p)
        {
            if (Has(command, "activeTool") && Enum.TryParse(p.activeTool, true, out Tool tool))
                Tools.current = tool;
            if (Has(command, "pivotMode") && Enum.TryParse(p.pivotMode, true, out PivotMode pivot))
                Tools.pivotMode = pivot;
            if (Has(command, "pivotRotation")
                && Enum.TryParse(p.pivotRotation, true, out PivotRotation rotation))
                Tools.pivotRotation = rotation;
            if (Has(command, "toolsHidden"))
                Tools.hidden = p.toolsHidden;
            if (Has(command, "visibleLayers"))
                Tools.visibleLayers = p.visibleLayers;
            if (Has(command, "lockedLayers"))
                Tools.lockedLayers = p.lockedLayers;
        }

        private static void ApplyAnnotationFields(BridgeCommand command, SceneStateParams p)
        {
            if (Has(command, "use3dGizmos"))
                SetStatic("UnityEditor.AnnotationUtility", "use3dGizmos", p.use3dGizmos);
            if (Has(command, "showSelectionOutline"))
                SetStatic("UnityEditor.AnnotationUtility", "showSelectionOutline",
                    p.showSelectionOutline);
            if (Has(command, "showSelectionWire"))
                SetStatic("UnityEditor.AnnotationUtility", "showSelectionWire",
                    p.showSelectionWire);
        }

        private static void ApplySceneViewFields(BridgeCommand command, SceneStateParams p)
        {
            var sv = SceneView.lastActiveSceneView;
            if (sv == null) return;
            if (Has(command, "showGrid"))
                sv.showGrid = p.showGrid;
            if (Has(command, "drawGizmos"))
                sv.drawGizmos = p.drawGizmos;
            if (Has(command, "overlaysEnabled"))
                SetProperty(GetOverlayCanvas(sv), "overlaysEnabled", p.overlaysEnabled);
            sv.Repaint();
        }

        private static SceneStateResult Snapshot(string operation, string message = "")
        {
            var result = new SceneStateResult
            {
                success = true,
                operation = operation,
                snap = BuildSnap(),
                tools = BuildTools(),
                annotations = BuildAnnotations(),
                sceneView = BuildSceneView(),
                overlays = BuildOverlays()
            };
            result.message = string.IsNullOrEmpty(message) ? DefaultMessage(result) : message;
            return result;
        }

        private static string DefaultMessage(SceneStateResult result)
        {
            return result.sceneView.exists
                ? "Scene/editor state retrieved."
                : "Scene/editor state retrieved; no active Scene View was found.";
        }

        private static SceneStateSnapInfo BuildSnap()
        {
            return new SceneStateSnapInfo
            {
                gridSnapEnabled = EditorSnapSettings.gridSnapEnabled,
                snapEnabled = EditorSnapSettings.snapEnabled,
                angleSnapEnabled = EditorSnapSettings.angleSnapEnabled,
                scaleSnapEnabled = EditorSnapSettings.scaleSnapEnabled,
                gridSnapActive = EditorSnapSettings.gridSnapActive,
                incrementalSnapActive = EditorSnapSettings.incrementalSnapActive,
                gridSize = FromVector3(EditorSnapSettings.gridSize),
                gridPosition = FromVector3(EditorSnapSettings.gridPosition),
                moveSnap = FromVector3(EditorSnapSettings.move),
                rotateSnap = EditorSnapSettings.rotate,
                scaleSnap = EditorSnapSettings.scale
            };
        }

        private static SceneStateToolsInfo BuildTools()
        {
            return new SceneStateToolsInfo
            {
                activeTool = Tools.current.ToString(),
                pivotMode = Tools.pivotMode.ToString(),
                pivotRotation = Tools.pivotRotation.ToString(),
                toolsHidden = Tools.hidden,
                visibleLayers = Tools.visibleLayers,
                lockedLayers = Tools.lockedLayers
            };
        }

        private static SceneStateSceneViewInfo BuildSceneView()
        {
            var sv = SceneView.lastActiveSceneView;
            if (sv == null) return new SceneStateSceneViewInfo();
            return new SceneStateSceneViewInfo
            {
                exists = true,
                showGrid = sv.showGrid,
                drawGizmos = sv.drawGizmos,
                sceneLighting = sv.sceneLighting,
                in2DMode = sv.in2DMode,
                orthographic = sv.orthographic,
                cameraMode = sv.cameraMode.drawMode.ToString()
            };
        }

        private static SceneStateAnnotationInfo BuildAnnotations()
        {
            return new SceneStateAnnotationInfo
            {
                use3dGizmos = Bool(GetStatic("UnityEditor.AnnotationUtility", "use3dGizmos")),
                showSelectionOutline =
                    Bool(GetStatic("UnityEditor.AnnotationUtility", "showSelectionOutline")),
                showSelectionWire =
                    Bool(GetStatic("UnityEditor.AnnotationUtility", "showSelectionWire")),
                iconSize = Float(GetStatic("UnityEditor.AnnotationUtility", "iconSize"))
            };
        }

        private static SceneStateOverlayState BuildOverlays()
        {
            var state = new SceneStateOverlayState();
            var canvas = GetOverlayCanvas(SceneView.lastActiveSceneView);
            if (canvas == null) return state;
            state.available = true;
            state.overlaysEnabled = Bool(GetProperty(canvas, "overlaysEnabled"));
            foreach (var overlay in ToEnumerable(GetProperty(canvas, "overlays")))
                state.items.Add(BuildOverlayInfo(overlay));
            return state;
        }

        private static SceneStateOverlayInfo BuildOverlayInfo(object overlay)
        {
            return new SceneStateOverlayInfo
            {
                id = Text(GetProperty(overlay, "id")),
                displayName = Text(GetProperty(overlay, "displayName")),
                visible = Bool(GetProperty(overlay, "visible")),
                collapsed = Bool(GetProperty(overlay, "collapsed")),
                floating = Bool(GetProperty(overlay, "floating"))
            };
        }

        private static object GetOverlayCanvas(SceneView sv)
        {
            return sv == null ? null : GetProperty(sv, "overlayCanvas");
        }

        private static Vector3 ToVector3(float[] values)
        {
            return values != null && values.Length >= 3
                ? new Vector3(values[0], values[1], values[2])
                : Vector3.zero;
        }

        private static SceneStateVec3 FromVector3(Vector3 value)
        {
            return new SceneStateVec3 { x = value.x, y = value.y, z = value.z };
        }

        private static IEnumerable ToEnumerable(object value)
        {
            return value is IEnumerable enumerable && !(value is string)
                ? enumerable
                : Array.Empty<object>();
        }

        private static bool Has(BridgeCommand command, string fieldName)
        {
            return (command.parametersJson ?? "{}").Contains($"\"{fieldName}\"");
        }

        private static Type FindType(string fullName)
        {
            foreach (var assembly in AppDomain.CurrentDomain.GetAssemblies())
                if (assembly.GetType(fullName) != null) return assembly.GetType(fullName);
            return null;
        }

        private static object GetProperty(object target, string name)
        {
            if (target == null) return null;
            var flags = BindingFlags.Public | BindingFlags.NonPublic | BindingFlags.Instance;
            try { return target.GetType().GetProperty(name, flags)?.GetValue(target); }
            catch { return null; }
        }

        private static void SetProperty(object target, string name, object value)
        {
            if (target == null) return;
            var flags = BindingFlags.Public | BindingFlags.NonPublic | BindingFlags.Instance;
            try { target.GetType().GetProperty(name, flags)?.SetValue(target, value); }
            catch { }
        }

        private static object GetStatic(string typeName, string propertyName)
        {
            var type = FindType(typeName);
            var flags = BindingFlags.Public | BindingFlags.NonPublic | BindingFlags.Static;
            try { return type?.GetProperty(propertyName, flags)?.GetValue(null); }
            catch { return null; }
        }

        private static void SetStatic(string typeName, string propertyName, object value)
        {
            var type = FindType(typeName);
            var flags = BindingFlags.Public | BindingFlags.NonPublic | BindingFlags.Static;
            try { type?.GetProperty(propertyName, flags)?.SetValue(null, value); }
            catch { }
        }

        private static string Text(object value)
        {
            return value != null ? value.ToString() : "";
        }

        private static bool Bool(object value)
        {
            return value is bool b && b;
        }

        private static float Float(object value)
        {
            return value is float f ? f : 0f;
        }

        private static BridgeResponse Success(BridgeCommand command, SceneStateResult result)
        {
            return BridgeResponse.Success(command.commandId, command.commandType,
                JsonUtility.ToJson(result));
        }

        private static BridgeResponse Error(BridgeCommand command, string operation, string message)
        {
            var result = new SceneStateResult
            {
                success = false,
                operation = operation,
                message = message
            };
            return new BridgeResponse
            {
                commandId = command.commandId,
                commandType = command.commandType,
                status = "error",
                timestamp = DateTime.UtcNow.ToString("o"),
                dataJson = JsonUtility.ToJson(result),
                errorMessage = message
            };
        }
    }

    [Serializable]
    public class SceneStateParams
    {
        public string operation;
        public bool showGrid;
        public bool gridSnapEnabled;
        public bool snapEnabled;
        public bool angleSnapEnabled;
        public bool scaleSnapEnabled;
        public float[] gridSize;
        public float[] gridPosition;
        public float[] moveSnap;
        public float rotateSnap;
        public float scaleSnap;
        public bool drawGizmos;
        public bool use3dGizmos;
        public bool showSelectionOutline;
        public bool showSelectionWire;
        public string activeTool;
        public string pivotMode;
        public string pivotRotation;
        public bool toolsHidden;
        public int visibleLayers;
        public int lockedLayers;
        public bool overlaysEnabled;
    }

    [Serializable]
    public class SceneStateResult
    {
        public bool success;
        public string operation;
        public string message;
        public SceneStateSnapInfo snap;
        public SceneStateSceneViewInfo sceneView;
        public SceneStateToolsInfo tools;
        public SceneStateAnnotationInfo annotations;
        public SceneStateOverlayState overlays;
    }

    [Serializable]
    public class SceneStateSnapInfo
    {
        public bool gridSnapEnabled;
        public bool snapEnabled;
        public bool angleSnapEnabled;
        public bool scaleSnapEnabled;
        public bool gridSnapActive;
        public bool incrementalSnapActive;
        public SceneStateVec3 gridSize;
        public SceneStateVec3 gridPosition;
        public SceneStateVec3 moveSnap;
        public float rotateSnap;
        public float scaleSnap;
    }

    [Serializable]
    public class SceneStateSceneViewInfo
    {
        public bool exists;
        public bool showGrid;
        public bool drawGizmos;
        public bool sceneLighting;
        public bool in2DMode;
        public bool orthographic;
        public string cameraMode;
    }

    [Serializable]
    public class SceneStateToolsInfo
    {
        public string activeTool;
        public string pivotMode;
        public string pivotRotation;
        public bool toolsHidden;
        public int visibleLayers;
        public int lockedLayers;
    }

    [Serializable]
    public class SceneStateAnnotationInfo
    {
        public bool use3dGizmos;
        public bool showSelectionOutline;
        public bool showSelectionWire;
        public float iconSize;
    }

    [Serializable]
    public class SceneStateOverlayState
    {
        public bool available;
        public bool overlaysEnabled;
        public List<SceneStateOverlayInfo> items = new List<SceneStateOverlayInfo>();
    }

    [Serializable]
    public class SceneStateOverlayInfo
    {
        public string id;
        public string displayName;
        public bool visible;
        public bool collapsed;
        public bool floating;
    }

    [Serializable]
    public class SceneStateVec3
    {
        public float x;
        public float y;
        public float z;
    }
}
