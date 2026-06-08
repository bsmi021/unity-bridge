using System;
using System.Collections.Generic;
using System.Reflection;
using UnityEditor;
using UnityEngine;
using UnityEngine.SceneManagement;

namespace BWS.Editor.ClaudeCodeBridge
{
    /// <summary>
    /// Reports stable and transient Unity object identity forms.
    ///
    /// SUPPORTED OPERATIONS:
    /// 1. "get-selection" - Return identity info for Selection.objects.
    /// 2. "resolve"       - Resolve one target by path, GlobalObjectId, or instance ID.
    /// 3. "ping"          - Resolve one target and ping it in the Editor.
    /// </summary>
    public class ObjectIdentityCommandHandler : ICommandHandler
    {
        public string CommandType => "object-identity";

        private static readonly MethodInfo GetEntityIdMethod =
            typeof(UnityEngine.Object).GetMethod(
                "GetEntityId",
                BindingFlags.Public | BindingFlags.Instance,
                null,
                Type.EmptyTypes,
                null);
        private static readonly MethodInfo GetInstanceIdMethod =
            typeof(UnityEngine.Object).GetMethod(
                "GetInstanceID",
                BindingFlags.Public | BindingFlags.Instance,
                null,
                Type.EmptyTypes,
                null);
        private static readonly MethodInfo InstanceIdToObjectMethod =
            typeof(EditorUtility).GetMethod(
                "InstanceIDToObject",
                BindingFlags.Public | BindingFlags.Static,
                null,
                new[] { typeof(int) },
                null);
        private static readonly MethodInfo PingObjectMethod =
            typeof(EditorUtility).GetMethod(
                "PingObject",
                BindingFlags.Public | BindingFlags.Static,
                null,
                new[] { typeof(UnityEngine.Object) },
                null)
            ?? typeof(EditorGUIUtility).GetMethod(
                "PingObject",
                BindingFlags.Public | BindingFlags.Static,
                null,
                new[] { typeof(UnityEngine.Object) },
                null);

        public BridgeResponse Execute(BridgeCommand command)
        {
            try
            {
                var parameters = JsonUtility.FromJson<ObjectIdentityParams>(
                    command.parametersJson ?? "{}") ?? new ObjectIdentityParams();
                var operation = string.IsNullOrEmpty(parameters.operation)
                    ? "get-selection"
                    : parameters.operation.ToLower();

                switch (operation)
                {
                    case "get-selection":
                        return HandleGetSelection(command);
                    case "resolve":
                        return HandleResolve(command, parameters);
                    case "ping":
                        return HandlePing(command, parameters);
                    default:
                        return Error(command, operation,
                            "Unknown operation. Supported: get-selection, resolve, ping");
                }
            }
            catch (Exception ex)
            {
                BridgeLogger.LogError($"Object identity error: {ex}");
                return Error(command, "object-identity", ex.ToString());
            }
        }

        private BridgeResponse HandleGetSelection(BridgeCommand command)
        {
            var objects = new List<ObjectIdentityInfo>();
            foreach (var obj in Selection.objects)
            {
                if (obj != null)
                    objects.Add(BuildInfo(obj));
            }

            var result = new ObjectIdentityResult
            {
                success = true,
                operation = "get-selection",
                objects = objects,
                count = objects.Count,
                message = $"Selection contains {objects.Count} object(s)."
            };
            return Success(command, result);
        }

        private BridgeResponse HandleResolve(
            BridgeCommand command,
            ObjectIdentityParams parameters)
        {
            var target = ResolveTarget(parameters, out var message);
            if (target == null)
                return Error(command, "resolve", message);

            return Success(command, new ObjectIdentityResult
            {
                success = true,
                operation = "resolve",
                objects = new List<ObjectIdentityInfo> { BuildInfo(target) },
                count = 1,
                message = $"Resolved {target.name}."
            });
        }

        private BridgeResponse HandlePing(
            BridgeCommand command,
            ObjectIdentityParams parameters)
        {
            var target = ResolveTarget(parameters, out var message);
            if (target == null)
                return Error(command, "ping", message);

            PingObject(target);
            return Success(command, new ObjectIdentityResult
            {
                success = true,
                operation = "ping",
                objects = new List<ObjectIdentityInfo> { BuildInfo(target) },
                count = 1,
                message = $"Pinged {target.name}."
            });
        }

