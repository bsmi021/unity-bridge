using System;
using System.Collections.Generic;
using System.IO;
using UnityEditor;
using UnityEngine;
using UnityEngine.SceneManagement;
using UnityEngine.UIElements;

namespace BWS.Editor.ClaudeCodeBridge
{
    /// <summary>
    /// Command handler for Unity UI Toolkit authoring and inspection.
    /// </summary>
    public class UIToolkitCommandHandler : ICommandHandler
    {
        public string CommandType => "ui-toolkit";

        public BridgeResponse Execute(BridgeCommand command)
        {
            try
            {
                var p = JsonUtility.FromJson<UIToolkitParams>(
                    command.parametersJson ?? "{}") ?? new UIToolkitParams();
                var operation = string.IsNullOrEmpty(p.operation)
                    ? "list-documents"
                    : p.operation.ToLower();

                switch (operation)
                {
                    case "list-documents":
                        return HandleListDocuments(command);
                    case "inspect-uxml":
                        return HandleInspectUxml(command, p);
                    case "inspect-uss":
                        return HandleInspectUss(command, p);
                    case "create-uxml":
                        return HandleCreateUxml(command, p);
                    case "create-panel-settings":
                        return HandleCreatePanelSettings(command, p);
                    case "add-ui-document":
                        return HandleAddUIDocument(command, p, HasField(command, "sortingOrder"));
                    default:
                        return Error(command, operation, "Unknown operation. Supported: " +
                            "list-documents, inspect-uxml, inspect-uss, create-uxml, " +
                            "create-panel-settings, add-ui-document");
                }
            }
            catch (Exception ex)
            {
                BridgeLogger.LogError($"UI Toolkit error: {ex}");
                return Error(command, "ui-toolkit", ex.ToString());
            }
        }

        private BridgeResponse HandleListDocuments(BridgeCommand command)
        {
            var documents = new List<UIDocumentInfo>();
            for (int i = 0; i < SceneManager.sceneCount; i++)
            {
                var scene = SceneManager.GetSceneAt(i);
                if (!scene.isLoaded) continue;

                foreach (var root in scene.GetRootGameObjects())
                {
                    foreach (var document in root.GetComponentsInChildren<UIDocument>(true))
                        documents.Add(BuildDocumentInfo(document));
                }
            }

            return Success(command, new UIToolkitResult
            {
                success = true,
                operation = "list-documents",
                documents = documents,
                message = $"Found {documents.Count} UI Document component(s)."
            });
        }

        private BridgeResponse HandleInspectUxml(
            BridgeCommand command, UIToolkitParams parameters)
        {
            var assetPath = CoalescePath(parameters.assetPath, parameters.uxmlPath);
            if (string.IsNullOrEmpty(assetPath))
                return Error(command, "inspect-uxml", "assetPath or uxmlPath is required.");

            var asset = AssetDatabase.LoadAssetAtPath<VisualTreeAsset>(assetPath);
            if (asset == null)
                return Error(command, "inspect-uxml",
                    $"VisualTreeAsset not found: {assetPath}", assetPath);

            var root = asset.CloneTree();
            int maxDepth = parameters.maxDepth <= 0 ? 3 : Math.Min(parameters.maxDepth, 25);
            return Success(command, new UIToolkitResult
            {
                success = true,
                operation = "inspect-uxml",
                assetPath = assetPath,
                tree = BuildTree(root, 0, maxDepth),
                message = $"Inspected UXML asset: {assetPath}"
            });
        }

        private BridgeResponse HandleInspectUss(
            BridgeCommand command, UIToolkitParams parameters)
        {
            var assetPath = CoalescePath(parameters.assetPath, parameters.ussPath);
            if (string.IsNullOrEmpty(assetPath))
                return Error(command, "inspect-uss", "assetPath or ussPath is required.");
            if (AssetDatabase.LoadAssetAtPath<StyleSheet>(assetPath) == null)
                return Error(command, "inspect-uss",
                    $"StyleSheet asset not found: {assetPath}", assetPath);

            var fullPath = ToFullPath(assetPath);
            if (!File.Exists(fullPath))
                return Error(command, "inspect-uss",
                    $"USS file not found on disk: {assetPath}", assetPath);

            var text = File.ReadAllText(fullPath);
            return Success(command, new UIToolkitResult
            {
                success = true,
                operation = "inspect-uss",
                assetPath = assetPath,
                sizeBytes = new FileInfo(fullPath).Length,
                ruleCount = CountStyleRules(text),
                message = $"Inspected USS asset: {assetPath}"
            });
        }

