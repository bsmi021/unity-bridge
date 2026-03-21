using System;
using System.Collections.Generic;
using UnityEditor;
using UnityEngine;
using UnityEngine.AI;

namespace BWS.Editor.ClaudeCodeBridge
{
    /// <summary>
    /// Command handler for NavMesh operations.
    ///
    /// SUPPORTED OPERATIONS:
    /// 1. "bake"         - Bake NavMesh for the active scene
    /// 2. "clear"        - Clear all baked NavMesh data
    /// 3. "get-settings" - Read current NavMesh build settings
    /// 4. "set-settings" - Modify NavMesh build settings
    /// 5. "get-areas"    - List NavMesh area names and costs
    /// </summary>
    public class NavMeshCommandHandler : ICommandHandler
    {
        public string CommandType => "navmesh-operation";

        public BridgeResponse Execute(BridgeCommand command)
        {
            try
            {
                if (EditorApplication.isCompiling)
                {
                    return BridgeResponse.Error(command.commandId, command.commandType,
                        "Cannot perform NavMesh operations while scripts are compiling.");
                }

                var parameters = JsonUtility.FromJson<NavMeshParams>(
                    command.parametersJson ?? "{}");
                if (parameters == null)
                    parameters = new NavMeshParams();

                BridgeLogger.LogDebug($"Executing navmesh operation: {parameters.operation}");

                switch (parameters.operation?.ToLower())
                {
                    case "bake":
                        return ExecuteBake(command);
                    case "clear":
                        return ExecuteClear(command);
                    case "get-settings":
                        return ExecuteGetSettings(command);
                    case "set-settings":
                        return ExecuteSetSettings(command, parameters);
                    case "get-areas":
                        return ExecuteGetAreas(command);
                    default:
                        return BridgeResponse.Error(
                            command.commandId, command.commandType,
                            $"Unknown navmesh operation: {parameters.operation}. "
                            + "Supported: bake, clear, get-settings, set-settings, get-areas");
                }
            }
            catch (Exception ex)
            {
                BridgeLogger.LogError($"NavMesh operation error: {ex}");
                return BridgeResponse.Error(command.commandId, command.commandType, ex.ToString());
            }
        }

        private BridgeResponse ExecuteBake(BridgeCommand command)
        {
            if (EditorApplication.isPlaying)
            {
                return BridgeResponse.Error(command.commandId, command.commandType,
                    "Cannot bake NavMesh while in Play mode.");
            }

            UnityEditor.AI.NavMeshBuilder.BuildNavMesh();

            var result = new NavMeshResult
            {
                operation = "bake",
                success = true,
                message = "NavMesh baked successfully"
            };
            return BridgeResponse.Success(
                command.commandId, command.commandType, JsonUtility.ToJson(result));
        }

        private BridgeResponse ExecuteClear(BridgeCommand command)
        {
            if (EditorApplication.isPlaying)
            {
                return BridgeResponse.Error(command.commandId, command.commandType,
                    "Cannot clear NavMesh while in Play mode.");
            }

            UnityEditor.AI.NavMeshBuilder.ClearAllNavMeshes();

            var result = new NavMeshResult
            {
                operation = "clear",
                success = true,
                message = "All NavMesh data cleared"
            };
            return BridgeResponse.Success(
                command.commandId, command.commandType, JsonUtility.ToJson(result));
        }

        private BridgeResponse ExecuteGetSettings(BridgeCommand command)
        {
            var settings = NavMesh.GetSettingsByIndex(0);

            var result = new NavMeshSettingsResult
            {
                operation = "get-settings",
                agentRadius = settings.agentRadius,
                agentHeight = settings.agentHeight,
                agentSlope = settings.agentClimb > 0 ? 45f : 0f,
                agentClimb = settings.agentClimb,
                success = true,
                message = "NavMesh settings retrieved"
            };

            // Read from serialized NavMeshProjectSettings for full data
            var serialized = new SerializedObject(
                UnityEditor.AI.NavMeshBuilder.navMeshSettingsObject);
            if (serialized is not null)
            {
                var agentRadius = serialized.FindProperty("m_BuildSettings.agentRadius");
                var agentHeight = serialized.FindProperty("m_BuildSettings.agentHeight");
                var agentSlope = serialized.FindProperty("m_BuildSettings.agentSlope");
                var agentClimb = serialized.FindProperty("m_BuildSettings.agentClimb");

                if (agentRadius is not null) result.agentRadius = agentRadius.floatValue;
                if (agentHeight is not null) result.agentHeight = agentHeight.floatValue;
                if (agentSlope is not null) result.agentSlope = agentSlope.floatValue;
                if (agentClimb is not null) result.agentClimb = agentClimb.floatValue;
            }

            return BridgeResponse.Success(
                command.commandId, command.commandType, JsonUtility.ToJson(result));
        }