        private static UnityEngine.Object ResolveTarget(
            ObjectIdentityParams parameters,
            out string message)
        {
            if (!string.IsNullOrEmpty(parameters.gameObjectPath))
                return ResolveGameObject(parameters.gameObjectPath, out message);
            if (!string.IsNullOrEmpty(parameters.assetPath))
                return ResolveAsset(parameters.assetPath, out message);
            if (!string.IsNullOrEmpty(parameters.globalObjectId))
                return ResolveGlobalObjectId(parameters.globalObjectId, out message);
            if (!string.IsNullOrEmpty(parameters.entityId))
                return ResolveEntityId(parameters.entityId, out message);
            if (parameters.instanceId != 0)
                return ResolveInstanceId(parameters.instanceId, out message);

            message = "One target is required: gameObjectPath, assetPath, " +
                "globalObjectId, entityId, or instanceId.";
            return null;
        }

        private static UnityEngine.Object ResolveGameObject(string path, out string message)
        {
            var obj = FindGameObjectByPath(path);
            message = obj == null ? $"GameObject not found: {path}" : null;
            return obj;
        }

        private static UnityEngine.Object ResolveAsset(string path, out string message)
        {
            var obj = AssetDatabase.LoadAssetAtPath<UnityEngine.Object>(path);
            message = obj == null ? $"Asset not found: {path}" : null;
            return obj;
        }

        private static UnityEngine.Object ResolveGlobalObjectId(string value, out string message)
        {
            if (!GlobalObjectId.TryParse(value, out var id))
            {
                message = $"Invalid GlobalObjectId: {value}";
                return null;
            }

            var obj = GlobalObjectId.GlobalObjectIdentifierToObjectSlow(id);
            message = obj == null ? $"Object not found for GlobalObjectId: {value}" : null;
            return obj;
        }

        private static UnityEngine.Object ResolveInstanceId(int instanceId, out string message)
        {
            var obj = InstanceIdToObjectMethod?.Invoke(null, new object[] { instanceId })
                as UnityEngine.Object;
            message = obj == null ? $"Object not found for instanceId: {instanceId}" : null;
            return obj;
        }

        private static UnityEngine.Object ResolveEntityId(string entityId, out string message)
        {
            var entityIdType = FindType("UnityEngine.EntityId");
            var entityIdToObject = FindEntityIdToObject(entityIdType);
            if (entityIdType == null || entityIdToObject == null)
            {
                message = "EntityId resolution is not available in this Unity version.";
                return null;
            }

            object value = ConvertToEntityId(entityIdType, entityId);
            if (value == null)
            {
                message = $"Invalid EntityId: {entityId}";
                return null;
            }

            var obj = entityIdToObject.Invoke(null, new[] { value }) as UnityEngine.Object;
            message = obj == null ? $"Object not found for EntityId: {entityId}" : null;
            return obj;
        }

        private static ObjectIdentityInfo BuildInfo(UnityEngine.Object obj)
        {
            var go = AsGameObject(obj);
            var persistent = EditorUtility.IsPersistent(obj);
            var assetPath = AssetDatabase.GetAssetPath(obj);
            return new ObjectIdentityInfo
            {
                name = obj.name,
                type = obj.GetType().FullName,
                instanceId = GetLegacyInstanceId(obj),
                entityId = GetEntityId(obj),
                globalObjectId = GetGlobalObjectId(obj),
                assetPath = assetPath,
                scenePath = go != null && !persistent ? go.scene.path : "",
                hierarchyPath = go != null && !persistent ? GetHierarchyPath(go) : "",
                isAsset = persistent && !string.IsNullOrEmpty(assetPath),
                isSceneObject = go != null && !persistent,
                isPersistent = persistent
            };
        }

        private static string GetEntityId(UnityEngine.Object obj)
        {
            if (GetEntityIdMethod == null)
                return "";

            try
            {
                return GetEntityIdMethod.Invoke(obj, null)?.ToString() ?? "";
            }
            catch
            {
                return "";
            }
        }

