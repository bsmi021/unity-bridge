using System;
using System.Collections.Generic;
using UnityEditor;
using UnityEngine;

namespace BWS.Editor.ClaudeCodeBridge
{
    /// <summary>
    /// Command handler for Scene View camera control.
    ///
    /// PURPOSE:
    /// Read and set the Scene View camera state (pivot, rotation, size,
    /// orthographic, 2D mode) and draw mode.
    ///
    /// COMMAND JSON:
    /// {
    ///   "commandId": "guid",
    ///   "commandType": "scene-view",
    ///   "parametersJson": "{\"operation\":\"get-camera\"}"
    /// }
    /// </summary>
    public class SceneViewCommandHandler : ICommandHandler
    {
        public string CommandType => "scene-view";

        public BridgeResponse Execute(BridgeCommand command)
        {
            try
            {
                var parameters = JsonUtility.FromJson<SceneViewParams>(
                    command.parametersJson ?? "{}");

                if (parameters == null
                    || string.IsNullOrEmpty(parameters.operation))
                {
                    return BridgeResponse.Error(
                        command.commandId, command.commandType,
                        "Missing required parameter: operation");
                }

                SceneViewResult result;
                switch (parameters.operation.ToLower())
                {
                    case "get-camera":
                        result = GetCamera();
                        break;
                    case "set-camera":
                        result = SetCamera(parameters);
                        break;
                    case "toggle-2d":
                        result = Toggle2D(parameters);
                        break;
                    case "set-draw-mode":
                        result = SetDrawMode(parameters);
                        break;
                    default:
                        return BridgeResponse.Error(
                            command.commandId, command.commandType,
                            $"Unknown operation: {parameters.operation}. "
                            + "Supported: get-camera, set-camera, toggle-2d, "
                            + "set-draw-mode");
                }

                if (result.success)
                {
                    BridgeLogger.LogInfo(
                        $"scene-view {parameters.operation}: {result.message}");
                    return BridgeResponse.Success(
                        command.commandId, command.commandType,
                        JsonUtility.ToJson(result));
                }
                return BridgeResponse.Error(
                    command.commandId, command.commandType, result.message);
            }
            catch (Exception ex)
            {
                BridgeLogger.LogError($"Error: {ex}");
                return BridgeResponse.Error(
                    command.commandId, command.commandType, ex.ToString());
            }
        }

        /// <summary>
        /// Return current scene view camera state.
        /// </summary>
        private SceneViewResult GetCamera()
        {
            var result = new SceneViewResult { operation = "get-camera" };
            var sv = SceneView.lastActiveSceneView;
            if (sv == null)
            {
                result.success = false;
                result.message = "No active SceneView found";
                return result;
            }

            PopulateFromSceneView(result, sv);
            result.success = true;
            result.message = "Retrieved scene view camera state";
            return result;
        }

        /// <summary>
        /// Set the scene view camera transform.
        /// </summary>
        private SceneViewResult SetCamera(SceneViewParams parameters)
        {
            var result = new SceneViewResult { operation = "set-camera" };
            var sv = SceneView.lastActiveSceneView;
            if (sv == null)
            {
                result.success = false;
                result.message = "No active SceneView found";
                return result;
            }

            if (parameters.pivot.isSet)
            {
                sv.pivot = new Vector3(
                    parameters.pivot.x, parameters.pivot.y, parameters.pivot.z);
            }

            if (parameters.rotation.isSet)
            {
                sv.rotation = Quaternion.Euler(
                    parameters.rotation.x,
                    parameters.rotation.y,
                    parameters.rotation.z);
            }

            if (parameters.size > 0)
            {
                sv.size = parameters.size;
            }

            if (parameters.orthographic)
            {
                sv.orthographic = true;
            }
            else if (parameters.setPerspective)
            {
                sv.orthographic = false;
            }

            sv.Repaint();

            PopulateFromSceneView(result, sv);
            result.success = true;
            result.message = "Updated scene view camera";
            return result;
        }

        /// <summary>
        /// Toggle 2D mode on the scene view.
        /// </summary>
        private SceneViewResult Toggle2D(SceneViewParams parameters)
        {
            var result = new SceneViewResult { operation = "toggle-2d" };
            var sv = SceneView.lastActiveSceneView;
            if (sv == null)
            {
                result.success = false;
                result.message = "No active SceneView found";
                return result;
            }

            sv.in2DMode = parameters.enable2D;
            sv.Repaint();

            PopulateFromSceneView(result, sv);
            result.success = true;
            result.message = $"Set 2D mode to {parameters.enable2D}";
            return result;
        }

        /// <summary>
        /// Set the draw mode (Textured, Wireframe, etc.).
        /// </summary>
        private SceneViewResult SetDrawMode(SceneViewParams parameters)
        {
            var result = new SceneViewResult { operation = "set-draw-mode" };
            var sv = SceneView.lastActiveSceneView;
            if (sv == null)
            {
                result.success = false;
                result.message = "No active SceneView found";
                return result;
            }

            if (string.IsNullOrEmpty(parameters.drawMode))
            {
                result.success = false;
                result.message = "drawMode is required for set-draw-mode";
                return result;
            }

            if (!TryParseDrawMode(parameters.drawMode, out var mode))
            {
                result.success = false;
                result.message = $"Unknown drawMode: {parameters.drawMode}. "
                    + "Supported: Textured, Wireframe, TexturedWire, "
                    + "ShadedWireframe, Shaded";
                return result;
            }

            sv.cameraMode = mode;
            sv.Repaint();

            PopulateFromSceneView(result, sv);
            result.success = true;
            result.message = $"Set draw mode to {parameters.drawMode}";
            return result;
        }

        private void PopulateFromSceneView(SceneViewResult result, SceneView sv)
        {
            result.pivotX = sv.pivot.x;
            result.pivotY = sv.pivot.y;
            result.pivotZ = sv.pivot.z;
            var euler = sv.rotation.eulerAngles;
            result.rotationX = euler.x;
            result.rotationY = euler.y;
            result.rotationZ = euler.z;
            result.cameraSize = sv.size;
            result.isOrthographic = sv.orthographic;
            result.is2D = sv.in2DMode;
            result.drawModeName = sv.cameraMode.drawMode.ToString();
        }

        private bool TryParseDrawMode(string name, out SceneView.CameraMode mode)
        {
            mode = default;
            var lower = name.ToLower();

            // Enumerate DrawCameraMode values and use the static singular method
            foreach (DrawCameraMode drawMode in Enum.GetValues(typeof(DrawCameraMode)))
            {
                if (drawMode.ToString().ToLower() == lower)
                {
                    mode = SceneView.GetBuiltinCameraMode(drawMode);
                    return true;
                }
            }
            return false;
        }
    }

    [Serializable]
    public class SceneViewVec3
    {
        public float x;
        public float y;
        public float z;
        public bool isSet;
    }

    [Serializable]
    public class SceneViewParams
    {
        public string operation;
        public SceneViewVec3 pivot = new SceneViewVec3();
        public SceneViewVec3 rotation = new SceneViewVec3();
        public float size;
        public bool orthographic;
        public bool setPerspective;
        public bool enable2D;
        public string drawMode;
    }

    [Serializable]
    public class SceneViewResult
    {
        public string operation;
        public float pivotX;
        public float pivotY;
        public float pivotZ;
        public float rotationX;
        public float rotationY;
        public float rotationZ;
        public float cameraSize;
        public bool isOrthographic;
        public bool is2D;
        public string drawModeName;
        public bool success;
        public string message;
    }
}
