using System;
using System.Collections.Generic;
using UnityEditor;
using UnityEngine;
using UnityEngine.Tilemaps;

namespace BWS.Editor.ClaudeCodeBridge
{
    /// <summary>
    /// Command handler for 2D Tilemap operations.
    ///
    /// SUPPORTED OPERATIONS:
    /// 1. "set-tile"         - Place a tile at position
    /// 2. "get-tile"         - Get tile at position
    /// 3. "fill-box"         - Fill a rectangular area with tiles
    /// 4. "clear"            - Clear all tiles
    /// 5. "get-bounds"       - Get used cell bounds
    /// 6. "compress-bounds"  - Compress tilemap bounds to used area
    /// </summary>
    public class TilemapCommandHandler : ICommandHandler
    {
        public string CommandType => "tilemap-operation";

        public BridgeResponse Execute(BridgeCommand command)
        {
            try
            {
                if (EditorApplication.isCompiling)
                {
                    return BridgeResponse.Error(command.commandId, command.commandType,
                        "Cannot perform tilemap operations while scripts are compiling.");
                }

                var parameters = JsonUtility.FromJson<TilemapParams>(
                    command.parametersJson ?? "{}");
                if (parameters == null)
                    parameters = new TilemapParams();

                BridgeLogger.LogDebug($"Executing tilemap operation: {parameters.operation}");

                switch (parameters.operation?.ToLower())
                {
                    case "set-tile":
                        return ExecuteSetTile(command, parameters);
                    case "get-tile":
                        return ExecuteGetTile(command, parameters);
                    case "fill-box":
                        return ExecuteFillBox(command, parameters);
                    case "clear":
                        return ExecuteClear(command, parameters);
                    case "get-bounds":
                        return ExecuteGetBounds(command, parameters);
                    case "compress-bounds":
                        return ExecuteCompressBounds(command, parameters);
                    default:
                        return BridgeResponse.Error(
                            command.commandId, command.commandType,
                            $"Unknown tilemap operation: {parameters.operation}. "
                            + "Supported: set-tile, get-tile, fill-box, clear, "
                            + "get-bounds, compress-bounds");
                }
            }
            catch (Exception ex)
            {
                BridgeLogger.LogError($"Tilemap operation error: {ex}");
                return BridgeResponse.Error(command.commandId, command.commandType, ex.ToString());
            }
        }

        private BridgeResponse ExecuteSetTile(BridgeCommand command, TilemapParams p)
        {
            var tilemap = FindTilemap(p.tilemapPath);
            if (tilemap is null)
            {
                return BridgeResponse.Error(command.commandId, command.commandType,
                    $"Tilemap not found: {p.tilemapPath ?? "(none)"}");
            }

            TileBase tile = LoadTile(p.tilePath);
            if (tile is null && !string.IsNullOrEmpty(p.tilePath))
            {
                return BridgeResponse.Error(command.commandId, command.commandType,
                    $"Tile asset not found at: {p.tilePath}");
            }

            var pos = new Vector3Int(p.posX, p.posY, p.posZ);
            Undo.RecordObject(tilemap, "Set Tile");
            tilemap.SetTile(pos, tile);

            var result = new TilemapResult
            {
                operation = "set-tile",
                tilemapPath = p.tilemapPath,
                success = true,
                message = $"Tile set at ({p.posX},{p.posY},{p.posZ})"
            };
            return BridgeResponse.Success(
                command.commandId, command.commandType, JsonUtility.ToJson(result));
        }

        private BridgeResponse ExecuteGetTile(BridgeCommand command, TilemapParams p)
        {
            var tilemap = FindTilemap(p.tilemapPath);
            if (tilemap is null)
            {
                return BridgeResponse.Error(command.commandId, command.commandType,
                    $"Tilemap not found: {p.tilemapPath ?? "(none)"}");
            }

            var pos = new Vector3Int(p.posX, p.posY, p.posZ);
            TileBase tile = tilemap.GetTile(pos);

            string tileName = tile is not null ? tile.name : null;
            string tileAssetPath = tile is not null ? AssetDatabase.GetAssetPath(tile) : null;

            var result = new TilemapTileResult
            {
                operation = "get-tile",
                tilemapPath = p.tilemapPath,
                posX = p.posX,
                posY = p.posY,
                posZ = p.posZ,
                tileName = tileName ?? "",
                tileAssetPath = tileAssetPath ?? "",
                hasTile = tile is not null,
                success = true,
                message = tile is not null
                    ? $"Tile at ({p.posX},{p.posY},{p.posZ}): {tileName}"
                    : $"No tile at ({p.posX},{p.posY},{p.posZ})"
            };
            return BridgeResponse.Success(
                command.commandId, command.commandType, JsonUtility.ToJson(result));
        }

