using System;
using System.Collections.Generic;
using System.Reflection;
using UnityEditor;
using UnityEngine;

namespace BWS.Editor.ClaudeCodeBridge
{
    /// <summary>
    /// Command handler for Unity Cinemachine (com.unity.cinemachine) operations.
    /// All operations use reflection because Cinemachine is an optional UPM
    /// package: this file must compile even when the package is absent.
    ///
    /// SUPPORTED OPERATIONS:
    /// 1. "list-cameras"      - List all CinemachineCamera instances in the scene
    /// 2. "get-camera-info"   - Priority/lens/follow/lookat for one camera
    /// 3. "set-priority"      - Set a camera's priority
    /// 4. "set-lens"          - Set any subset of lens fields
    /// 5. "set-follow"        - Set or clear the Follow target
    /// 6. "set-lookat"        - Set or clear the LookAt target
    /// 7. "get-active-camera" - Active camera via the main camera's CinemachineBrain
    /// </summary>
    public class CinemachineCommandHandler : ICommandHandler
    {
        private const string CameraTypeName = "Unity.Cinemachine.CinemachineCamera, Unity.Cinemachine";
        private const string BrainTypeName = "Unity.Cinemachine.CinemachineBrain, Unity.Cinemachine";
        private const string NotInstalledMessage =
            "Cinemachine package not installed. Install via Package Manager: com.unity.cinemachine";

        public string CommandType => "cinemachine-operation";

        public BridgeResponse Execute(BridgeCommand command)
        {
            try
            {
                if (EditorApplication.isCompiling)
                {
                    return BridgeResponse.Error(command.commandId, command.commandType,
                        "Cannot perform Cinemachine operations while scripts are compiling.");
                }

                var parameters = JsonUtility.FromJson<CinemachineParams>(
                    command.parametersJson ?? "{}");
                if (parameters == null)
                    parameters = new CinemachineParams();

                BridgeLogger.LogDebug($"Executing cinemachine operation: {parameters.operation}");

                return DispatchOperation(command, parameters);
            }
            catch (Exception ex)
            {
                if (ex is TypeLoadException || ex is System.IO.FileNotFoundException)
                {
                    return BridgeResponse.Error(command.commandId, command.commandType,
                        NotInstalledMessage);
                }
                BridgeLogger.LogError($"Cinemachine operation error: {ex}");
                return BridgeResponse.Error(command.commandId, command.commandType, ex.ToString());
            }
        }

        private BridgeResponse DispatchOperation(BridgeCommand command, CinemachineParams p)
        {
            Type cameraType = Type.GetType(CameraTypeName);
            if (cameraType is null)
            {
                return BridgeResponse.Error(command.commandId, command.commandType, NotInstalledMessage);
            }

            switch (p.operation?.ToLower())
            {
                case "list-cameras":
                    return ExecuteListCameras(command, cameraType);
                case "get-camera-info":
                    return ExecuteGetCameraInfo(command, p, cameraType);
                case "set-priority":
                    return ExecuteSetPriority(command, p, cameraType);
                case "set-lens":
                    return ExecuteSetLens(command, p, cameraType);
                case "set-follow":
                    return ExecuteSetFollow(command, p, cameraType);
                case "set-lookat":
                    return ExecuteSetLookAt(command, p, cameraType);
                case "get-active-camera":
                    return ExecuteGetActiveCamera(command);
                default:
                    return BridgeResponse.Error(
                        command.commandId, command.commandType,
                        $"Unknown cinemachine operation: {p.operation}. "
                        + "Supported: list-cameras, get-camera-info, set-priority, "
                        + "set-lens, set-follow, set-lookat, get-active-camera");
            }
        }

