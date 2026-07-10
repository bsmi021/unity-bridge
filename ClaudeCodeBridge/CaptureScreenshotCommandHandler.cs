using System;
using System.IO;
using UnityEditor;
using UnityEngine;
using UnityEngine.SceneManagement;

namespace BWS.Editor.ClaudeCodeBridge
{
    /// <summary>
    /// Command handler for capturing screenshots from scene view or game cameras.
    ///
    /// PURPOSE:
    /// Captures high-quality screenshots from Unity cameras or the scene view for documentation,
    /// testing visual output, and debugging visual issues. Supports custom resolutions and
    /// flexible camera selection.
    ///
    /// USE CASES:
    /// - Capture scene view for documentation or issue reporting
    /// - Generate test screenshots from specific camera angles
    /// - Validate visual output programmatically
    /// - Create reference images for visual regression testing
    /// - Export high-resolution images for marketing materials
    ///
    /// COMMAND JSON:
    /// {
    ///   "commandId": "guid",
    ///   "commandType": "capture-screenshot",
    ///   "timestamp": "2025-10-06T10:00:00Z",
    ///   "parametersJson": "{\"cameraPath\":\"Player/Main Camera\",\"width\":1920,\"height\":1080,\"outputPath\":\"Screenshots/test.png\"}"
    /// }
    ///
    /// USAGE EXAMPLES:
    ///
    /// 1. Capture from scene view:
    ///    send-command.ps1 -CommandType "capture-screenshot" -Parameters @{cameraPath="SceneView"; outputPath="Screenshots/scene.png"}
    ///
    /// 2. Capture from Main Camera at 4K resolution:
    ///    send-command.ps1 -CommandType "capture-screenshot" -Parameters @{cameraPath="Main Camera"; width=3840; height=2160; outputPath="Screenshots/4k.png"}
    ///
    /// 3. Capture from specific camera path:
    ///    send-command.ps1 -CommandType "capture-screenshot" -Parameters @{cameraPath="Player/CameraRig/Camera"; outputPath="Screenshots/player_view.png"}
    /// </summary>
    public class CaptureScreenshotCommandHandler : ICommandHandler
    {
        public string CommandType => "capture-screenshot";

        public BridgeResponse Execute(BridgeCommand command)
        {
            try
            {
                // Parse parameters with defaults
                var parameters = JsonUtility.FromJson<CaptureScreenshotParams>(command.parametersJson ?? "{}");
                if (parameters == null)
                    parameters = new CaptureScreenshotParams();

                // Set default output path if not specified
                if (string.IsNullOrEmpty(parameters.outputPath))
                {
                    parameters.outputPath = $"Screenshots/screenshot_{DateTime.Now:yyyyMMdd_HHmmss}.png";
                }

                BridgeLogger.LogDebug($"Capturing screenshot: camera='{parameters.cameraPath ?? "SceneView"}', resolution={parameters.width}x{parameters.height}, output='{parameters.outputPath}'");

                // Capture screenshot based on camera type
                CaptureScreenshotResult result;
                if (parameters.multiAngle)
                {
                    result = CaptureMultiAngle(parameters);
                }
                else if (string.Equals(parameters.cameraPath, "SceneView", StringComparison.OrdinalIgnoreCase))
                {
                    result = CaptureFromSceneView(parameters);
                }
                else
                {
                    result = CaptureFromCamera(parameters);
                }

                var resultJson = JsonUtility.ToJson(result);

                if (result.success)
                {
                    BridgeLogger.LogInfo($"Successfully captured screenshot: {result.outputPath} ({result.fileSizeBytes} bytes)");
                    return BridgeResponse.Success(command.commandId, command.commandType, resultJson);
                }
                else
                {
                    BridgeLogger.LogError($"Failed to capture screenshot: {result.message}");
                    return BridgeResponse.Error(command.commandId, command.commandType, result.message);
                }
            }
            catch (Exception ex)
            {
                BridgeLogger.LogError($"Error: {ex}");
                return BridgeResponse.Error(command.commandId, command.commandType, ex.ToString());
            }
        }

