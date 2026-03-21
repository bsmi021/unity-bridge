using System;
using System.Collections.Generic;
using System.Linq;
using UnityEditor;
using UnityEngine;

namespace BWS.Editor.ClaudeCodeBridge
{
    /// <summary>
    /// Command handler for common GameObject maintenance utilities.
    ///
    /// PURPOSE:
    /// Provides Claude Code with tools for finding missing scripts,
    /// managing static flags, setting layers and tags on GameObjects.
    ///
    /// SUPPORTED OPERATIONS:
    /// 1. "missing-scripts" - Find (and optionally fix) missing MonoBehaviour scripts
    /// 2. "static-flags" - Get static editor flags for a GameObject
    /// 3. "set-static-flags" - Set static editor flags on a GameObject
    /// 4. "set-layer" - Set layer on a GameObject (optionally recursive)
    /// 5. "set-tag" - Set tag on a GameObject
    /// 6. "duplicate" - Duplicate a GameObject with Undo support
    /// </summary>
    public class GameObjectUtilityCommandHandler : ICommandHandler
    {
        public string CommandType => "gameobject-utility";

        public BridgeResponse Execute(BridgeCommand command)
        {
            try
            {
                var parameters = JsonUtility.FromJson<GameObjectUtilityParams>(
                    command.parametersJson ?? "{}");
                if (parameters == null)
                    parameters = new GameObjectUtilityParams();

                var operation = parameters.operation?.ToLower();
                BridgeLogger.LogDebug($"Executing gameobject-utility: {operation}");

                // Guard: no operations while compiling
                if (EditorApplication.isCompiling)
                {
                    return BridgeResponse.Error(command.commandId, command.commandType,
                        "Cannot execute while scripts are compiling.");
                }

                // Guard: no mutating operations during play mode
                if (EditorApplication.isPlaying &&
                    operation is "set-static-flags" or "set-layer"
                        or "set-tag" or "missing-scripts" or "duplicate")
                {
                    if (operation == "missing-scripts" && !parameters.fix)
                    {
                        // Read-only missing-scripts scan is okay in play mode
                    }
                    else
                    {
                        return BridgeResponse.Error(command.commandId, command.commandType,
                            "Mutating operations are not supported during play mode.");
                    }
                }

                switch (operation)
                {
                    case "missing-scripts":
                        return HandleMissingScripts(command, parameters.fix);
                    case "static-flags":
                        return GetStaticFlags(command, parameters.gameObjectPath);
                    case "set-static-flags":
                        return SetStaticFlags(command, parameters);
                    case "set-layer":
                        return SetLayer(command, parameters);
                    case "set-tag":
                        return SetTag(command, parameters);
                    case "duplicate":
                        return DuplicateGameObject(command, parameters);
                    default:
                        return BridgeResponse.Error(command.commandId, command.commandType,
                            $"Unknown operation: {parameters.operation}. " +
                            "Supported: missing-scripts, static-flags, set-static-flags, " +
                            "set-layer, set-tag, duplicate");
                }
            }
            catch (Exception ex)
            {
                BridgeLogger.LogError($"GameObject utility error: {ex}");
                return BridgeResponse.Error(command.commandId, command.commandType, ex.ToString());
            }
        }

        private BridgeResponse HandleMissingScripts(BridgeCommand command, bool fix)
        {
            var allObjects = Resources.FindObjectsOfTypeAll<GameObject>();
            var results = new List<MissingScriptInfo>();
            int totalRemoved = 0;
            int totalCount = 0;

            foreach (var go in allObjects)
            {
                // Skip persistent assets (only process scene objects)
                if (EditorUtility.IsPersistent(go)) continue;

                int missingCount = GameObjectUtility.GetMonoBehavioursWithMissingScriptCount(go);
                if (missingCount > 0)
                {
                    results.Add(new MissingScriptInfo
                    {
                        path = GetGameObjectPath(go),
                        count = missingCount
                    });
                    totalCount += missingCount;

                    if (fix)
                    {
                        Undo.SetCurrentGroupName($"Bridge: Remove missing scripts from {go.name}");
                        // MC6: RegisterCompleteObjectUndo BEFORE RemoveMonoBehavioursWithMissingScript
                        Undo.RegisterCompleteObjectUndo(go, "Remove Missing Scripts");
                        int removed = GameObjectUtility.RemoveMonoBehavioursWithMissingScript(go);
                        totalRemoved += removed;
                    }
                }
            }

            var result = new GameObjectUtilityResult
            {
                success = true,
                operation = "missing-scripts",
                found = results,
                totalCount = totalCount,
                removed = totalRemoved
            };
            return BridgeResponse.Success(command.commandId, command.commandType,
                JsonUtility.ToJson(result));
        }