        private BridgeResponse ExecuteListCameras(BridgeCommand command, Type cameraType)
        {
            var cameras = FindAllCameras(cameraType);
            var infos = new List<CinemachineCameraInfo>();
            foreach (var cam in cameras)
            {
                var behaviour = cam as Behaviour;
                var component = cam as Component;
                infos.Add(new CinemachineCameraInfo
                {
                    path = GetHierarchyPath(component?.transform),
                    priority = GetPriority(cam, cameraType),
                    enabled = behaviour is not null && behaviour.enabled,
                    activeInHierarchy = component is not null && component.gameObject.activeInHierarchy
                });
            }

            var result = new CinemachineListResult
            {
                operation = "list-cameras",
                cameras = infos,
                success = true,
                message = $"Found {infos.Count} Cinemachine cameras"
            };
            return BridgeResponse.Success(
                command.commandId, command.commandType, JsonUtility.ToJson(result));
        }

        private BridgeResponse ExecuteGetCameraInfo(
            BridgeCommand command, CinemachineParams p, Type cameraType)
        {
            var camera = FindCamera(p.cameraPath, cameraType, out var error);
            if (camera is null)
            {
                return BridgeResponse.Error(command.commandId, command.commandType, error);
            }

            var lens = GetLens(camera, cameraType);
            var follow = GetTargetPath(camera, cameraType, "Follow");
            var lookAt = GetTargetPath(camera, cameraType, "LookAt");
            var behaviour = camera as Behaviour;

            var result = new CinemachineCameraInfoResult
            {
                operation = "get-camera-info",
                path = p.cameraPath,
                priority = GetPriority(camera, cameraType),
                enabled = behaviour is not null && behaviour.enabled,
                fieldOfView = GetLensField(lens, "FieldOfView"),
                orthographicSize = GetLensField(lens, "OrthographicSize"),
                nearClipPlane = GetLensField(lens, "NearClipPlane"),
                farClipPlane = GetLensField(lens, "FarClipPlane"),
                dutch = GetLensField(lens, "Dutch"),
                followPath = follow,
                lookAtPath = lookAt,
                success = true,
                message = "Camera info retrieved"
            };
            return BridgeResponse.Success(
                command.commandId, command.commandType, JsonUtility.ToJson(result));
        }

        private BridgeResponse ExecuteSetPriority(
            BridgeCommand command, CinemachineParams p, Type cameraType)
        {
            var camera = FindCamera(p.cameraPath, cameraType, out var error);
            if (camera is null)
            {
                return BridgeResponse.Error(command.commandId, command.commandType, error);
            }

            var priorityProp = cameraType.GetProperty("Priority",
                BindingFlags.Public | BindingFlags.Instance);
            if (priorityProp is not null)
            {
                var toPrioritySettings = priorityProp.PropertyType.GetMethod(
                    "op_Implicit", new[] { typeof(int) });
                if (toPrioritySettings is not null)
                {
                    priorityProp.SetValue(
                        camera, toPrioritySettings.Invoke(null, new object[] { p.priority }));
                }
            }

            var result = new CinemachineResult
            {
                operation = "set-priority",
                success = true,
                message = $"Priority set to {p.priority} for '{p.cameraPath}'"
            };
            return BridgeResponse.Success(
                command.commandId, command.commandType, JsonUtility.ToJson(result));
        }