        /// <summary>
        /// Capture screenshot from the active scene view.
        /// Uses SceneView.lastActiveSceneView to get the current scene camera.
        /// </summary>
        private CaptureScreenshotResult CaptureFromSceneView(CaptureScreenshotParams parameters)
        {
            var result = new CaptureScreenshotResult
            {
                width = parameters.width,
                height = parameters.height,
                outputPath = parameters.outputPath
            };

            try
            {
                // Get the active scene view
                var sceneView = SceneView.lastActiveSceneView;
                if (sceneView == null)
                {
                    result.success = false;
                    result.message = "No active scene view found. Please open a scene view in the Unity Editor.";
                    return result;
                }

                // Create render texture
                RenderTexture renderTexture = new RenderTexture(parameters.width, parameters.height, 24);
                RenderTexture previousActive = RenderTexture.active;

                try
                {
                    // Store original camera state
                    UnityEngine.Camera sceneCamera = sceneView.camera;
                    RenderTexture originalTargetTexture = sceneCamera.targetTexture;

                    // Set up camera to render to our texture
                    sceneCamera.targetTexture = renderTexture;
                    RenderTexture.active = renderTexture;

                    // Render the scene
                    sceneCamera.Render();

                    // Read pixels from render texture
                    Texture2D screenshot = new Texture2D(parameters.width, parameters.height, TextureFormat.RGB24, false);
                    screenshot.ReadPixels(new Rect(0, 0, parameters.width, parameters.height), 0, 0);
                    screenshot.Apply();

                    // Save to file
                    SaveScreenshot(screenshot, parameters.outputPath, out result.fileSizeBytes);
                    MaybePopulateBase64(result, parameters);

                    // Cleanup
                    UnityEngine.Object.DestroyImmediate(screenshot);

                    // Restore original camera state
                    sceneCamera.targetTexture = originalTargetTexture;

                    result.success = true;
                    result.message = $"Successfully captured screenshot from scene view";
                }
                finally
                {
                    // Restore active render texture
                    RenderTexture.active = previousActive;
                    UnityEngine.Object.DestroyImmediate(renderTexture);
                }
            }
            catch (Exception ex)
            {
                result.success = false;
                result.message = $"Failed to capture from scene view: {ex.Message}";
                BridgeLogger.LogError($"Scene view capture error: {ex}");
            }

            return result;
        }

        /// <summary>
        /// Capture screenshot from a specific camera in the scene.
        /// Uses GameObject path to find the camera component.
        /// </summary>
        private CaptureScreenshotResult CaptureFromCamera(CaptureScreenshotParams parameters)
        {
            var result = new CaptureScreenshotResult
            {
                width = parameters.width,
                height = parameters.height,
                outputPath = parameters.outputPath
            };

            try
            {
                // Find the camera
                UnityEngine.Camera camera = FindCamera(parameters.cameraPath);
                if (camera == null)
                {
                    result.success = false;
                    result.message = $"Camera not found at path: {parameters.cameraPath}";
                    return result;
                }

                // Create render texture
                RenderTexture renderTexture = new RenderTexture(parameters.width, parameters.height, 24);
                RenderTexture previousActive = RenderTexture.active;

                try
                {
                    // Store original camera state
                    RenderTexture originalTargetTexture = camera.targetTexture;

                    // Set up camera to render to our texture
                    camera.targetTexture = renderTexture;
                    RenderTexture.active = renderTexture;

                    // Render the camera
                    camera.Render();

                    // Read pixels from render texture
                    Texture2D screenshot = new Texture2D(parameters.width, parameters.height, TextureFormat.RGB24, false);
                    screenshot.ReadPixels(new Rect(0, 0, parameters.width, parameters.height), 0, 0);
                    screenshot.Apply();

                    // Save to file
                    SaveScreenshot(screenshot, parameters.outputPath, out result.fileSizeBytes);
                    MaybePopulateBase64(result, parameters);

                    // Cleanup
                    UnityEngine.Object.DestroyImmediate(screenshot);

                    // Restore original camera state
                    camera.targetTexture = originalTargetTexture;

                    result.success = true;
                    result.message = $"Successfully captured screenshot from camera: {parameters.cameraPath}";
                }
                finally
                {
                    // Restore active render texture
                    RenderTexture.active = previousActive;
                    UnityEngine.Object.DestroyImmediate(renderTexture);
                }
            }
            catch (Exception ex)
            {
                result.success = false;
                result.message = $"Failed to capture from camera: {ex.Message}";
                BridgeLogger.LogError($"Camera capture error: {ex}");
            }

            return result;
        }

