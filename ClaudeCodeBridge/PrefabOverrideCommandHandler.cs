using System;
using System.Collections.Generic;
using System.Linq;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;

namespace BWS.Editor.ClaudeCodeBridge
{
    /// <summary>
    /// Command handler for granular prefab override management.
    ///
    /// PURPOSE:
    /// Provides Claude Code with the ability to inspect, apply, and revert
    /// individual prefab overrides on instances in the scene, query prefab
    /// type/status, find all instances of a prefab, and unpack prefabs.
    ///
    /// SUPPORTED OPERATIONS:
    /// 1. "list" - List all overrides on a prefab instance
    /// 2. "apply" - Apply overrides to prefab asset
    /// 3. "revert" - Revert overrides back to prefab asset state
    /// 4. "status" - Get prefab type and instance status
    /// 5. "find-instances" - Find all scene instances of a prefab asset (root-level only)
    /// 6. "unpack" - Unpack a prefab instance
    ///
    /// NOTE: This is separate from PrefabOperationCommandHandler which handles
    /// create, instantiate, apply (whole), revert (whole), and get-info.
    /// </summary>
    public class PrefabOverrideCommandHandler : ICommandHandler
    {
        public string CommandType => "prefab-override";

        public BridgeResponse Execute(BridgeCommand command)
        {
            try
            {
                var parameters = JsonUtility.FromJson<PrefabOverrideParams>(
                    command.parametersJson ?? "{}");
                if (parameters == null)
                    parameters = new PrefabOverrideParams();

                var operation = parameters.operation?.ToLower();
                BridgeLogger.LogDebug($"Executing prefab override operation: {operation}");

                // Guard: no mutating operations while compiling
                if (EditorApplication.isCompiling)
                {
                    return BridgeResponse.Error(command.commandId, command.commandType,
                        "Cannot execute while scripts are compiling.");
                }

                // Guard: no mutating operations during play mode
                if (EditorApplication.isPlaying &&
                    operation is "apply" or "revert" or "unpack")
                {
                    return BridgeResponse.Error(command.commandId, command.commandType,
                        "Mutating prefab operations are not supported during play mode.");
                }

                switch (operation)
                {
                    case "list":
                        return ListOverrides(command, parameters);
                    case "apply":
                        return ApplyOverrides(command, parameters);
                    case "revert":
                        return RevertOverrides(command, parameters);
                    case "status":
                        return GetStatus(command, parameters);
                    case "find-instances":
                        return FindInstances(command, parameters);
                    case "unpack":
                        return UnpackPrefab(command, parameters);
                    default:
                        return BridgeResponse.Error(command.commandId, command.commandType,
                            $"Unknown prefab override operation: {parameters.operation}. " +
                            "Supported: list, apply, revert, status, find-instances, unpack");
                }
            }
            catch (Exception ex)
            {
                BridgeLogger.LogError($"Prefab override error: {ex}");
                return BridgeResponse.Error(command.commandId, command.commandType, ex.ToString());
            }
        }