        private BridgeResponse ExecuteSetLens(
            BridgeCommand command, CinemachineParams p, Type cameraType)
        {
            var camera = FindCamera(p.cameraPath, cameraType, out var error);
            if (camera is null)
            {
                return BridgeResponse.Error(command.commandId, command.commandType, error);
            }

            var lensProp = cameraType.GetProperty("Lens", BindingFlags.Public | BindingFlags.Instance);
            if (lensProp is null)
            {
                return BridgeResponse.Error(command.commandId, command.commandType,
                    "Could not find Lens property on CinemachineCamera.");
            }

            object boxedLens = lensProp.GetValue(camera);
            Type lensType = boxedLens.GetType();
            bool changed = false;

            changed |= SetLensField(lensType, boxedLens, "FieldOfView", p.fieldOfView, p.fieldOfView > 0f);
            changed |= SetLensField(
                lensType, boxedLens, "OrthographicSize", p.orthographicSize, p.orthographicSize > 0f);
            changed |= SetLensField(
                lensType, boxedLens, "NearClipPlane", p.nearClipPlane, p.nearClipPlane > 0f);
            changed |= SetLensField(
                lensType, boxedLens, "FarClipPlane", p.farClipPlane, p.farClipPlane > 0f);
            changed |= SetLensField(
                lensType, boxedLens, "Dutch", p.dutch, !float.IsNaN(p.dutch));

            if (changed)
                lensProp.SetValue(camera, boxedLens);

            var result = new CinemachineResult
            {
                operation = "set-lens",
                success = true,
                message = changed
                    ? $"Lens updated for '{p.cameraPath}'"
                    : "No lens fields provided to update"
            };
            return BridgeResponse.Success(
                command.commandId, command.commandType, JsonUtility.ToJson(result));
        }

        private BridgeResponse ExecuteSetFollow(
            BridgeCommand command, CinemachineParams p, Type cameraType)
        {
            return SetTarget(command, p, cameraType, "Follow", p.followPath);
        }

        private BridgeResponse ExecuteSetLookAt(
            BridgeCommand command, CinemachineParams p, Type cameraType)
        {
            return SetTarget(command, p, cameraType, "LookAt", p.lookAtPath);
        }

        private BridgeResponse SetTarget(
            BridgeCommand command, CinemachineParams p, Type cameraType,
            string propertyName, string targetPath)
        {
            var camera = FindCamera(p.cameraPath, cameraType, out var error);
            if (camera is null)
            {
                return BridgeResponse.Error(command.commandId, command.commandType, error);
            }

            Transform target = null;
            if (!string.IsNullOrEmpty(targetPath))
            {
                var targetObject = GameObject.Find(targetPath);
                if (targetObject is null)
                {
                    return BridgeResponse.Error(command.commandId, command.commandType,
                        $"Target GameObject not found at path: {targetPath}");
                }
                target = targetObject.transform;
            }

            var prop = cameraType.GetProperty(propertyName, BindingFlags.Public | BindingFlags.Instance);
            prop?.SetValue(camera, target);

            var result = new CinemachineResult
            {
                operation = propertyName == "Follow" ? "set-follow" : "set-lookat",
                success = true,
                message = target is null
                    ? $"{propertyName} target cleared for '{p.cameraPath}'"
                    : $"{propertyName} target set to '{targetPath}' for '{p.cameraPath}'"
            };
            return BridgeResponse.Success(
                command.commandId, command.commandType, JsonUtility.ToJson(result));
        }

        private BridgeResponse ExecuteGetActiveCamera(BridgeCommand command)
        {
            Type brainType = Type.GetType(BrainTypeName);
            if (brainType is null)
            {
                return BridgeResponse.Error(command.commandId, command.commandType, NotInstalledMessage);
            }

            var mainCamera = Camera.main;
            var brain = mainCamera?.GetComponent(brainType);
            if (brain is null)
            {
                var result = new CinemachineActiveCameraResult
                {
                    operation = "get-active-camera",
                    hasActiveCamera = false,
                    success = false,
                    message = "No CinemachineBrain found on the main camera."
                };
                return BridgeResponse.Success(
                    command.commandId, command.commandType, JsonUtility.ToJson(result));
            }

            var activeVcamProp = brainType.GetProperty("ActiveVirtualCamera",
                BindingFlags.Public | BindingFlags.Instance);
            var isBlendingProp = brainType.GetProperty("IsBlending",
                BindingFlags.Public | BindingFlags.Instance);
            var outputCameraProp = brainType.GetProperty("OutputCamera",
                BindingFlags.Public | BindingFlags.Instance);

            object activeVcam = activeVcamProp?.GetValue(brain);
            string activeName = null;
            if (activeVcam is not null)
            {
                var nameProp = activeVcam.GetType().GetProperty("Name");
                activeName = nameProp?.GetValue(activeVcam) as string;
                if (string.IsNullOrEmpty(activeName) && activeVcam is Component activeComponent)
                    activeName = activeComponent.name;
            }

            var outputCamera = outputCameraProp?.GetValue(brain) as Camera;

            var activeResult = new CinemachineActiveCameraResult
            {
                operation = "get-active-camera",
                hasActiveCamera = activeVcam is not null,
                activeCameraName = activeName,
                isBlending = isBlendingProp is not null && (bool)isBlendingProp.GetValue(brain),
                outputCameraName = outputCamera is not null ? outputCamera.name : null,
                success = true,
                message = activeVcam is not null
                    ? $"Active camera: {activeName}"
                    : "No active virtual camera."
            };
            return BridgeResponse.Success(
                command.commandId, command.commandType, JsonUtility.ToJson(activeResult));
        }

