using System;
using System.Linq;
using UnityEditor;
using UnityEngine;
using UnityEngine.SceneManagement;

namespace BWS.Editor.ClaudeCodeBridge
{
    /// <summary>
    /// Command handler for transform manipulation operations.
    ///
    /// PURPOSE:
    /// Provides dedicated transform control (position, rotation, scale, parenting)
    /// with proper Undo support. The most-used operation in Unity Editor automation.
    ///
    /// SUPPORTED OPERATIONS:
    /// 1. "get" - Read all transform data (position, rotation, scale, parent, sibling index)
    /// 2. "set" - Modify position, rotation, and/or scale with Undo support
    /// 3. "parent" - Reparent a GameObject under a new parent with Undo
    /// 4. "sibling-index" - Set hierarchy order within the current parent
    ///
    /// GUARDS:
    /// - EditorApplication.isCompiling: blocks mutating operations
    /// - EditorApplication.isPlaying: blocks mutating operations
    /// </summary>
    public class TransformCommandHandler : ICommandHandler
    {
        public string CommandType => "transform-operation";

        public BridgeResponse Execute(BridgeCommand command)
        {
            try
            {
                var parameters = JsonUtility.FromJson<TransformParams>(
                    command.parametersJson ?? "{}"
                );
                if (parameters == null)
                    parameters = new TransformParams();

                BridgeLogger.LogDebug($"Transform operation: {parameters.operation}");

                TransformResult result;
                switch (parameters.operation?.ToLower())
                {
                    case "get":
                        result = ExecuteGet(parameters);
                        break;
                    case "set":
                        result = ExecuteSet(parameters);
                        break;
                    case "parent":
                        result = ExecuteParent(parameters);
                        break;
                    case "sibling-index":
                        result = ExecuteSiblingIndex(parameters);
                        break;
                    default:
                        result = new TransformResult
                        {
                            success = false,
                            operation = parameters.operation,
                            message = $"Unknown operation: {parameters.operation}. "
                                + "Supported: get, set, parent, sibling-index"
                        };
                        break;
                }

                var resultJson = JsonUtility.ToJson(result);
                return BridgeResponse.Success(command.commandId, command.commandType, resultJson);
            }
            catch (Exception ex)
            {
                BridgeLogger.LogError($"Transform error: {ex}");
                return BridgeResponse.Error(command.commandId, command.commandType, ex.ToString());
            }
        }

        private TransformResult ExecuteGet(TransformParams parameters)
        {
            var go = FindGameObjectByPath(parameters.gameObjectPath);
            if (go == null)
            {
                return new TransformResult
                {
                    success = false,
                    operation = "get",
                    message = $"GameObject not found: {parameters.gameObjectPath}"
                };
            }

            return BuildTransformResult("get", go);
        }

        private TransformResult ExecuteSet(TransformParams parameters)
        {
            if (!CheckMutationGuards(out string guardMsg))
                return ErrorResult("set", guardMsg);

            var go = FindGameObjectByPath(parameters.gameObjectPath);
            if (go == null)
                return ErrorResult("set", $"GameObject not found: {parameters.gameObjectPath}");

            var t = go.transform;
            Undo.RecordObject(t, "Transform Set");

            ApplySetValues(t, parameters);

            EditorUtility.SetDirty(go);
            return BuildTransformResult("set", go, "Transform updated successfully");
        }

        private TransformResult ExecuteParent(TransformParams parameters)
        {
            if (!CheckMutationGuards(out string guardMsg))
                return ErrorResult("parent", guardMsg);

            var go = FindGameObjectByPath(parameters.gameObjectPath);
            if (go == null)
                return ErrorResult("parent", $"GameObject not found: {parameters.gameObjectPath}");

            Transform newParent = null;
            if (!string.IsNullOrEmpty(parameters.parentPath))
            {
                var parentGo = FindGameObjectByPath(parameters.parentPath);
                if (parentGo == null)
                    return ErrorResult("parent", $"Parent not found: {parameters.parentPath}");
                newParent = parentGo.transform;
            }

            Undo.SetTransformParent(
                go.transform,
                newParent,
                parameters.worldPositionStays,
                "Reparent"
            );

            EditorUtility.SetDirty(go);
            return BuildTransformResult("parent", go, "Reparented successfully");
        }

