using System.Collections.Generic;
using System.Linq;
using UnityEditor;
using UnityEngine;
using UnityEngine.SceneManagement;

namespace BWS.Editor.ClaudeCodeBridge
{
    /// <summary>
    /// Helper methods for PrefabOperationCommandHandler (partial class).
    /// </summary>
    public partial class PrefabOperationCommandHandler
    {
        /// <summary>
        /// Find a GameObject in the scene by hierarchy path or simple name.
        /// </summary>
        private GameObject FindGameObject(string path)
        {
            if (string.IsNullOrEmpty(path))
                return null;

            var allObjects = SceneManager.GetActiveScene().GetRootGameObjects();

            if (path.Contains("/"))
            {
                var parts = path.Split('/');
                Transform current = null;

                foreach (var root in allObjects)
                {
                    if (root.name == parts[0])
                    {
                        current = root.transform;
                        break;
                    }
                }

                if (current == null)
                    return null;

                for (int i = 1; i < parts.Length; i++)
                {
                    current = current.Find(parts[i]);
                    if (current == null)
                        return null;
                }

                return current.gameObject;
            }
            else
            {
                foreach (var root in allObjects)
                {
                    if (root.name == path)
                        return root;

                    var found = root.transform.Find(path);
                    if (found != null)
                        return found.gameObject;

                    var foundDeep = FindGameObjectRecursive(root.transform, path);
                    if (foundDeep != null)
                        return foundDeep;
                }
            }

            return null;
        }

        private GameObject FindGameObjectRecursive(Transform parent, string name)
        {
            foreach (Transform child in parent)
            {
                if (child.name == name)
                    return child.gameObject;

                var found = FindGameObjectRecursive(child, name);
                if (found != null)
                    return found;
            }
            return null;
        }

        /// <summary>
        /// Destroy an instantiated prefab root without deleting its source asset.
        /// </summary>
        private PrefabOperationResult DestroyPrefabInstance(PrefabOperationParams parameters)
        {
            var result = new PrefabOperationResult { operation = "destroy" };
            if (string.IsNullOrEmpty(parameters.gameObjectPath))
            {
                result.message = "gameObjectPath is required for destroy operation.";
                return result;
            }

            var gameObject = FindGameObject(parameters.gameObjectPath);
            if (gameObject == null)
            {
                result.message = $"GameObject not found: {parameters.gameObjectPath}";
                return result;
            }

            if (!PrefabUtility.IsPartOfPrefabInstance(gameObject))
            {
                result.message = $"GameObject is not a prefab instance: {parameters.gameObjectPath}";
                return result;
            }

            var root = PrefabUtility.GetOutermostPrefabInstanceRoot(gameObject);
            result.gameObjectPath = GetGameObjectPath(root);
            result.prefabPath = AssetDatabase.GetAssetPath(
                PrefabUtility.GetCorrespondingObjectFromSource(root));
            Undo.DestroyObjectImmediate(root);
            result.success = true;
            result.message = $"Destroyed prefab instance: {result.gameObjectPath}";
            return result;
        }

        /// <summary>
        /// Get the full hierarchy path of a GameObject.
        /// </summary>
        private string GetGameObjectPath(GameObject obj)
        {
            if (obj == null)
                return string.Empty;

            var path = obj.name;
            var parent = obj.transform.parent;

            while (parent != null)
            {
                path = parent.name + "/" + path;
                parent = parent.parent;
            }
            return path;
        }

        /// <summary>
        /// Get human-readable descriptions of prefab instance modifications.
        /// </summary>
        private List<string> GetPrefabModifications(GameObject prefabRoot)
        {
            var modifications = new List<string>();
            if (prefabRoot == null)
                return modifications;

            var propertyMods = PrefabUtility.GetPropertyModifications(prefabRoot);
            if (propertyMods != null && propertyMods.Length > 0)
            {
                var grouped = propertyMods
                    .Where(m => m.target != null)
                    .GroupBy(m => m.target.name)
                    .Take(10);

                foreach (var group in grouped)
                {
                    modifications.Add($"{group.Key}: {group.Count()} property change(s)");
                }

                if (propertyMods.Length > 10)
                {
                    modifications.Add($"... and {propertyMods.Length - 10} more modification(s)");
                }
            }

            var addedComponents = PrefabUtility.GetAddedComponents(prefabRoot);
            if (addedComponents != null && addedComponents.Count > 0)
                modifications.Add($"{addedComponents.Count} added component(s)");

            var removedComponents = PrefabUtility.GetRemovedComponents(prefabRoot);
            if (removedComponents != null && removedComponents.Count > 0)
                modifications.Add($"{removedComponents.Count} removed component(s)");

            var addedObjects = PrefabUtility.GetAddedGameObjects(prefabRoot);
            if (addedObjects != null && addedObjects.Count > 0)
                modifications.Add($"{addedObjects.Count} added GameObject(s)");

            return modifications;
        }
    }
}