        // -----------------------------------------------------------------
        // Reflection helpers
        // -----------------------------------------------------------------

        private static List<object> FindAllCameras(Type cameraType)
        {
            var found = new List<object>();
            var results = UnityEngine.Object.FindObjectsByType(
                cameraType, FindObjectsInactive.Include, FindObjectsSortMode.None);
            if (results is not null)
            {
                foreach (var item in results)
                    found.Add(item);
            }
            return found;
        }

        private object FindCamera(string path, Type cameraType, out string error)
        {
            error = null;
            if (string.IsNullOrEmpty(path))
            {
                error = "cameraPath is required.";
                return null;
            }

            var gameObject = GameObject.Find(path);
            if (gameObject is null)
            {
                error = $"GameObject not found at path: {path}";
                return null;
            }

            var camera = gameObject.GetComponent(cameraType);
            if (camera is null)
            {
                error = $"No CinemachineCamera component found at path: {path}";
                return null;
            }

            return camera;
        }

        private static int GetPriority(object camera, Type cameraType)
        {
            var priorityProp = cameraType.GetProperty("Priority",
                BindingFlags.Public | BindingFlags.Instance);
            var value = priorityProp?.GetValue(camera);
            if (value is null)
                return 0;

            var toInt = value.GetType().GetMethod("op_Implicit", new[] { value.GetType() });
            if (toInt is not null)
                return (int)toInt.Invoke(null, new object[] { value });

            return 0;
        }

        private static object GetLens(object camera, Type cameraType)
        {
            var lensProp = cameraType.GetProperty("Lens", BindingFlags.Public | BindingFlags.Instance);
            return lensProp?.GetValue(camera);
        }

        private static float GetLensField(object boxedLens, string fieldName)
        {
            if (boxedLens is null)
                return 0f;
            var field = boxedLens.GetType().GetField(fieldName, BindingFlags.Public | BindingFlags.Instance);
            var value = field?.GetValue(boxedLens);
            return value is null ? 0f : Convert.ToSingle(value);
        }

        private static bool SetLensField(
            Type lensType, object boxedLens, string fieldName, float value, bool shouldSet)
        {
            if (!shouldSet)
                return false;

            var field = lensType.GetField(fieldName, BindingFlags.Public | BindingFlags.Instance);
            if (field is null)
                return false;

            field.SetValue(boxedLens, value);
            return true;
        }

        private static string GetTargetPath(object camera, Type cameraType, string propertyName)
        {
            var prop = cameraType.GetProperty(propertyName, BindingFlags.Public | BindingFlags.Instance);
            var transform = prop?.GetValue(camera) as Transform;
            return transform is null ? string.Empty : GetHierarchyPath(transform);
        }

        private static string GetHierarchyPath(Transform transform)
        {
            if (transform is null)
                return string.Empty;

            var segments = new List<string>();
            var current = transform;
            while (current is not null)
            {
                segments.Insert(0, current.name);
                current = current.parent;
            }
            return string.Join("/", segments);
        }
    }
}