        private TransformResult ExecuteSiblingIndex(TransformParams parameters)
        {
            if (!CheckMutationGuards(out string guardMsg))
                return ErrorResult("sibling-index", guardMsg);

            var go = FindGameObjectByPath(parameters.gameObjectPath);
            if (go == null)
                return ErrorResult("sibling-index",
                    $"GameObject not found: {parameters.gameObjectPath}");

            Undo.RecordObject(go.transform, "Set Sibling Index");
            go.transform.SetSiblingIndex(parameters.siblingIndex);

            EditorUtility.SetDirty(go);
            return BuildTransformResult("sibling-index", go, "Sibling index updated");
        }

        // -----------------------------------------------------------------
        // Helpers
        // -----------------------------------------------------------------

        private void ApplySetValues(Transform t, TransformParams p)
        {
            if (p.position != null && p.position.isSet)
                t.position = new Vector3(p.position.x, p.position.y, p.position.z);

            if (p.localPosition != null && p.localPosition.isSet)
                t.localPosition = new Vector3(p.localPosition.x, p.localPosition.y,
                    p.localPosition.z);

            if (p.rotation != null && p.rotation.isSet)
            {
                if (p.useLocal)
                    t.localEulerAngles = new Vector3(p.rotation.x, p.rotation.y, p.rotation.z);
                else
                    t.eulerAngles = new Vector3(p.rotation.x, p.rotation.y, p.rotation.z);
            }

            if (p.scale != null && p.scale.isSet)
                t.localScale = new Vector3(p.scale.x, p.scale.y, p.scale.z);
        }

        private TransformResult BuildTransformResult(
            string operation, GameObject go, string message = null)
        {
            var t = go.transform;
            string parentPath = null;
            if (t.parent != null)
                parentPath = GetGameObjectPath(t.parent.gameObject);

            return new TransformResult
            {
                success = true,
                operation = operation,
                gameObjectPath = GetGameObjectPath(go),
                position = SerializableVector3Data.FromVector3(t.position),
                localPosition = SerializableVector3Data.FromVector3(t.localPosition),
                rotation = SerializableVector3Data.FromVector3(t.eulerAngles),
                localEulerAngles = SerializableVector3Data.FromVector3(t.localEulerAngles),
                localScale = SerializableVector3Data.FromVector3(t.localScale),
                parentPath = parentPath,
                siblingIndex = t.GetSiblingIndex(),
                message = message ?? $"Transform {operation} completed"
            };
        }

        private TransformResult ErrorResult(string operation, string message)
        {
            return new TransformResult
            {
                success = false,
                operation = operation,
                message = message
            };
        }

        private bool CheckMutationGuards(out string message)
        {
            if (EditorApplication.isCompiling)
            {
                message = "Cannot modify transforms while scripts are compiling.";
                return false;
            }
            if (EditorApplication.isPlaying)
            {
                message = "Cannot modify transforms in play mode.";
                return false;
            }
            message = null;
            return true;
        }

        private GameObject FindGameObjectByPath(string path)
        {
            if (string.IsNullOrEmpty(path))
                return null;

            var parts = path.Split('/');
            var rootObjects = SceneManager.GetActiveScene().GetRootGameObjects();
            var current = rootObjects.FirstOrDefault(go => go.name == parts[0]);
            if (current == null)
                return null;

            for (int i = 1; i < parts.Length; i++)
            {
                var child = current.transform.Find(parts[i]);
                if (child == null) return null;
                current = child.gameObject;
            }
            return current;
        }

        private string GetGameObjectPath(GameObject go)
        {
            string path = go.name;
            Transform t = go.transform.parent;
            while (t != null)
            {
                path = t.name + "/" + path;
                t = t.parent;
            }
            return path;
        }
    }
}