        private BridgeResponse HandleCreateUxml(
            BridgeCommand command, UIToolkitParams parameters)
        {
            if (string.IsNullOrEmpty(parameters.assetPath))
                return Error(command, "create-uxml", "assetPath is required.");
            if (!CanWriteAsset(parameters.assetPath, parameters.overwrite, out var message))
                return Error(command, "create-uxml", message, parameters.assetPath);

            var fullPath = ToFullPath(parameters.assetPath);
            EnsureDirectory(parameters.assetPath);
            File.WriteAllText(fullPath, MinimalUxml());
            AssetDatabase.ImportAsset(parameters.assetPath);
            AssetDatabase.Refresh();

            return Success(command, new UIToolkitResult
            {
                success = true,
                operation = "create-uxml",
                assetPath = parameters.assetPath,
                message = $"Created UXML asset: {parameters.assetPath}"
            });
        }

        private BridgeResponse HandleCreatePanelSettings(
            BridgeCommand command, UIToolkitParams parameters)
        {
            if (string.IsNullOrEmpty(parameters.assetPath))
                return Error(command, "create-panel-settings", "assetPath is required.");
            if (!CanWriteAsset(parameters.assetPath, parameters.overwrite, out var message))
                return Error(command, "create-panel-settings", message, parameters.assetPath);

            if (parameters.overwrite)
                AssetDatabase.DeleteAsset(parameters.assetPath);

            EnsureDirectory(parameters.assetPath);
            var panelSettings = ScriptableObject.CreateInstance<PanelSettings>();
            AssetDatabase.CreateAsset(panelSettings, parameters.assetPath);
            AssetDatabase.SaveAssets();
            AssetDatabase.ImportAsset(parameters.assetPath);
            AssetDatabase.Refresh();

            return Success(command, new UIToolkitResult
            {
                success = true,
                operation = "create-panel-settings",
                assetPath = parameters.assetPath,
                message = $"Created PanelSettings asset: {parameters.assetPath}"
            });
        }

        private BridgeResponse HandleAddUIDocument(
            BridgeCommand command, UIToolkitParams p, bool hasSortingOrder)
        {
            if (string.IsNullOrEmpty(p.gameObjectPath))
                return Error(command, "add-ui-document", "gameObjectPath is required.");

            var go = FindGameObjectByPath(p.gameObjectPath);
            if (go == null)
                return Error(command, "add-ui-document",
                    $"GameObject not found: {p.gameObjectPath}");

            if (!ResolveDocumentAssets(p, out var uxml, out var panel, out var error))
                return Error(command, "add-ui-document", error);

            var document = go.GetComponent<UIDocument>();
            if (document == null)
                document = Undo.AddComponent<UIDocument>(go);
            else
                Undo.RecordObject(document, "Configure UI Document");

            AssignAssets(document, uxml, panel, p.sortingOrder, hasSortingOrder);

            EditorUtility.SetDirty(document);
            return Success(command, new UIToolkitResult
            {
                success = true,
                operation = "add-ui-document",
                documents = new List<UIDocumentInfo> { BuildDocumentInfo(document) },
                message = $"Configured UIDocument on {p.gameObjectPath}."
            });
        }

        private static bool ResolveDocumentAssets(
            UIToolkitParams p,
            out VisualTreeAsset uxml,
            out PanelSettings panel,
            out string error)
        {
            uxml = null;
            panel = null;
            error = null;
            if (!string.IsNullOrEmpty(p.uxmlPath))
            {
                uxml = AssetDatabase.LoadAssetAtPath<VisualTreeAsset>(p.uxmlPath);
                if (uxml == null)
                {
                    error = $"VisualTreeAsset not found: {p.uxmlPath}";
                    return false;
                }
            }
            if (!string.IsNullOrEmpty(p.panelSettingsPath))
            {
                panel = AssetDatabase.LoadAssetAtPath<PanelSettings>(p.panelSettingsPath);
                if (panel == null)
                {
                    error = $"PanelSettings not found: {p.panelSettingsPath}";
                    return false;
                }
            }
            return true;
        }

        private static void AssignAssets(
            UIDocument document,
            VisualTreeAsset uxml,
            PanelSettings panel,
            int sortingOrder,
            bool hasSortingOrder)
        {
            if (uxml != null) document.visualTreeAsset = uxml;
            if (panel != null) document.panelSettings = panel;
            if (hasSortingOrder) document.sortingOrder = sortingOrder;
        }