        private BridgeResponse ListOverrides(BridgeCommand command, PrefabOverrideParams parameters)
        {
            var go = FindGameObject(parameters.instancePath);
            if (go == null)
                return GameObjectNotFound(command, parameters.instancePath);

            if (!PrefabUtility.IsPartOfPrefabInstance(go))
                return NotPrefabInstance(command, parameters.instancePath);

            var result = new PrefabOverrideResult { success = true, operation = "list" };
            var overrides = PrefabUtility.GetObjectOverrides(go, parameters.includeDefaultOverrides);

            foreach (var ov in overrides)
            {
                var info = new PrefabOverrideInfo
                {
                    type = "PropertyModification",
                    objectPath = GetRelativePath(ov.instanceObject, go),
                    componentType = ov.instanceObject != null ? ov.instanceObject.GetType().Name : "",
                    details = $"Override on {(ov.instanceObject != null ? ov.instanceObject.GetType().Name : "unknown")}"
                };
                result.overrides.Add(info);
            }

            var addedComponents = PrefabUtility.GetAddedComponents(go);
            foreach (var ac in addedComponents)
            {
                result.overrides.Add(new PrefabOverrideInfo
                {
                    type = "AddedComponent",
                    objectPath = GetRelativePath(ac.instanceComponent.gameObject, go),
                    componentType = ac.instanceComponent.GetType().Name,
                    details = $"Added {ac.instanceComponent.GetType().Name} component"
                });
            }

            var removedComponents = PrefabUtility.GetRemovedComponents(go);
            foreach (var rc in removedComponents)
            {
                result.overrides.Add(new PrefabOverrideInfo
                {
                    type = "RemovedComponent",
                    objectPath = rc.containingInstanceGameObject != null
                        ? GetRelativePath(rc.containingInstanceGameObject, go) : "",
                    componentType = rc.assetComponent != null ? rc.assetComponent.GetType().Name : "Unknown",
                    details = $"Removed {(rc.assetComponent != null ? rc.assetComponent.GetType().Name : "Unknown")} component"
                });
            }

            var addedGOs = PrefabUtility.GetAddedGameObjects(go);
            foreach (var ag in addedGOs)
            {
                result.overrides.Add(new PrefabOverrideInfo
                {
                    type = "AddedGameObject",
                    objectPath = GetRelativePath(ag.instanceGameObject, go),
                    details = "Added child GameObject"
                });
            }

            result.hasOverrides = result.overrides.Count > 0;
            result.count = result.overrides.Count;
            return BridgeResponse.Success(command.commandId, command.commandType,
                JsonUtility.ToJson(result));
        }

        private BridgeResponse ApplyOverrides(BridgeCommand command, PrefabOverrideParams parameters)
        {
            var go = FindGameObject(parameters.instancePath);
            if (go == null)
                return GameObjectNotFound(command, parameters.instancePath);

            if (!PrefabUtility.IsPartOfPrefabInstance(go))
                return NotPrefabInstance(command, parameters.instancePath);

            Undo.SetCurrentGroupName($"Bridge: Prefab apply {parameters.instancePath}");
            var assetPath = PrefabUtility.GetPrefabAssetPathOfNearestInstanceRoot(go);
            PrefabUtility.ApplyPrefabInstance(go, InteractionMode.AutomatedAction);

            var result = new PrefabOverrideResult
            {
                success = true,
                operation = "apply",
                applied = true,
                assetPath = assetPath
            };
            return BridgeResponse.Success(command.commandId, command.commandType,
                JsonUtility.ToJson(result));
        }

        private BridgeResponse RevertOverrides(BridgeCommand command, PrefabOverrideParams parameters)
        {
            var go = FindGameObject(parameters.instancePath);
            if (go == null)
                return GameObjectNotFound(command, parameters.instancePath);

            if (!PrefabUtility.IsPartOfPrefabInstance(go))
                return NotPrefabInstance(command, parameters.instancePath);

            Undo.SetCurrentGroupName($"Bridge: Prefab revert {parameters.instancePath}");
            // MUST use 2-param version — single-param RevertPrefabInstance is OBSOLETE in Unity 6
            PrefabUtility.RevertPrefabInstance(go, InteractionMode.AutomatedAction);

            var result = new PrefabOverrideResult
            {
                success = true,
                operation = "revert",
                reverted = true
            };
            return BridgeResponse.Success(command.commandId, command.commandType,
                JsonUtility.ToJson(result));
        }

        private BridgeResponse GetStatus(BridgeCommand command, PrefabOverrideParams parameters)
        {
            var path = parameters.instancePath ?? parameters.assetPath;
            if (string.IsNullOrEmpty(path))
            {
                return BridgeResponse.Error(command.commandId, command.commandType,
                    "instancePath or assetPath is required for status operation.");
            }

            var go = FindGameObject(path);
            if (go == null)
                return GameObjectNotFound(command, path);

            var prefabType = PrefabUtility.GetPrefabAssetType(go);
            var instanceStatus = PrefabUtility.GetPrefabInstanceStatus(go);
            var assetPath = PrefabUtility.GetPrefabAssetPathOfNearestInstanceRoot(go);
            var isVariant = prefabType == PrefabAssetType.Variant;
            var isPartOfPrefab = PrefabUtility.IsPartOfAnyPrefab(go);

            var result = new PrefabOverrideResult
            {
                success = true,
                operation = "status",
                prefabType = prefabType.ToString(),
                instanceStatus = instanceStatus.ToString(),
                assetPath = assetPath,
                isVariant = isVariant,
                isPartOfPrefab = isPartOfPrefab
            };
            return BridgeResponse.Success(command.commandId, command.commandType,
                JsonUtility.ToJson(result));
        }

