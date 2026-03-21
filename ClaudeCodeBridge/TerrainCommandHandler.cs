using System;
using System.Collections.Generic;
using UnityEditor;
using UnityEngine;

namespace BWS.Editor.ClaudeCodeBridge
{
    /// <summary>
    /// Command handler for terrain operations.
    ///
    /// SUPPORTED OPERATIONS:
    /// 1. "create"       - Create a new Terrain with TerrainData
    /// 2. "get-info"     - Get terrain info (resolution, size, layers, etc.)
    /// 3. "set-heights"  - Set heightmap region
    /// 4. "get-heights"  - Read heightmap region
    /// 5. "set-settings" - Modify terrain settings
    /// </summary>
    public class TerrainCommandHandler : ICommandHandler
    {
        public string CommandType => "terrain-operation";

        public BridgeResponse Execute(BridgeCommand command)
        {
            try
            {
                if (EditorApplication.isCompiling)
                {
                    return BridgeResponse.Error(command.commandId, command.commandType,
                        "Cannot perform terrain operations while scripts are compiling.");
                }

                var parameters = JsonUtility.FromJson<TerrainParams>(
                    command.parametersJson ?? "{}");
                if (parameters == null)
                    parameters = new TerrainParams();

                BridgeLogger.LogDebug($"Executing terrain operation: {parameters.operation}");

                switch (parameters.operation?.ToLower())
                {
                    case "create":
                        return ExecuteCreate(command, parameters);
                    case "get-info":
                        return ExecuteGetInfo(command, parameters);
                    case "set-heights":
                        return ExecuteSetHeights(command, parameters);
                    case "get-heights":
                        return ExecuteGetHeights(command, parameters);
                    case "set-settings":
                        return ExecuteSetSettings(command, parameters);
                    default:
                        return BridgeResponse.Error(
                            command.commandId, command.commandType,
                            $"Unknown terrain operation: {parameters.operation}. "
                            + "Supported: create, get-info, set-heights, get-heights, set-settings");
                }
            }
            catch (Exception ex)
            {
                BridgeLogger.LogError($"Terrain operation error: {ex}");
                return BridgeResponse.Error(command.commandId, command.commandType, ex.ToString());
            }
        }

        private BridgeResponse ExecuteCreate(BridgeCommand command, TerrainParams p)
        {
            if (EditorApplication.isPlaying)
            {
                return BridgeResponse.Error(command.commandId, command.commandType,
                    "Cannot create terrain while in Play mode.");
            }

            var terrainData = new TerrainData();
            terrainData.heightmapResolution = p.heightmapResolution > 0 ? p.heightmapResolution : 513;
            terrainData.size = new Vector3(
                p.sizeX > 0 ? p.sizeX : 1000f,
                p.sizeY > 0 ? p.sizeY : 600f,
                p.sizeZ > 0 ? p.sizeZ : 1000f);

            string dataPath = p.terrainDataPath;
            if (string.IsNullOrEmpty(dataPath))
                dataPath = "Assets/New Terrain Data.asset";

            AssetDatabase.CreateAsset(terrainData, dataPath);
            var terrainGO = Terrain.CreateTerrainGameObject(terrainData);

            string name = string.IsNullOrEmpty(p.terrainName) ? "Terrain" : p.terrainName;
            terrainGO.name = name;
            Undo.RegisterCreatedObjectUndo(terrainGO, "Create Terrain");

            var result = new TerrainResult
            {
                operation = "create",
                terrainName = name,
                terrainDataPath = dataPath,
                success = true,
                message = $"Terrain '{name}' created with data at {dataPath}"
            };
            return BridgeResponse.Success(
                command.commandId, command.commandType, JsonUtility.ToJson(result));
        }

        private BridgeResponse ExecuteGetInfo(BridgeCommand command, TerrainParams p)
        {
            var terrain = FindTerrain(p.terrainName);
            if (terrain is null)
            {
                return BridgeResponse.Error(command.commandId, command.commandType,
                    $"Terrain not found: {p.terrainName ?? "(none)"}. "
                    + "Specify terrainName or ensure a Terrain exists in the scene.");
            }

            var data = terrain.terrainData;
            var result = new TerrainInfoResult
            {
                operation = "get-info",
                terrainName = terrain.name,
                heightmapResolution = data.heightmapResolution,
                sizeX = data.size.x,
                sizeY = data.size.y,
                sizeZ = data.size.z,
                alphamapLayers = data.alphamapLayers,
                treeInstanceCount = data.treeInstanceCount,
                detailResolution = data.detailResolution,
                success = true,
                message = "Terrain info retrieved"
            };
            return BridgeResponse.Success(
                command.commandId, command.commandType, JsonUtility.ToJson(result));
        }