        private static UIDocumentInfo BuildDocumentInfo(UIDocument document)
        {
            return new UIDocumentInfo
            {
                name = document.name,
                gameObjectPath = GetHierarchyPath(document.gameObject),
                scenePath = document.gameObject.scene.path,
                uxmlPath = AssetDatabase.GetAssetPath(document.visualTreeAsset),
                panelSettingsPath = AssetDatabase.GetAssetPath(document.panelSettings),
                sortingOrder = document.sortingOrder,
                enabled = document.enabled
            };
        }

        private static UIToolkitTreeNode BuildTree(
            VisualElement element, int depth, int maxDepth)
        {
            var node = new UIToolkitTreeNode
            {
                name = element.name,
                type = element.GetType().FullName,
                classList = new List<string>(element.GetClasses()),
                childCount = element.childCount
            };
            if (depth >= maxDepth) return node;

            foreach (var child in element.Children())
                node.children.Add(BuildTree(child, depth + 1, maxDepth));
            return node;
        }

        private static int CountStyleRules(string text)
        {
            int count = 0;
            foreach (var ch in text)
            {
                if (ch == '{')
                    count++;
            }
            return count;
        }

        private static bool CanWriteAsset(
            string assetPath, bool overwrite, out string message)
        {
            if (!assetPath.StartsWith("Assets/", StringComparison.Ordinal))
            {
                message = $"assetPath must be under Assets/: {assetPath}";
                return false;
            }
            if (!overwrite && File.Exists(ToFullPath(assetPath)))
            {
                message = $"Asset already exists: {assetPath}";
                return false;
            }
            message = null;
            return true;
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

        private static void EnsureDirectory(string assetPath)
        {
            var dir = Path.GetDirectoryName(ToFullPath(assetPath));
            if (!string.IsNullOrEmpty(dir) && !Directory.Exists(dir))
                Directory.CreateDirectory(dir);
        }

        private static string ToFullPath(string assetPath)
        {
            var projectRoot = Directory.GetParent(Application.dataPath).FullName;
            return Path.Combine(projectRoot, assetPath.Replace('/', Path.DirectorySeparatorChar));
        }

        private static string MinimalUxml()
        {
            return "<?xml version=\"1.0\" encoding=\"utf-8\"?>\n" +
                "<ui:UXML xmlns:ui=\"UnityEngine.UIElements\">\n" +
                "  <ui:VisualElement name=\"root\" />\n" +
                "</ui:UXML>\n";
        }

        private static bool HasField(BridgeCommand command, string fieldName)
        {
            return (command.parametersJson ?? "{}").Contains($"\"{fieldName}\"");
        }

        private static string CoalescePath(string first, string second)
        {
            return string.IsNullOrEmpty(first) ? second : first;
        }

        private static BridgeResponse Success(
            BridgeCommand command, UIToolkitResult result)
        {
            return BridgeResponse.Success(
                command.commandId, command.commandType, JsonUtility.ToJson(result));
        }

        private static BridgeResponse Error(
            BridgeCommand command, string operation, string message, string assetPath = "")
        {
            var result = new UIToolkitResult
            {
                success = false,
                operation = operation,
                assetPath = assetPath,
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
        private class UIToolkitParams
        {
            public string operation = "list-documents";
            public string assetPath;
            public string gameObjectPath;
            public string uxmlPath;
            public string ussPath;
            public string panelSettingsPath;
            public int sortingOrder;
            public int maxDepth;
            public bool overwrite;
        }
#pragma warning restore 0649

        [Serializable]
        private class UIToolkitResult
        {
            public bool success;
            public string operation;
            public List<UIDocumentInfo> documents = new List<UIDocumentInfo>();
            public UIToolkitTreeNode tree;
            public string assetPath;
            public long sizeBytes;
            public int ruleCount;
            public string message;
        }

        [Serializable]
        private class UIDocumentInfo
        {
            public string name;
            public string gameObjectPath;
            public string scenePath;
            public string uxmlPath;
            public string panelSettingsPath;
            public float sortingOrder;
            public bool enabled;
        }

        [Serializable]
        private class UIToolkitTreeNode
        {
            public string name;
            public string type;
            public List<string> classList = new List<string>();
            public int childCount;
            public List<UIToolkitTreeNode> children = new List<UIToolkitTreeNode>();
        }
    }
}