        private BridgeResponse GetStaticFlags(BridgeCommand command, string objectPath)
        {
            if (string.IsNullOrEmpty(objectPath))
            {
                return BridgeResponse.Error(command.commandId, command.commandType,
                    "gameObjectPath is required for static-flags operation.");
            }

            var go = GameObject.Find(objectPath);
            if (go == null)
            {
                return BridgeResponse.Error(command.commandId, command.commandType,
                    $"GameObject not found at path: {objectPath}");
            }

            var flags = GameObjectUtility.GetStaticEditorFlags(go);
            var flagNames = ParseFlagNames(flags);

            var result = new GameObjectUtilityResult
            {
                success = true,
                operation = "static-flags",
                path = objectPath,
                flags = flagNames,
                rawValue = (int)flags
            };
            return BridgeResponse.Success(command.commandId, command.commandType,
                JsonUtility.ToJson(result));
        }

        private BridgeResponse SetStaticFlags(BridgeCommand command, GameObjectUtilityParams parameters)
        {
            if (string.IsNullOrEmpty(parameters.gameObjectPath))
            {
                return BridgeResponse.Error(command.commandId, command.commandType,
                    "gameObjectPath is required for set-static-flags operation.");
            }

            var go = GameObject.Find(parameters.gameObjectPath);
            if (go == null)
            {
                return BridgeResponse.Error(command.commandId, command.commandType,
                    $"GameObject not found at path: {parameters.gameObjectPath}");
            }

            var newFlags = BuildFlags(parameters.flags);
            Undo.RecordObject(go, "Set Static Flags");
            GameObjectUtility.SetStaticEditorFlags(go, newFlags);

            var flagNames = ParseFlagNames(newFlags);
            var result = new GameObjectUtilityResult
            {
                success = true,
                operation = "set-static-flags",
                path = parameters.gameObjectPath,
                flags = flagNames,
                changed = true
            };
            return BridgeResponse.Success(command.commandId, command.commandType,
                JsonUtility.ToJson(result));
        }

        private BridgeResponse SetLayer(BridgeCommand command, GameObjectUtilityParams parameters)
        {
            if (string.IsNullOrEmpty(parameters.gameObjectPath))
            {
                return BridgeResponse.Error(command.commandId, command.commandType,
                    "gameObjectPath is required for set-layer operation.");
            }

            var go = GameObject.Find(parameters.gameObjectPath);
            if (go == null)
            {
                return BridgeResponse.Error(command.commandId, command.commandType,
                    $"GameObject not found at path: {parameters.gameObjectPath}");
            }

            Undo.SetCurrentGroupName($"Bridge: Set layer {parameters.layer} on {parameters.gameObjectPath}");
            int affected = 0;

            if (parameters.recursive)
            {
                // GetComponentsInChildren<Transform>(true) includes inactive children
                var transforms = go.GetComponentsInChildren<Transform>(true);
                foreach (var t in transforms)
                {
                    Undo.RecordObject(t.gameObject, "Set Layer");
                    t.gameObject.layer = parameters.layer;
                    affected++;
                }
            }
            else
            {
                Undo.RecordObject(go, "Set Layer");
                go.layer = parameters.layer;
                affected = 1;
            }

            var result = new GameObjectUtilityResult
            {
                success = true,
                operation = "set-layer",
                path = parameters.gameObjectPath,
                layer = parameters.layer,
                affectedCount = affected
            };
            return BridgeResponse.Success(command.commandId, command.commandType,
                JsonUtility.ToJson(result));
        }

        private BridgeResponse SetTag(BridgeCommand command, GameObjectUtilityParams parameters)
        {
            if (string.IsNullOrEmpty(parameters.gameObjectPath))
            {
                return BridgeResponse.Error(command.commandId, command.commandType,
                    "gameObjectPath is required for set-tag operation.");
            }

            if (string.IsNullOrEmpty(parameters.tag))
            {
                return BridgeResponse.Error(command.commandId, command.commandType,
                    "tag is required for set-tag operation.");
            }

            var go = GameObject.Find(parameters.gameObjectPath);
            if (go == null)
            {
                return BridgeResponse.Error(command.commandId, command.commandType,
                    $"GameObject not found at path: {parameters.gameObjectPath}");
            }

            Undo.RecordObject(go, "Set Tag");
            go.tag = parameters.tag;

            var result = new GameObjectUtilityResult
            {
                success = true,
                operation = "set-tag",
                path = parameters.gameObjectPath,
                tag = parameters.tag,
                changed = true
            };
            return BridgeResponse.Success(command.commandId, command.commandType,
                JsonUtility.ToJson(result));
        }

