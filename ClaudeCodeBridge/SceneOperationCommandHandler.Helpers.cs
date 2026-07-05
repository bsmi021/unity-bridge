using System;
using System.Linq;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.SceneManagement;

namespace BWS.Editor.ClaudeCodeBridge
{
    public partial class SceneOperationCommandHandler
    {
        /// <summary>
        /// Resolve OpenSceneMode from string parameter.
        /// </summary>
        private OpenSceneMode ResolveOpenMode(string mode)
        {
            switch (mode?.ToLower())
            {
                case "additive": return OpenSceneMode.Additive;
                case "additive-without-loading": return OpenSceneMode.AdditiveWithoutLoading;
                default: return OpenSceneMode.Single;
            }
        }

        /// <summary>
        /// Unload a scene from the Editor (for multi-scene editing).
        /// </summary>
        private SceneOperationResult UnloadScene(SceneOperationParams parameters)
        {
            var result = new SceneOperationResult { operation = "unload" };

            if (string.IsNullOrEmpty(parameters.scenePath))
            {
                result.success = false;
                result.message = "scenePath is required for unload operation";
                return result;
            }

            try
            {
                var scene = SceneManager.GetSceneByPath(parameters.scenePath);
                if (!scene.IsValid() || !scene.isLoaded)
                {
                    result.success = false;
                    result.message = $"Scene not loaded: {parameters.scenePath}";
                    return result;
                }

                if (SceneManager.sceneCount <= 1)
                {
                    result.success = false;
                    result.message = "Cannot unload the only loaded scene";
                    return result;
                }

                bool closed = EditorSceneManager.CloseScene(scene, parameters.removeScene);
                result.success = closed;
                result.message = closed
                    ? $"Unloaded scene: {parameters.scenePath}"
                    : $"Failed to unload scene: {parameters.scenePath}";
                result.currentScenePath = SceneManager.GetActiveScene().path;
                BridgeLogger.LogInfo(result.message);
            }
            catch (Exception ex)
            {
                result.success = false;
                result.message = $"Failed to unload scene: {ex.Message}";
            }

            return result;
        }

        /// <summary>
        /// Set the active scene (when multiple scenes are loaded).
        /// </summary>
        private SceneOperationResult SetActiveScene(SceneOperationParams parameters)
        {
            var result = new SceneOperationResult { operation = "set-active" };

            if (string.IsNullOrEmpty(parameters.scenePath))
            {
                result.success = false;
                result.message = "scenePath is required for set-active operation";
                return result;
            }

            try
            {
                var scene = SceneManager.GetSceneByPath(parameters.scenePath);
                if (!scene.IsValid() || !scene.isLoaded)
                {
                    result.success = false;
                    result.message = $"Scene not loaded: {parameters.scenePath}";
                    return result;
                }

                bool set = SceneManager.SetActiveScene(scene);
                result.success = set;
                result.currentScenePath = parameters.scenePath;
                result.message = set
                    ? $"Active scene set to: {parameters.scenePath}"
                    : $"Failed to set active scene: {parameters.scenePath}";
                BridgeLogger.LogInfo(result.message);
            }
            catch (Exception ex)
            {
                result.success = false;
                result.message = $"Failed to set active scene: {ex.Message}";
            }

            return result;
        }

        private SceneOperationResult MoveObjectToScene(SceneOperationParams parameters)
        {
            var result = new SceneOperationResult { operation = "move-object" };
            if (string.IsNullOrEmpty(parameters.gameObjectPath))
            {
                result.success = false;
                result.message = "gameObjectPath is required for move-object";
                return result;
            }
            if (string.IsNullOrEmpty(parameters.scenePath))
            {
                result.success = false;
                result.message = "scenePath is required for move-object";
                return result;
            }
            try
            {
                GameObject target = FindGameObjectAcrossScenes(parameters.gameObjectPath);
                if (target == null)
                {
                    result.success = false;
                    result.message = $"GameObject not found: {parameters.gameObjectPath}";
                    return result;
                }
                if (target.transform.parent != null)
                {
                    result.success = false;
                    result.message = "Only root GameObjects can be moved between scenes.";
                    return result;
                }
                var targetScene = SceneManager.GetSceneByPath(parameters.scenePath);
                if (!targetScene.IsValid() || !targetScene.isLoaded)
                {
                    result.success = false;
                    result.message = $"Target scene not loaded: {parameters.scenePath}";
                    return result;
                }
                Undo.RecordObject(target, "Move GameObject To Scene");
                SceneManager.MoveGameObjectToScene(target, targetScene);
                EditorUtility.SetDirty(target);
                EditorSceneManager.MarkSceneDirty(targetScene);
                result.success = true;
                result.currentScenePath = targetScene.path;
                result.message = $"Moved '{parameters.gameObjectPath}' to {parameters.scenePath}";
                BridgeLogger.LogInfo(result.message);
            }
            catch (Exception ex)
            {
                result.success = false;
                result.message = $"Failed to move object: {ex.Message}";
            }
            return result;
        }

        private GameObject FindGameObjectAcrossScenes(string path)
        {
            var parts = path.Split('/');
            for (int s = 0; s < SceneManager.sceneCount; s++)
            {
                var scene = SceneManager.GetSceneAt(s);
                if (!scene.isLoaded) continue;
                var roots = scene.GetRootGameObjects();
                var current = roots.FirstOrDefault(go => go.name == parts[0]);
                if (current == null) continue;
                bool found = true;
                for (int i = 1; i < parts.Length; i++)
                {
                    var child = current.transform.Find(parts[i]);
                    if (child == null) { found = false; break; }
                    current = child.gameObject;
                }
                if (found) return current;
            }
            return null;
        }
    }
}
