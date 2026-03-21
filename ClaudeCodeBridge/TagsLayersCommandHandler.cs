using System;
using System.Collections.Generic;
using UnityEditor;
using UnityEngine;

namespace BWS.Editor.ClaudeCodeBridge
{
    /// <summary>
    /// Command handler for tags and layers management.
    ///
    /// SUPPORTED OPERATIONS:
    /// 1. "list-tags" - List all project tags
    /// 2. "add-tag" - Add a custom tag
    /// 3. "list-layers" - List all layers (0-31)
    /// 4. "add-layer" - Add a layer to a user slot
    /// 5. "list-sorting-layers" - List all sorting layers
    /// 6. "add-sorting-layer" - Add a sorting layer
    ///
    /// Uses SerializedObject on TagManager.asset for reliable access.
    ///
    /// GUARDS:
    /// - EditorApplication.isCompiling: blocks all operations
    /// - EditorApplication.isPlaying: blocks mutating operations
    /// </summary>
    public class TagsLayersCommandHandler : ICommandHandler
    {
        public string CommandType => "tags-layers";

        private const string TAG_MANAGER_PATH = "ProjectSettings/TagManager.asset";

        public BridgeResponse Execute(BridgeCommand command)
        {
            try
            {
                if (EditorApplication.isCompiling)
                {
                    return BridgeResponse.Error(command.commandId, command.commandType,
                        "Cannot access tags/layers while scripts are compiling.");
                }

                var parameters = JsonUtility.FromJson<TagsLayersParams>(
                    command.parametersJson ?? "{}");
                if (parameters == null)
                    parameters = new TagsLayersParams();

                TagsLayersResult result;
                switch (parameters.operation?.ToLower())
                {
                    case "list-tags":
                        result = ExecuteListTags();
                        break;
                    case "add-tag":
                        result = ExecuteAddTag(parameters);
                        break;
                    case "list-layers":
                        result = ExecuteListLayers();
                        break;
                    case "add-layer":
                        result = ExecuteAddLayer(parameters);
                        break;
                    case "list-sorting-layers":
                        result = ExecuteListSortingLayers();
                        break;
                    case "add-sorting-layer":
                        result = ExecuteAddSortingLayer(parameters);
                        break;
                    default:
                        result = new TagsLayersResult
                        {
                            success = false,
                            operation = parameters.operation,
                            message = $"Unknown operation: {parameters.operation}. "
                                + "Supported: list-tags, add-tag, list-layers, add-layer, "
                                + "list-sorting-layers, add-sorting-layer"
                        };
                        break;
                }

                var resultJson = JsonUtility.ToJson(result);
                return BridgeResponse.Success(command.commandId, command.commandType, resultJson);
            }
            catch (Exception ex)
            {
                BridgeLogger.LogError($"TagsLayers error: {ex}");
                return BridgeResponse.Error(command.commandId, command.commandType, ex.ToString());
            }
        }

        private TagsLayersResult ExecuteListTags()
        {
            var result = new TagsLayersResult
            {
                success = true,
                operation = "list-tags"
            };

            foreach (var tag in UnityEditorInternal.InternalEditorUtility.tags)
                result.tags.Add(tag);

            result.message = $"Found {result.tags.Count} tags";
            return result;
        }

        private TagsLayersResult ExecuteAddTag(TagsLayersParams p)
        {
            if (!CheckMutationGuards(out string guardMsg))
                return ErrorResult("add-tag", guardMsg);

            if (string.IsNullOrEmpty(p.tagName))
                return ErrorResult("add-tag", "tagName is required");

            // Check if tag already exists
            foreach (var existing in UnityEditorInternal.InternalEditorUtility.tags)
            {
                if (existing == p.tagName)
                    return ErrorResult("add-tag", $"Tag '{p.tagName}' already exists");
            }

            var asset = AssetDatabase.LoadMainAssetAtPath(TAG_MANAGER_PATH);
            var so = new SerializedObject(asset);
            var tagsProp = so.FindProperty("tags");

            int newIndex = tagsProp.arraySize;
            tagsProp.InsertArrayElementAtIndex(newIndex);
            tagsProp.GetArrayElementAtIndex(newIndex).stringValue = p.tagName;
            so.ApplyModifiedProperties();

            return new TagsLayersResult
            {
                success = true,
                operation = "add-tag",
                message = $"Tag '{p.tagName}' added successfully"
            };
        }

        private TagsLayersResult ExecuteListLayers()
        {
            var result = new TagsLayersResult
            {
                success = true,
                operation = "list-layers"
            };

            for (int i = 0; i < 32; i++)
            {
                string name = LayerMask.LayerToName(i);
                result.layers.Add(new LayerInfo
                {
                    index = i,
                    name = string.IsNullOrEmpty(name) ? "" : name,
                    isBuiltIn = i < 8
                });
            }

            result.message = "Listed 32 layers";
            return result;
        }

