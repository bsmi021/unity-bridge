using System;
using System.Collections.Generic;
using System.Linq;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.SceneManagement;

namespace BWS.Editor.ClaudeCodeBridge
{
    public static class BridgeSceneModalRecovery
    {
        private static readonly HashSet<string> DefaultRootNames = new HashSet<string>
        {
            "Main Camera",
            "Directional Light"
        };

        public static bool PrepareForAutomation(string context, out string message)
        {
            if (!TryDiscardUnsavedBlankScenes(context, out message))
                return false;

            var blockers = FindBlockingModifiedScenes();
            if (blockers.Count == 0)
            {
                message = "";
                return true;
            }

            message = "Refusing to trigger Unity save modal before " + context
                + ". Save or discard these scene changes manually: "
                + string.Join(", ", blockers);
            BridgeLogger.LogWarning(message);
            return false;
        }

        public static bool PrepareForExplicitSave(string context, out string message)
        {
            if (!TryDiscardUnsavedBlankScenes(context, out message))
                return false;

            var blockers = FindUntitledSaveBlockers();
            if (blockers.Count == 0)
            {
                message = "";
                return true;
            }

            message = "Refusing to trigger Unity save modal before " + context
                + ". Save or discard these untitled scene changes manually: "
                + string.Join(", ", blockers);
            BridgeLogger.LogWarning(message);
            return false;
        }

        public static string DiscardUnsavedBlankScenes(string context)
        {
            TryDiscardUnsavedBlankScenes(context, out var message);
            return message;
        }

        private static bool TryDiscardUnsavedBlankScenes(string context, out string message)
        {
            try
            {
                var blankScenes = LoadedScenes()
                    .Where(IsUntitledBlankScene)
                    .ToList();
                if (blankScenes.Count == 0)
                {
                    message = "";
                    return true;
                }

                var failures = new List<string>();
                if (blankScenes.Count == SceneManager.sceneCount)
                {
                    EditorSceneManager.NewScene(
                        NewSceneSetup.DefaultGameObjects,
                        NewSceneMode.Single);
                }
                else
                {
                    failures.AddRange(CloseBlankScenes(blankScenes));
                }

                if (failures.Count > 0)
                {
                    message = "Failed to discard blank untitled scene(s) before " + context
                        + ": " + string.Join(", ", failures);
                    BridgeLogger.LogWarning(message);
                    return false;
                }

                message = $"Discarded {blankScenes.Count} blank untitled scene(s) before {context}.";
                BridgeLogger.LogInfo(message);
                return true;
            }
            catch (Exception ex)
            {
                message = $"Scene modal recovery failed before {context}: {ex.Message}";
                BridgeLogger.LogWarning(message);
                return false;
            }
        }

        private static List<string> CloseBlankScenes(List<Scene> blankScenes)
        {
            var failures = new List<string>();
            var fallback = LoadedScenes()
                .FirstOrDefault(scene => !blankScenes.Contains(scene));
            if (fallback.IsValid())
                SceneManager.SetActiveScene(fallback);

            foreach (var scene in blankScenes)
            {
                if (!scene.IsValid() || !scene.isLoaded)
                    continue;
                if (!EditorSceneManager.CloseScene(scene, true))
                    failures.Add(SceneLabel(scene));
            }

            return failures;
        }

        private static List<string> FindBlockingModifiedScenes()
        {
            return LoadedScenes()
                .Where(scene => IsBlockingScene(scene))
                .Select(SceneLabel)
                .ToList();
        }

        private static List<string> FindUntitledSaveBlockers()
        {
            return LoadedScenes()
                .Where(scene => string.IsNullOrEmpty(scene.path) && !IsUntitledBlankScene(scene))
                .Select(SceneLabel)
                .ToList();
        }

        private static bool IsBlockingScene(Scene scene)
        {
            if (IsUntitledBlankScene(scene))
                return false;
            return scene.isDirty || string.IsNullOrEmpty(scene.path);
        }

        private static bool IsUntitledBlankScene(Scene scene)
        {
            if (!scene.IsValid() || !scene.isLoaded || !string.IsNullOrEmpty(scene.path))
                return false;

            var roots = scene.GetRootGameObjects();
            if (roots.Length == 0)
                return true;
            if (roots.Length > DefaultRootNames.Count)
                return false;

            return roots.All(IsCleanDefaultRoot);
        }

        private static bool IsCleanDefaultRoot(GameObject root)
        {
            if (root == null || !DefaultRootNames.Contains(root.name))
                return false;
            if (EditorUtility.IsDirty(root))
                return false;

            foreach (var component in root.GetComponents<Component>())
            {
                if (component != null && EditorUtility.IsDirty(component))
                    return false;
            }

            return true;
        }

        private static IEnumerable<Scene> LoadedScenes()
        {
            for (int i = 0; i < SceneManager.sceneCount; i++)
            {
                var scene = SceneManager.GetSceneAt(i);
                if (scene.isLoaded)
                    yield return scene;
            }
        }

        private static string SceneLabel(Scene scene)
        {
            if (!string.IsNullOrEmpty(scene.path))
                return scene.path;
            if (!string.IsNullOrEmpty(scene.name))
                return scene.name;
            return "<untitled>";
        }
    }
}