        private BridgeResponse ExecuteFillBox(BridgeCommand command, TilemapParams p)
        {
            var tilemap = FindTilemap(p.tilemapPath);
            if (tilemap is null)
            {
                return BridgeResponse.Error(command.commandId, command.commandType,
                    $"Tilemap not found: {p.tilemapPath ?? "(none)"}");
            }

            TileBase tile = LoadTile(p.tilePath);
            if (tile is null && !string.IsNullOrEmpty(p.tilePath))
            {
                return BridgeResponse.Error(command.commandId, command.commandType,
                    $"Tile asset not found at: {p.tilePath}");
            }

            Undo.RecordObject(tilemap, "Fill Box");
            var pos = new Vector3Int(p.posX, p.posY, p.posZ);
            tilemap.BoxFill(pos, tile, p.startX, p.startY, p.endX, p.endY);

            var result = new TilemapResult
            {
                operation = "fill-box",
                tilemapPath = p.tilemapPath,
                success = true,
                message = $"Box filled from ({p.startX},{p.startY}) to ({p.endX},{p.endY})"
            };
            return BridgeResponse.Success(
                command.commandId, command.commandType, JsonUtility.ToJson(result));
        }

        private BridgeResponse ExecuteClear(BridgeCommand command, TilemapParams p)
        {
            var tilemap = FindTilemap(p.tilemapPath);
            if (tilemap is null)
            {
                return BridgeResponse.Error(command.commandId, command.commandType,
                    $"Tilemap not found: {p.tilemapPath ?? "(none)"}");
            }

            Undo.RecordObject(tilemap, "Clear Tilemap");
            tilemap.ClearAllTiles();

            var result = new TilemapResult
            {
                operation = "clear",
                tilemapPath = p.tilemapPath,
                success = true,
                message = "All tiles cleared"
            };
            return BridgeResponse.Success(
                command.commandId, command.commandType, JsonUtility.ToJson(result));
        }

        private BridgeResponse ExecuteGetBounds(BridgeCommand command, TilemapParams p)
        {
            var tilemap = FindTilemap(p.tilemapPath);
            if (tilemap is null)
            {
                return BridgeResponse.Error(command.commandId, command.commandType,
                    $"Tilemap not found: {p.tilemapPath ?? "(none)"}");
            }

            var bounds = tilemap.cellBounds;
            var result = new TilemapBoundsResult
            {
                operation = "get-bounds",
                tilemapPath = p.tilemapPath,
                minX = bounds.xMin,
                minY = bounds.yMin,
                minZ = bounds.zMin,
                maxX = bounds.xMax,
                maxY = bounds.yMax,
                maxZ = bounds.zMax,
                sizeX = bounds.size.x,
                sizeY = bounds.size.y,
                sizeZ = bounds.size.z,
                success = true,
                message = "Tilemap bounds retrieved"
            };
            return BridgeResponse.Success(
                command.commandId, command.commandType, JsonUtility.ToJson(result));
        }

        private BridgeResponse ExecuteCompressBounds(BridgeCommand command, TilemapParams p)
        {
            var tilemap = FindTilemap(p.tilemapPath);
            if (tilemap is null)
            {
                return BridgeResponse.Error(command.commandId, command.commandType,
                    $"Tilemap not found: {p.tilemapPath ?? "(none)"}");
            }

            Undo.RecordObject(tilemap, "Compress Bounds");
            tilemap.CompressBounds();

            var bounds = tilemap.cellBounds;
            var result = new TilemapBoundsResult
            {
                operation = "compress-bounds",
                tilemapPath = p.tilemapPath,
                minX = bounds.xMin,
                minY = bounds.yMin,
                minZ = bounds.zMin,
                maxX = bounds.xMax,
                maxY = bounds.yMax,
                maxZ = bounds.zMax,
                sizeX = bounds.size.x,
                sizeY = bounds.size.y,
                sizeZ = bounds.size.z,
                success = true,
                message = "Tilemap bounds compressed"
            };
            return BridgeResponse.Success(
                command.commandId, command.commandType, JsonUtility.ToJson(result));
        }

        // -----------------------------------------------------------------
        // Helpers
        // -----------------------------------------------------------------

        private static Tilemap FindTilemap(string path)
        {
            if (string.IsNullOrEmpty(path)) return null;
            var go = GameObject.Find(path);
            if (go is null) return null;
            return go.GetComponent<Tilemap>();
        }

        private static TileBase LoadTile(string assetPath)
        {
            if (string.IsNullOrEmpty(assetPath)) return null;
            return AssetDatabase.LoadAssetAtPath<TileBase>(assetPath);
        }
    }

    // -----------------------------------------------------------------
    // Models
    // -----------------------------------------------------------------

    [Serializable]
    public class TilemapParams
    {
        public string operation;
        public string tilemapPath;
        public string tilePath;
        public int posX;
        public int posY;
        public int posZ;
        public int startX;
        public int startY;
        public int endX;
        public int endY;
    }

    [Serializable]
    public class TilemapResult
    {
        public string operation;
        public string tilemapPath;
        public bool success;
        public string message;
    }

    [Serializable]
    public class TilemapTileResult
    {
        public string operation;
        public string tilemapPath;
        public int posX;
        public int posY;
        public int posZ;
        public string tileName;
        public string tileAssetPath;
        public bool hasTile;
        public bool success;
        public string message;
    }

    [Serializable]
    public class TilemapBoundsResult
    {
        public string operation;
        public string tilemapPath;
        public int minX;
        public int minY;
        public int minZ;
        public int maxX;
        public int maxY;
        public int maxZ;
        public int sizeX;
        public int sizeY;
        public int sizeZ;
        public bool success;
        public string message;
    }
}