        private BridgeResponse DuplicateGameObject(
            BridgeCommand command, GameObjectUtilityParams parameters)
        {
            if (string.IsNullOrEmpty(parameters.gameObjectPath))
            {
                return BridgeResponse.Error(command.commandId, command.commandType,
                    "gameObjectPath is required for duplicate operation.");
            }

            var go = GameObject.Find(parameters.gameObjectPath);
            if (go == null)
            {
                return BridgeResponse.Error(command.commandId, command.commandType,
                    $"GameObject not found at path: {parameters.gameObjectPath}");
            }

            // Select the original so Duplicate operates on it
            Selection.activeGameObject = go;
            Unsupported.DuplicateGameObjectsUsingPasteboard();

            // The duplicate is now the active selection
            var duplicate = Selection.activeGameObject;
            if (duplicate == null || duplicate == go)
            {
                return BridgeResponse.Error(command.commandId, command.commandType,
                    $"Failed to duplicate GameObject: {parameters.gameObjectPath}");
            }

            var duplicatePath = GetGameObjectPath(duplicate);
            var result = new GameObjectUtilityResult
            {
                success = true,
                operation = "duplicate",
                path = parameters.gameObjectPath,
                duplicatePath = duplicatePath,
                duplicateName = duplicate.name,
            };
            BridgeLogger.LogInfo($"Duplicated: {parameters.gameObjectPath} -> {duplicatePath}");
            return BridgeResponse.Success(command.commandId, command.commandType,
                JsonUtility.ToJson(result));
        }

        // ---------------------------------------------------------------
        // Helpers
        // ---------------------------------------------------------------

        private static string GetGameObjectPath(GameObject go)
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

        private static readonly Dictionary<string, StaticEditorFlags> FLAG_MAP =
            new Dictionary<string, StaticEditorFlags>(StringComparer.OrdinalIgnoreCase)
        {
            { "Everything", StaticEditorFlags.ContributeGI | StaticEditorFlags.OccluderStatic |
                StaticEditorFlags.BatchingStatic | StaticEditorFlags.NavigationStatic |
                StaticEditorFlags.OccludeeStatic | StaticEditorFlags.OffMeshLinkGeneration |
                StaticEditorFlags.ReflectionProbeStatic },
            { "ContributeGI", StaticEditorFlags.ContributeGI },
            { "OccluderStatic", StaticEditorFlags.OccluderStatic },
            { "BatchingStatic", StaticEditorFlags.BatchingStatic },
            { "NavigationStatic", StaticEditorFlags.NavigationStatic },
            { "OccludeeStatic", StaticEditorFlags.OccludeeStatic },
            { "OffMeshLinkGeneration", StaticEditorFlags.OffMeshLinkGeneration },
            { "ReflectionProbeStatic", StaticEditorFlags.ReflectionProbeStatic },
        };

        private static StaticEditorFlags BuildFlags(List<string> flagNames)
        {
            StaticEditorFlags result = 0;
            if (flagNames == null) return result;

            foreach (var name in flagNames)
            {
                if (FLAG_MAP.TryGetValue(name.Trim(), out var flag))
                    result |= flag;
                else if (int.TryParse(name.Trim(), out var rawValue))
                    result |= (StaticEditorFlags)rawValue;
            }
            return result;
        }

        private static List<string> ParseFlagNames(StaticEditorFlags flags)
        {
            var names = new List<string>();
            if (flags.HasFlag(StaticEditorFlags.ContributeGI)) names.Add("ContributeGI");
            if (flags.HasFlag(StaticEditorFlags.OccluderStatic)) names.Add("OccluderStatic");
            if (flags.HasFlag(StaticEditorFlags.BatchingStatic)) names.Add("BatchingStatic");
            if (flags.HasFlag(StaticEditorFlags.NavigationStatic)) names.Add("NavigationStatic");
            if (flags.HasFlag(StaticEditorFlags.OccludeeStatic)) names.Add("OccludeeStatic");
            if (flags.HasFlag(StaticEditorFlags.OffMeshLinkGeneration)) names.Add("OffMeshLinkGeneration");
            if (flags.HasFlag(StaticEditorFlags.ReflectionProbeStatic)) names.Add("ReflectionProbeStatic");
            return names;
        }
    }
}