        private CaptureScreenshotResult CaptureMultiAngle(CaptureScreenshotParams parameters)
        {
            var result = new CaptureScreenshotResult
            {
                width = parameters.width,
                height = parameters.height,
                outputPath = parameters.outputPath,
                success = true,
                message = "Captured multi-angle scene view screenshots"
            };

            var sceneView = SceneView.lastActiveSceneView;
            SceneViewState? originalState = sceneView == null
                ? (SceneViewState?)null
                : CaptureSceneViewState(sceneView);
            try
            {
                foreach (var angle in new[] { "isometric", "front", "top", "right" })
                {
                    var captureParams = CloneForAngle(parameters, angle);
                    ApplySceneViewAngle(angle);
                    var capture = CaptureFromSceneView(captureParams);
                    capture.angle = angle;
                    result.captures.Add(capture);
                    result.fileSizeBytes += capture.fileSizeBytes;
                    if (!capture.success)
                    {
                        result.success = false;
                        result.message = capture.message;
                        break;
                    }
                }
            }
            finally
            {
                if (sceneView != null && originalState.HasValue)
                    RestoreSceneViewState(sceneView, originalState.Value);
            }

            return result;
        }

        private struct SceneViewState
        {
            public Vector3 pivot;
            public Quaternion rotation;
            public float size;
            public bool orthographic;
            public bool in2DMode;
        }

        private static SceneViewState CaptureSceneViewState(SceneView sceneView)
        {
            return new SceneViewState
            {
                pivot = sceneView.pivot,
                rotation = sceneView.rotation,
                size = sceneView.size,
                orthographic = sceneView.orthographic,
                in2DMode = sceneView.in2DMode,
            };
        }

        private static void RestoreSceneViewState(SceneView sceneView, SceneViewState state)
        {
            sceneView.in2DMode = state.in2DMode;
            sceneView.LookAt(state.pivot, state.rotation, state.size, state.orthographic, true);
            sceneView.Repaint();
        }

        private CaptureScreenshotParams CloneForAngle(CaptureScreenshotParams parameters, string angle)
        {
            return new CaptureScreenshotParams
            {
                cameraPath = "SceneView",
                width = parameters.width,
                height = parameters.height,
                outputPath = OutputPathForAngle(parameters.outputPath, angle),
                captureUI = parameters.captureUI,
                returnBase64 = parameters.returnBase64
            };
        }

        private string OutputPathForAngle(string outputPath, string angle)
        {
            var directory = Path.GetDirectoryName(outputPath);
            var name = Path.GetFileNameWithoutExtension(outputPath);
            var extension = Path.GetExtension(outputPath);
            if (string.IsNullOrEmpty(extension))
                extension = ".png";
            return Path.Combine(directory ?? "", $"{name}-{angle}{extension}").Replace("\\", "/");
        }

        private void ApplySceneViewAngle(string angle)
        {
            var sceneView = SceneView.lastActiveSceneView;
            if (sceneView == null)
                return;
            Quaternion rotation;
            switch (angle)
            {
                case "front": rotation = Quaternion.Euler(0f, 0f, 0f); break;
                case "top": rotation = Quaternion.Euler(90f, 0f, 0f); break;
                case "right": rotation = Quaternion.Euler(0f, -90f, 0f); break;
                default: rotation = Quaternion.Euler(35f, 45f, 0f); break;
            }
            sceneView.LookAt(sceneView.pivot, rotation, sceneView.size, sceneView.orthographic, true);
            sceneView.Repaint();
        }

