using System;
using System.Collections.Generic;
using UnityEditor;
using UnityEngine;

namespace BWS.Editor.ClaudeCodeBridge
{
    /// <summary>
    /// Reads and writes Physics2D settings and the 32x32 2D layer collision
    /// matrix. Mirrors <see cref="PhysicsConfigCommandHandler"/> (3D) with the
    /// analogous <see cref="Physics2D"/> API surface.
    ///
    /// SUPPORTED OPERATIONS:
    /// 1. "get"                - All Physics2D settings as a flat struct.
    /// 2. "set"                - Mutate one or more Physics2D properties.
    /// 3. "get-collision-matrix" - 32x32 layer collision matrix.
    /// 4. "set-collision"      - Toggle collision between two layers.
    /// </summary>
    public class Physics2DConfigCommandHandler : ICommandHandler
    {
        public string CommandType => "physics2d-config";

        public BridgeResponse Execute(BridgeCommand command)
        {
            try
            {
                var parameters = JsonUtility.FromJson<Physics2DConfigParams>(
                    command.parametersJson ?? "{}") ?? new Physics2DConfigParams();
                var operation = parameters.operation?.ToLower();

                switch (operation)
                {
                    case "get":
                        return HandleGet(command);
                    case "set":
                        return HandleSet(command, parameters);
                    case "get-collision-matrix":
                        return HandleGetMatrix(command);
                    case "set-collision":
                        return HandleSetCollision(command, parameters);
                    default:
                        return BridgeResponse.Error(
                            command.commandId, command.commandType,
                            $"Unknown operation: {parameters.operation}. " +
                            "Supported: get, set, get-collision-matrix, set-collision");
                }
            }
            catch (Exception ex)
            {
                BridgeLogger.LogError($"Physics2D config error: {ex}");
                return BridgeResponse.Error(command.commandId, command.commandType, ex.ToString());
            }
        }

        private BridgeResponse HandleGet(BridgeCommand command)
        {
            var data = new Physics2DConfigData
            {
                gravityX = Physics2D.gravity.x,
                gravityY = Physics2D.gravity.y,
                defaultContactOffset = Physics2D.defaultContactOffset,
                velocityIterations = Physics2D.velocityIterations,
                positionIterations = Physics2D.positionIterations,
                velocityThreshold = Physics2D.velocityThreshold,
                maxLinearCorrection = Physics2D.maxLinearCorrection,
                maxAngularCorrection = Physics2D.maxAngularCorrection,
                maxTranslationSpeed = Physics2D.maxTranslationSpeed,
                maxRotationSpeed = Physics2D.maxRotationSpeed,
                baumgarteScale = Physics2D.baumgarteScale,
                baumgarteTOIScale = Physics2D.baumgarteTOIScale,
                timeToSleep = Physics2D.timeToSleep,
                linearSleepTolerance = Physics2D.linearSleepTolerance,
                angularSleepTolerance = Physics2D.angularSleepTolerance,
                defaultMaterial = Physics2D.defaultMaterial?.name,
                queriesHitTriggers = Physics2D.queriesHitTriggers,
                queriesStartInColliders = Physics2D.queriesStartInColliders,
                callbacksOnDisable = Physics2D.callbacksOnDisable,
                reuseCollisionCallbacks = Physics2D.reuseCollisionCallbacks,
                autoSyncTransforms = Physics2D.autoSyncTransforms,
                simulationMode = Physics2D.simulationMode.ToString(),
                success = true,
            };
            return BridgeResponse.Success(
                command.commandId, command.commandType,
                JsonUtility.ToJson(data));
        }