        private TagsLayersResult ExecuteAddLayer(TagsLayersParams p)
        {
            if (!CheckMutationGuards(out string guardMsg))
                return ErrorResult("add-layer", guardMsg);

            if (string.IsNullOrEmpty(p.layerName))
                return ErrorResult("add-layer", "layerName is required");

            var asset = AssetDatabase.LoadMainAssetAtPath(TAG_MANAGER_PATH);
            var so = new SerializedObject(asset);
            var layersProp = so.FindProperty("layers");

            // Check for existing layer with same name
            for (int i = 0; i < layersProp.arraySize; i++)
            {
                if (layersProp.GetArrayElementAtIndex(i).stringValue == p.layerName)
                    return ErrorResult("add-layer", $"Layer '{p.layerName}' already exists");
            }

            int targetIndex = p.layerIndex;
            if (targetIndex >= 0)
            {
                // Validate target index
                if (targetIndex < 8)
                    return ErrorResult("add-layer", "Cannot modify built-in layers (0-7)");
                if (targetIndex >= layersProp.arraySize)
                    return ErrorResult("add-layer",
                        $"Index {targetIndex} out of range (max {layersProp.arraySize - 1})");

                var existing = layersProp.GetArrayElementAtIndex(targetIndex).stringValue;
                if (!string.IsNullOrEmpty(existing))
                    return ErrorResult("add-layer",
                        $"Slot {targetIndex} already occupied by '{existing}'");

                layersProp.GetArrayElementAtIndex(targetIndex).stringValue = p.layerName;
            }
            else
            {
                // Find first empty user slot (8-31)
                bool found = false;
                for (int i = 8; i < layersProp.arraySize; i++)
                {
                    if (string.IsNullOrEmpty(
                            layersProp.GetArrayElementAtIndex(i).stringValue))
                    {
                        layersProp.GetArrayElementAtIndex(i).stringValue = p.layerName;
                        targetIndex = i;
                        found = true;
                        break;
                    }
                }
                if (!found)
                    return ErrorResult("add-layer", "No empty layer slots available (8-31)");
            }

            so.ApplyModifiedProperties();

            return new TagsLayersResult
            {
                success = true,
                operation = "add-layer",
                message = $"Layer '{p.layerName}' added at index {targetIndex}"
            };
        }

        private TagsLayersResult ExecuteListSortingLayers()
        {
            var result = new TagsLayersResult
            {
                success = true,
                operation = "list-sorting-layers"
            };

            foreach (var sl in SortingLayer.layers)
            {
                result.sortingLayers.Add(new SortingLayerInfo
                {
                    name = sl.name,
                    id = sl.id,
                    value = sl.value
                });
            }

            result.message = $"Found {result.sortingLayers.Count} sorting layers";
            return result;
        }

        private TagsLayersResult ExecuteAddSortingLayer(TagsLayersParams p)
        {
            if (!CheckMutationGuards(out string guardMsg))
                return ErrorResult("add-sorting-layer", guardMsg);

            if (string.IsNullOrEmpty(p.sortingLayerName))
                return ErrorResult("add-sorting-layer", "sortingLayerName is required");

            // Check existing
            foreach (var sl in SortingLayer.layers)
            {
                if (sl.name == p.sortingLayerName)
                    return ErrorResult("add-sorting-layer",
                        $"Sorting layer '{p.sortingLayerName}' already exists");
            }

            var asset = AssetDatabase.LoadMainAssetAtPath(TAG_MANAGER_PATH);
            var so = new SerializedObject(asset);
            var sortingProp = so.FindProperty("m_SortingLayers");

            int newIndex = sortingProp.arraySize;
            sortingProp.InsertArrayElementAtIndex(newIndex);
            var newEntry = sortingProp.GetArrayElementAtIndex(newIndex);
            newEntry.FindPropertyRelative("name").stringValue = p.sortingLayerName;
            // Unity assigns unique IDs automatically via ApplyModifiedProperties
            so.ApplyModifiedProperties();

            return new TagsLayersResult
            {
                success = true,
                operation = "add-sorting-layer",
                message = $"Sorting layer '{p.sortingLayerName}' added"
            };
        }

        // -----------------------------------------------------------------
        // Helpers
        // -----------------------------------------------------------------

        private bool CheckMutationGuards(out string message)
        {
            if (EditorApplication.isPlaying)
            {
                message = "Cannot modify tags/layers in play mode.";
                return false;
            }
            message = null;
            return true;
        }

        private TagsLayersResult ErrorResult(string operation, string message)
        {
            return new TagsLayersResult
            {
                success = false,
                operation = operation,
                message = message
            };
        }
    }

    // -----------------------------------------------------------------
    // Models
    // -----------------------------------------------------------------

    [Serializable]
    public class TagsLayersParams
    {
        public string operation;
        public string tagName;
        public string layerName;
        public int layerIndex = -1;
        public string sortingLayerName;
    }

    [Serializable]
    public class TagsLayersResult
    {
        public bool success;
        public string operation;
        public string message;
        public List<string> tags = new List<string>();
        public List<LayerInfo> layers = new List<LayerInfo>();
        public List<SortingLayerInfo> sortingLayers = new List<SortingLayerInfo>();
    }

    [Serializable]
    public class LayerInfo
    {
        public int index;
        public string name;
        public bool isBuiltIn;
    }

    [Serializable]
    public class SortingLayerInfo
    {
        public string name;
        public int id;
        public int value;
    }
}