        private BridgeResponse ExecuteSetSettings(BridgeCommand command, NavMeshParams p)
        {
            if (EditorApplication.isPlaying)
            {
                return BridgeResponse.Error(command.commandId, command.commandType,
                    "Cannot modify NavMesh settings while in Play mode.");
            }

            var serialized = new SerializedObject(
                UnityEditor.AI.NavMeshBuilder.navMeshSettingsObject);
            if (serialized is null)
            {
                return BridgeResponse.Error(command.commandId, command.commandType,
                    "Could not access NavMesh settings object.");
            }

            bool changed = false;
            if (p.agentRadius > 0)
            {
                var prop = serialized.FindProperty("m_BuildSettings.agentRadius");
                if (prop is not null) { prop.floatValue = p.agentRadius; changed = true; }
            }
            if (p.agentHeight > 0)
            {
                var prop = serialized.FindProperty("m_BuildSettings.agentHeight");
                if (prop is not null) { prop.floatValue = p.agentHeight; changed = true; }
            }
            if (p.agentSlope > 0)
            {
                var prop = serialized.FindProperty("m_BuildSettings.agentSlope");
                if (prop is not null) { prop.floatValue = p.agentSlope; changed = true; }
            }
            if (p.agentClimb > 0)
            {
                var prop = serialized.FindProperty("m_BuildSettings.agentClimb");
                if (prop is not null) { prop.floatValue = p.agentClimb; changed = true; }
            }

            if (changed)
                serialized.ApplyModifiedProperties();

            var result = new NavMeshResult
            {
                operation = "set-settings",
                success = true,
                message = changed ? "NavMesh settings updated" : "No settings changed"
            };
            return BridgeResponse.Success(
                command.commandId, command.commandType, JsonUtility.ToJson(result));
        }

        private BridgeResponse ExecuteGetAreas(BridgeCommand command)
        {
            var areaNames = GameObjectUtility.GetNavMeshAreaNames();
            var areas = new List<NavMeshAreaInfo>();
            for (int i = 0; i < areaNames.Length; i++)
            {
                int areaIndex = GameObjectUtility.GetNavMeshAreaFromName(areaNames[i]);
                areas.Add(new NavMeshAreaInfo
                {
                    name = areaNames[i],
                    index = areaIndex,
                    cost = NavMesh.GetAreaCost(areaIndex)
                });
            }

            var result = new NavMeshAreasResult
            {
                operation = "get-areas",
                areas = areas,
                success = true,
                message = $"Retrieved {areas.Count} NavMesh areas"
            };
            return BridgeResponse.Success(
                command.commandId, command.commandType, JsonUtility.ToJson(result));
        }
    }

    // -----------------------------------------------------------------
    // Models
    // -----------------------------------------------------------------

    [Serializable]
    public class NavMeshParams
    {
        public string operation;
        public float agentRadius = -1f;
        public float agentHeight = -1f;
        public float agentSlope = -1f;
        public float agentClimb = -1f;
    }

    [Serializable]
    public class NavMeshResult
    {
        public string operation;
        public bool success;
        public string message;
    }

    [Serializable]
    public class NavMeshSettingsResult
    {
        public string operation;
        public float agentRadius;
        public float agentHeight;
        public float agentSlope;
        public float agentClimb;
        public bool success;
        public string message;
    }

    [Serializable]
    public class NavMeshAreasResult
    {
        public string operation;
        public List<NavMeshAreaInfo> areas = new List<NavMeshAreaInfo>();
        public bool success;
        public string message;
    }

    [Serializable]
    public class NavMeshAreaInfo
    {
        public string name;
        public int index;
        public float cost;
    }
}