        private BridgeResponse HandleSet(BridgeCommand command, Physics2DConfigParams p)
        {
            var changes = new List<string>();

            if (p.setGravity)
            {
                Physics2D.gravity = new Vector2(p.gravityX, p.gravityY);
                changes.Add($"gravity={p.gravityX},{p.gravityY}");
            }
            if (p.setVelocityIterations)
            {
                Physics2D.velocityIterations = p.velocityIterations;
                changes.Add($"velocityIterations={p.velocityIterations}");
            }
            if (p.setPositionIterations)
            {
                Physics2D.positionIterations = p.positionIterations;
                changes.Add($"positionIterations={p.positionIterations}");
            }
            if (p.setVelocityThreshold)
            {
                Physics2D.velocityThreshold = p.velocityThreshold;
                changes.Add($"velocityThreshold={p.velocityThreshold}");
            }
            if (p.setDefaultContactOffset)
            {
                Physics2D.defaultContactOffset = p.defaultContactOffset;
                changes.Add($"defaultContactOffset={p.defaultContactOffset}");
            }
            if (p.setQueriesHitTriggers)
            {
                Physics2D.queriesHitTriggers = p.queriesHitTriggers;
                changes.Add($"queriesHitTriggers={p.queriesHitTriggers}");
            }
            if (p.setAutoSyncTransforms)
            {
                Physics2D.autoSyncTransforms = p.autoSyncTransforms;
                changes.Add($"autoSyncTransforms={p.autoSyncTransforms}");
            }

            var result = new Physics2DMutationResult
            {
                success = true,
                changedFields = changes,
                message = changes.Count == 0
                    ? "No fields changed (pass setX=true with the desired value)."
                    : $"Updated {changes.Count} field(s)."
            };
            return BridgeResponse.Success(
                command.commandId, command.commandType,
                JsonUtility.ToJson(result));
        }

        private BridgeResponse HandleGetMatrix(BridgeCommand command)
        {
            var matrix = new Physics2DMatrixResult { success = true };
            matrix.rows = new List<Physics2DMatrixRow>();
            for (int i = 0; i < 32; i++)
            {
                var row = new Physics2DMatrixRow
                {
                    layer = i,
                    layerName = LayerMask.LayerToName(i),
                    collides = new List<int>(),
                };
                for (int j = 0; j < 32; j++)
                {
                    if (!Physics2D.GetIgnoreLayerCollision(i, j))
                        row.collides.Add(j);
                }
                matrix.rows.Add(row);
            }
            return BridgeResponse.Success(
                command.commandId, command.commandType,
                JsonUtility.ToJson(matrix));
        }

        private BridgeResponse HandleSetCollision(BridgeCommand command, Physics2DConfigParams p)
        {
            if (p.layerA < 0 || p.layerA > 31 || p.layerB < 0 || p.layerB > 31)
            {
                return BridgeResponse.Error(
                    command.commandId, command.commandType,
                    "layerA and layerB must be in range 0-31.");
            }

            Physics2D.IgnoreLayerCollision(p.layerA, p.layerB, !p.collides);
            var result = new Physics2DMutationResult
            {
                success = true,
                changedFields = new List<string> { $"layer[{p.layerA}]<->layer[{p.layerB}]={p.collides}" },
                message = $"Layers {p.layerA} and {p.layerB} now {(p.collides ? "collide" : "do not collide")}."
            };
            return BridgeResponse.Success(
                command.commandId, command.commandType,
                JsonUtility.ToJson(result));
        }
    }

    [Serializable]
    public class Physics2DConfigParams
    {
        public string operation;

        public bool setGravity;
        public float gravityX;
        public float gravityY;

        public bool setVelocityIterations;
        public int velocityIterations;

        public bool setPositionIterations;
        public int positionIterations;

        public bool setVelocityThreshold;
        public float velocityThreshold;

        public bool setDefaultContactOffset;
        public float defaultContactOffset;

        public bool setQueriesHitTriggers;
        public bool queriesHitTriggers;

        public bool setAutoSyncTransforms;
        public bool autoSyncTransforms;

        public int layerA = -1;
        public int layerB = -1;
        public bool collides;
    }

    [Serializable]
    public class Physics2DConfigData
    {
        public bool success;
        public float gravityX;
        public float gravityY;
        public float defaultContactOffset;
        public int velocityIterations;
        public int positionIterations;
        public float velocityThreshold;
        public float maxLinearCorrection;
        public float maxAngularCorrection;
        public float maxTranslationSpeed;
        public float maxRotationSpeed;
        public float baumgarteScale;
        public float baumgarteTOIScale;
        public float timeToSleep;
        public float linearSleepTolerance;
        public float angularSleepTolerance;
        public string defaultMaterial;
        public bool queriesHitTriggers;
        public bool queriesStartInColliders;
        public bool callbacksOnDisable;
        public bool reuseCollisionCallbacks;
        public bool autoSyncTransforms;
        public string simulationMode;
    }

    [Serializable]
    public class Physics2DMutationResult
    {
        public bool success;
        public List<string> changedFields;
        public string message;
    }

    [Serializable]
    public class Physics2DMatrixRow
    {
        public int layer;
        public string layerName;
        public List<int> collides;
    }

    [Serializable]
    public class Physics2DMatrixResult
    {
        public bool success;
        public List<Physics2DMatrixRow> rows;
    }
}