        private static int GetLegacyInstanceId(UnityEngine.Object obj)
        {
            try
            {
                var value = GetInstanceIdMethod?.Invoke(obj, null);
                return value is int id ? id : 0;
            }
            catch
            {
                return 0;
            }
        }

        private static void PingObject(UnityEngine.Object obj)
        {
            try
            {
                PingObjectMethod?.Invoke(null, new object[] { obj });
            }
            catch (Exception ex)
            {
                BridgeLogger.LogWarning($"PingObject failed: {ex.Message}");
            }
        }

        private static string GetGlobalObjectId(UnityEngine.Object obj)
        {
            try
            {
                return GlobalObjectId.GetGlobalObjectIdSlow(obj).ToString();
            }
            catch
            {
                return "";
            }
        }

        private static Type FindType(string fullName)
        {
            foreach (var assembly in AppDomain.CurrentDomain.GetAssemblies())
            {
                var type = assembly.GetType(fullName);
                if (type != null) return type;
            }
            return null;
        }

        private static MethodInfo FindEntityIdToObject(Type entityIdType)
        {
            if (entityIdType == null) return null;
            return typeof(EditorUtility).GetMethod(
                "EntityIdToObject",
                BindingFlags.Public | BindingFlags.Static,
                null,
                new[] { entityIdType },
                null);
        }

        private static object ConvertToEntityId(Type entityIdType, string entityId)
        {
            if (!int.TryParse(entityId, out var legacyValue)) return null;
            var op = entityIdType.GetMethod(
                "op_Implicit",
                BindingFlags.Public | BindingFlags.Static,
                null,
                new[] { typeof(int) },
                null);
            return op?.Invoke(null, new object[] { legacyValue });
        }

        private static GameObject FindGameObjectByPath(string path)
        {
            for (int i = 0; i < SceneManager.sceneCount; i++)
            {
                var scene = SceneManager.GetSceneAt(i);
                if (!scene.isLoaded) continue;

                var found = FindInRoots(scene.GetRootGameObjects(), path);
                if (found != null) return found;
            }
            return null;
        }

        private static GameObject FindInRoots(GameObject[] roots, string path)
        {
            var parts = path.Split('/');
            foreach (var root in roots)
            {
                if (root.name != parts[0]) continue;
                var current = root;
                for (int i = 1; i < parts.Length && current != null; i++)
                {
                    var child = current.transform.Find(parts[i]);
                    current = child == null ? null : child.gameObject;
                }
                if (current != null) return current;
            }
            return null;
        }

        private static GameObject AsGameObject(UnityEngine.Object obj)
        {
            if (obj is GameObject go)
                return go;
            if (obj is Component component)
                return component.gameObject;
            return null;
        }

        private static string GetHierarchyPath(GameObject go)
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

        private static BridgeResponse Success(
            BridgeCommand command,
            ObjectIdentityResult result)
        {
            return BridgeResponse.Success(
                command.commandId,
                command.commandType,
                JsonUtility.ToJson(result));
        }

        private static BridgeResponse Error(
            BridgeCommand command,
            string operation,
            string message)
        {
            var result = new ObjectIdentityResult
            {
                success = false,
                operation = operation,
                count = 0,
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

#pragma warning disable 0649
        [Serializable]
        private class ObjectIdentityParams
        {
            public string operation = "get-selection";
            public string gameObjectPath;
            public string assetPath;
            public string globalObjectId;
            public string entityId;
            public int instanceId;
        }
#pragma warning restore 0649

        [Serializable]
        private class ObjectIdentityResult
        {
            public bool success;
            public string operation;
            public List<ObjectIdentityInfo> objects = new List<ObjectIdentityInfo>();
            public int count;
            public string message;
        }

        [Serializable]
        private class ObjectIdentityInfo
        {
            public string name;
            public string type;
            public int instanceId;
            public string entityId;
            public string globalObjectId;
            public string assetPath;
            public string scenePath;
            public string hierarchyPath;
            public bool isAsset;
            public bool isSceneObject;
            public bool isPersistent;
        }
    }
}