        private BridgeResponse FindInstances(BridgeCommand command, PrefabOverrideParams parameters)
        {
            if (string.IsNullOrEmpty(parameters.assetPath))
            {
                return BridgeResponse.Error(command.commandId, command.commandType,
                    "assetPath is required for find-instances operation.");
            }

            var prefab = AssetDatabase.LoadAssetAtPath<GameObject>(parameters.assetPath);
            if (prefab == null)
            {
                return BridgeResponse.Error(command.commandId, command.commandType,
                    $"Prefab asset not found at: {parameters.assetPath}");
            }

            // FindAllInstancesOfPrefab only returns root-level instances, no nested
            var instances = PrefabUtility.FindAllInstancesOfPrefab(prefab);
            var result = new PrefabOverrideResult
            {
                success = true,
                operation = "find-instances"
            };

            foreach (var inst in instances)
            {
                var scene = inst.scene;
                var hasOverrides = PrefabUtility.HasPrefabInstanceAnyOverrides(inst, false);
                result.instances.Add(new PrefabInstanceInfo
                {
                    path = GetFullPath(inst),
                    scene = scene.path,
                    hasOverrides = hasOverrides
                });
            }

            result.count = result.instances.Count;
            return BridgeResponse.Success(command.commandId, command.commandType,
                JsonUtility.ToJson(result));
        }

        private BridgeResponse UnpackPrefab(BridgeCommand command, PrefabOverrideParams parameters)
        {
            var go = FindGameObject(parameters.instancePath);
            if (go == null)
                return GameObjectNotFound(command, parameters.instancePath);

            if (!PrefabUtility.IsPartOfPrefabInstance(go))
                return NotPrefabInstance(command, parameters.instancePath);

            Undo.SetCurrentGroupName($"Bridge: Unpack prefab {parameters.instancePath}");
            var unpackMode = parameters.completely
                ? PrefabUnpackMode.Completely
                : PrefabUnpackMode.OutermostRoot;

            PrefabUtility.UnpackPrefabInstance(go, unpackMode, InteractionMode.AutomatedAction);

            var result = new PrefabOverrideResult
            {
                success = true,
                operation = "unpack",
                unpacked = true,
                mode = parameters.completely ? "Completely" : "OutermostRoot"
            };
            return BridgeResponse.Success(command.commandId, command.commandType,
                JsonUtility.ToJson(result));
        }

        // ---------------------------------------------------------------
        // Helpers
        // ---------------------------------------------------------------

        private static GameObject FindGameObject(string path)
        {
            if (string.IsNullOrEmpty(path)) return null;
            return GameObject.Find(path);
        }

        private static string GetFullPath(GameObject go)
        {
            var path = go.name;
            var parent = go.transform.parent;
            while (parent != null)
            {
                path = parent.name + "/" + path;
                parent = parent.parent;
            }
            return path;
        }

        private static string GetRelativePath(UnityEngine.Object obj, GameObject root)
        {
            if (obj == null) return "";
            if (obj is GameObject go) return GetRelativeGoPath(go, root);
            if (obj is Component comp) return GetRelativeGoPath(comp.gameObject, root);
            return obj.name;
        }

        private static string GetRelativeGoPath(GameObject go, GameObject root)
        {
            if (go == root) return root.name;
            var fullPath = GetFullPath(go);
            var rootPath = GetFullPath(root);
            if (fullPath.StartsWith(rootPath + "/"))
                return fullPath.Substring(rootPath.Length + 1);
            return fullPath;
        }

        private BridgeResponse GameObjectNotFound(BridgeCommand command, string path)
        {
            return BridgeResponse.Error(command.commandId, command.commandType,
                $"GameObject not found at path: {path}");
        }

        private BridgeResponse NotPrefabInstance(BridgeCommand command, string path)
        {
            return BridgeResponse.Error(command.commandId, command.commandType,
                $"GameObject at '{path}' is not a prefab instance.");
        }
    }
}