        /// <summary>
        /// Find a camera by GameObject path or name.
        /// Searches the active scene hierarchy for the camera.
        /// </summary>
        private UnityEngine.Camera FindCamera(string cameraPath)
        {
            if (string.IsNullOrEmpty(cameraPath))
            {
                // Try to find main camera
                var mainCamera = UnityEngine.Camera.main;
                if (mainCamera != null)
                    return mainCamera;

                // Fallback to any camera
                return UnityEngine.Camera.allCameras.Length > 0 ? UnityEngine.Camera.allCameras[0] : null;
            }

            // Try to find by path
            var activeScene = SceneManager.GetActiveScene();
            var rootObjects = activeScene.GetRootGameObjects();

            // First try exact path match
            foreach (var rootObject in rootObjects)
            {
                var camera = FindCameraInHierarchy(rootObject.transform, cameraPath);
                if (camera != null)
                    return camera;
            }

            // Fallback: try to find by name only
            foreach (var cam in UnityEngine.Camera.allCameras)
            {
                if (cam.gameObject.name == cameraPath)
                    return cam;
            }

            return null;
        }

        /// <summary>
        /// Recursively search for a camera in the GameObject hierarchy.
        /// Matches against full path from root to target GameObject.
        /// </summary>
        private UnityEngine.Camera FindCameraInHierarchy(Transform current, string targetPath)
        {
            // Build current path
            string currentPath = current.name;
            Transform parent = current.parent;
            while (parent != null)
            {
                currentPath = parent.name + "/" + currentPath;
                parent = parent.parent;
            }

            // Check if current object matches the path
            if (currentPath.EndsWith(targetPath, StringComparison.OrdinalIgnoreCase) ||
                current.name.Equals(targetPath, StringComparison.OrdinalIgnoreCase))
            {
                var camera = current.GetComponent<UnityEngine.Camera>();
                if (camera != null)
                    return camera;
            }

            // Search children recursively
            for (int i = 0; i < current.childCount; i++)
            {
                var camera = FindCameraInHierarchy(current.GetChild(i), targetPath);
                if (camera != null)
                    return camera;
            }

            return null;
        }

        /// <summary>
        /// Save the screenshot texture to a PNG file.
        /// Creates the output directory if it doesn't exist.
        /// </summary>
        private void SaveScreenshot(Texture2D screenshot, string outputPath, out long fileSizeBytes)
        {
            string fullPath = ResolveOutputPath(outputPath);

            // Create directory if it doesn't exist
            string directory = Path.GetDirectoryName(fullPath);
            if (!Directory.Exists(directory))
            {
                Directory.CreateDirectory(directory);
                BridgeLogger.LogDebug($"Created directory: {directory}");
            }

            // Encode to PNG and save
            byte[] pngData = screenshot.EncodeToPNG();
            File.WriteAllBytes(fullPath, pngData);
            fileSizeBytes = pngData.Length;

            BridgeLogger.LogDebug($"Saved screenshot to: {fullPath}");
        }

        private void MaybePopulateBase64(
            CaptureScreenshotResult result,
            CaptureScreenshotParams parameters)
        {
            if (!parameters.returnBase64 || string.IsNullOrEmpty(result.outputPath))
                return;
            var fullPath = ResolveOutputPath(result.outputPath);
            if (File.Exists(fullPath))
                result.base64Png = Convert.ToBase64String(File.ReadAllBytes(fullPath));
        }

        private string ResolveOutputPath(string outputPath)
        {
            if (Path.IsPathRooted(outputPath))
                return outputPath;
            string projectRoot = Directory.GetParent(Application.dataPath).FullName;
            return Path.Combine(projectRoot, outputPath);
        }
    }
}