        private BridgeResponse ExecuteSetHeights(BridgeCommand command, TerrainParams p)
        {
            if (EditorApplication.isPlaying)
            {
                return BridgeResponse.Error(command.commandId, command.commandType,
                    "Cannot set terrain heights while in Play mode.");
            }

            var terrain = FindTerrain(p.terrainName);
            if (terrain is null)
            {
                return BridgeResponse.Error(command.commandId, command.commandType,
                    $"Terrain not found: {p.terrainName ?? "(none)"}");
            }

            if (p.heights == null || p.heights.Count == 0)
            {
                return BridgeResponse.Error(command.commandId, command.commandType,
                    "heights array is required for set-heights operation.");
            }

            var data = terrain.terrainData;
            Undo.RecordObject(data, "Set Terrain Heights");

            int rows = p.heights.Count;
            int cols = p.heights[0].values.Count;
            float[,] heightArray = new float[rows, cols];
            for (int r = 0; r < rows; r++)
            {
                for (int c = 0; c < cols; c++)
                    heightArray[r, c] = p.heights[r].values[c];
            }

            data.SetHeights(p.heightX, p.heightY, heightArray);

            var result = new TerrainResult
            {
                operation = "set-heights",
                terrainName = terrain.name,
                success = true,
                message = $"Heights set at ({p.heightX},{p.heightY}), {rows}x{cols} region"
            };
            return BridgeResponse.Success(
                command.commandId, command.commandType, JsonUtility.ToJson(result));
        }

        private BridgeResponse ExecuteGetHeights(BridgeCommand command, TerrainParams p)
        {
            var terrain = FindTerrain(p.terrainName);
            if (terrain is null)
            {
                return BridgeResponse.Error(command.commandId, command.commandType,
                    $"Terrain not found: {p.terrainName ?? "(none)"}");
            }

            int w = p.heightWidth > 0 ? p.heightWidth : 16;
            int h = p.heightHeight > 0 ? p.heightHeight : 16;
            var data = terrain.terrainData;
            float[,] heightArray = data.GetHeights(p.heightX, p.heightY, w, h);

            var rows = new List<TerrainHeightRow>();
            for (int r = 0; r < heightArray.GetLength(0); r++)
            {
                var row = new TerrainHeightRow();
                for (int c = 0; c < heightArray.GetLength(1); c++)
                    row.values.Add(heightArray[r, c]);
                rows.Add(row);
            }

            var result = new TerrainHeightsResult
            {
                operation = "get-heights",
                terrainName = terrain.name,
                startX = p.heightX,
                startY = p.heightY,
                width = w,
                height = h,
                heights = rows,
                success = true,
                message = $"Heights retrieved at ({p.heightX},{p.heightY}), {h}x{w}"
            };
            return BridgeResponse.Success(
                command.commandId, command.commandType, JsonUtility.ToJson(result));
        }

        private BridgeResponse ExecuteSetSettings(BridgeCommand command, TerrainParams p)
        {
            if (EditorApplication.isPlaying)
            {
                return BridgeResponse.Error(command.commandId, command.commandType,
                    "Cannot modify terrain settings while in Play mode.");
            }

            var terrain = FindTerrain(p.terrainName);
            if (terrain is null)
            {
                return BridgeResponse.Error(command.commandId, command.commandType,
                    $"Terrain not found: {p.terrainName ?? "(none)"}");
            }

            var data = terrain.terrainData;
            Undo.RecordObject(data, "Set Terrain Settings");

            if (p.heightmapResolution > 0)
                data.heightmapResolution = p.heightmapResolution;

            if (p.sizeX > 0 || p.sizeY > 0 || p.sizeZ > 0)
            {
                data.size = new Vector3(
                    p.sizeX > 0 ? p.sizeX : data.size.x,
                    p.sizeY > 0 ? p.sizeY : data.size.y,
                    p.sizeZ > 0 ? p.sizeZ : data.size.z);
            }

            EditorUtility.SetDirty(data);

            var result = new TerrainResult
            {
                operation = "set-settings",
                terrainName = terrain.name,
                success = true,
                message = "Terrain settings updated"
            };
            return BridgeResponse.Success(
                command.commandId, command.commandType, JsonUtility.ToJson(result));
        }

        // -----------------------------------------------------------------
        // Helpers
        // -----------------------------------------------------------------

        private static Terrain FindTerrain(string name)
        {
            if (!string.IsNullOrEmpty(name))
            {
                var go = GameObject.Find(name);
                if (go is not null)
                {
                    var t = go.GetComponent<Terrain>();
                    if (t is not null) return t;
                }
            }
            // Fall back to first active Terrain
            return Terrain.activeTerrain;
        }
    }

    // -----------------------------------------------------------------
    // Models
    // -----------------------------------------------------------------

    [Serializable]
    public class TerrainParams
    {
        public string operation;
        public string terrainName;
        public string terrainDataPath;

        // create / set-settings
        public int heightmapResolution = -1;
        public float sizeX = -1f;
        public float sizeY = -1f;
        public float sizeZ = -1f;

        // set-heights / get-heights
        public int heightX;
        public int heightY;
        public int heightWidth = -1;
        public int heightHeight = -1;
        public List<TerrainHeightRow> heights = new List<TerrainHeightRow>();
    }

    [Serializable]
    public class TerrainHeightRow
    {
        public List<float> values = new List<float>();
    }

    [Serializable]
    public class TerrainResult
    {
        public string operation;
        public string terrainName;
        public string terrainDataPath;
        public bool success;
        public string message;
    }

    [Serializable]
    public class TerrainInfoResult
    {
        public string operation;
        public string terrainName;
        public int heightmapResolution;
        public float sizeX;
        public float sizeY;
        public float sizeZ;
        public int alphamapLayers;
        public int treeInstanceCount;
        public int detailResolution;
        public bool success;
        public string message;
    }

    [Serializable]
    public class TerrainHeightsResult
    {
        public string operation;
        public string terrainName;
        public int startX;
        public int startY;
        public int width;
        public int height;
        public List<TerrainHeightRow> heights = new List<TerrainHeightRow>();
        public bool success;
        public string message;
    }
}
