using System;
using System.Reflection;
using UnityEditor;
using UnityEngine;

namespace BWS.Editor.ClaudeCodeBridge
{
    /// <summary>
    /// Command handler for Game View configuration.
    ///
    /// PURPOSE:
    /// Read and set Game View resolution and scale. Uses reflection to
    /// access the internal GameView class.
    ///
    /// COMMAND JSON:
    /// {
    ///   "commandId": "guid",
    ///   "commandType": "game-view",
    ///   "parametersJson": "{\"operation\":\"get\"}"
    /// }
    /// </summary>
    public class GameViewCommandHandler : ICommandHandler
    {
        public string CommandType => "game-view";

        private static readonly Type GameViewType =
            typeof(EditorWindow).Assembly.GetType("UnityEditor.GameView");

        public BridgeResponse Execute(BridgeCommand command)
        {
            try
            {
                var parameters = JsonUtility.FromJson<GameViewParams>(
                    command.parametersJson ?? "{}");

                if (parameters == null
                    || string.IsNullOrEmpty(parameters.operation))
                {
                    return BridgeResponse.Error(
                        command.commandId, command.commandType,
                        "Missing required parameter: operation");
                }

                GameViewResult result;
                switch (parameters.operation.ToLower())
                {
                    case "get":
                        result = GetGameView();
                        break;
                    case "set-resolution":
                        result = SetResolution(parameters);
                        break;
                    case "set-scale":
                        result = SetScale(parameters);
                        break;
                    default:
                        return BridgeResponse.Error(
                            command.commandId, command.commandType,
                            $"Unknown operation: {parameters.operation}. "
                            + "Supported: get, set-resolution, set-scale");
                }

                if (result.success)
                {
                    BridgeLogger.LogInfo(
                        $"game-view {parameters.operation}: {result.message}");
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

        private EditorWindow GetGameViewWindow()
        {
            if (GameViewType == null) return null;
            return EditorWindow.GetWindow(GameViewType, false, null, false);
        }

        private GameViewResult GetGameView()
        {
            var result = new GameViewResult { operation = "get" };
            var gv = GetGameViewWindow();
            if (gv == null)
            {
                result.success = false;
                result.message = "Game View window not found";
                return result;
            }

            PopulateResult(result, gv);
            result.success = true;
            result.message = "Retrieved Game View state";
            return result;
        }

        private GameViewResult SetResolution(GameViewParams parameters)
        {
            var result = new GameViewResult { operation = "set-resolution" };

            if (parameters.width <= 0 || parameters.height <= 0)
            {
                result.success = false;
                result.message = "width and height must be > 0";
                return result;
            }

            var gv = GetGameViewWindow();
            if (gv == null)
            {
                result.success = false;
                result.message = "Game View window not found";
                return result;
            }

            try
            {
                SetCustomResolution(gv, parameters.width, parameters.height);
                gv.Repaint();

                PopulateResult(result, gv);
                result.success = true;
                result.message = $"Set resolution to {parameters.width}x{parameters.height}";
            }
            catch (Exception ex)
            {
                result.success = false;
                result.message = $"Failed to set resolution: {ex.Message}";
            }

            return result;
        }

        private GameViewResult SetScale(GameViewParams parameters)
        {
            var result = new GameViewResult { operation = "set-scale" };

            if (parameters.scale <= 0f)
            {
                result.success = false;
                result.message = "scale must be > 0";
                return result;
            }

            var gv = GetGameViewWindow();
            if (gv == null)
            {
                result.success = false;
                result.message = "Game View window not found";
                return result;
            }

            try
            {
                // Try to set zoom area scale via reflection
                var zoomProp = GameViewType?.GetProperty(
                    "zoomScale",
                    BindingFlags.Instance | BindingFlags.NonPublic
                    | BindingFlags.Public);

                if (zoomProp != null && zoomProp.CanWrite)
                {
                    zoomProp.SetValue(gv, parameters.scale);
                }
                else
                {
                    // Fallback: try m_ZoomArea.m_Scale field
                    var zoomArea = GameViewType?.GetField(
                        "m_ZoomArea",
                        BindingFlags.Instance | BindingFlags.NonPublic);
                    if (zoomArea != null)
                    {
                        var za = zoomArea.GetValue(gv);
                        if (za != null)
                        {
                            var scaleProp = za.GetType().GetProperty(
                                "scale",
                                BindingFlags.Instance | BindingFlags.Public
                                | BindingFlags.NonPublic);
                            if (scaleProp != null && scaleProp.CanWrite)
                            {
                                scaleProp.SetValue(za, new Vector2(
                                    parameters.scale, parameters.scale));
                            }
                        }
                    }
                }

                gv.Repaint();
                PopulateResult(result, gv);
                result.success = true;
                result.message = $"Set scale to {parameters.scale}";
            }
            catch (Exception ex)
            {
                result.success = false;
                result.message = $"Failed to set scale: {ex.Message}";
            }

            return result;
        }

        /// <summary>
        /// Set custom resolution on the Game View using reflection.
        /// </summary>
        private void SetCustomResolution(EditorWindow gv, int width, int height)
        {
            // Access the GameViewSizesGroupType and GameViewSizeGroup
            var sizesType = typeof(EditorWindow).Assembly
                .GetType("UnityEditor.GameViewSizes");
            var singleInstance = sizesType?.GetProperty(
                "instance",
                BindingFlags.Static | BindingFlags.Public);
            var instance = singleInstance?.GetValue(null);

            if (instance == null)
            {
                // Fallback: just set the position rect size
                var pos = gv.position;
                pos.width = width;
                pos.height = height;
                gv.position = pos;
                return;
            }

            // Set the window area target size via reflection
            var targetSizeProp = GameViewType?.GetField(
                "m_TargetSize",
                BindingFlags.Instance | BindingFlags.NonPublic);

            if (targetSizeProp != null)
            {
                targetSizeProp.SetValue(gv, new Vector2(width, height));
            }
            else
            {
                // Just resize the window as a fallback
                var pos = gv.position;
                pos.width = width;
                pos.height = height;
                gv.position = pos;
            }
        }

        private void PopulateResult(GameViewResult result, EditorWindow gv)
        {
            var pos = gv.position;
            result.width = (int)pos.width;
            result.height = (int)pos.height;

            // Try to read actual target size
            var targetField = GameViewType?.GetField(
                "m_TargetSize",
                BindingFlags.Instance | BindingFlags.NonPublic);
            if (targetField != null)
            {
                var target = (Vector2)targetField.GetValue(gv);
                if (target.x > 0 && target.y > 0)
                {
                    result.width = (int)target.x;
                    result.height = (int)target.y;
                }
            }

            result.scale = 1f;
            var zoomProp = GameViewType?.GetProperty(
                "zoomScale",
                BindingFlags.Instance | BindingFlags.NonPublic
                | BindingFlags.Public);
            if (zoomProp != null)
            {
                try { result.scale = (float)zoomProp.GetValue(gv); }
                catch { /* ignore */ }
            }
        }
    }

    [Serializable]
    public class GameViewParams
    {
        public string operation;
        public int width;
        public int height;
        public float scale;
    }

    [Serializable]
    public class GameViewResult
    {
        public string operation;
        public int width;
        public int height;
        public float scale;
        public bool success;
        public string message;
    }
}
