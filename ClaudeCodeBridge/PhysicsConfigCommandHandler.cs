using System;
using System.Collections.Generic;
using UnityEditor;
using UnityEngine;

namespace BWS.Editor.ClaudeCodeBridge
{
    /// <summary>
    /// Command handler for physics configuration operations.
    ///
    /// SUPPORTED OPERATIONS:
    /// 1. "get" - Read current physics settings
    /// 2. "set" - Modify physics settings
    /// 3. "collision-matrix-get" - Read the 32x32 layer collision matrix
    /// 4. "collision-matrix-set" - Set collision between two layers
    ///
    /// GUARDS:
    /// - EditorApplication.isCompiling: blocks all operations
    /// - EditorApplication.isPlaying: blocks mutating operations
    /// </summary>
    public class PhysicsConfigCommandHandler : ICommandHandler
    {
        public string CommandType => "physics-config";

        public BridgeResponse Execute(BridgeCommand command)
        {
            try
            {
                if (EditorApplication.isCompiling)
                {
                    return BridgeResponse.Error(command.commandId, command.commandType,
                        "Cannot access physics config while scripts are compiling.");
                }

                var parameters = JsonUtility.FromJson<PhysicsConfigParams>(
                    command.parametersJson ?? "{}");
                if (parameters == null)
                    parameters = new PhysicsConfigParams();

                PhysicsConfigResult result;
                switch (parameters.operation?.ToLower())
                {
                    case "get":
                        result = ExecuteGet();
                        break;
                    case "set":
                        result = ExecuteSet(parameters);
                        break;
                    case "collision-matrix-get":
                        result = ExecuteCollisionMatrixGet();
                        break;
                    case "collision-matrix-set":
                        result = ExecuteCollisionMatrixSet(parameters);
                        break;
                    default:
                        result = new PhysicsConfigResult
                        {
                            success = false,
                            operation = parameters.operation,
                            message = $"Unknown operation: {parameters.operation}. "
                                + "Supported: get, set, collision-matrix-get, collision-matrix-set"
                        };
                        break;
                }

                var resultJson = JsonUtility.ToJson(result);
                return BridgeResponse.Success(command.commandId, command.commandType, resultJson);
            }
            catch (Exception ex)
            {
                BridgeLogger.LogError($"PhysicsConfig error: {ex}");
                return BridgeResponse.Error(command.commandId, command.commandType, ex.ToString());
            }
        }

        private PhysicsConfigResult ExecuteGet()
        {
            return new PhysicsConfigResult
            {
                success = true,
                operation = "get",
                gravityX = Physics.gravity.x,
                gravityY = Physics.gravity.y,
                gravityZ = Physics.gravity.z,
                defaultSolverIterations = Physics.defaultSolverIterations,
                bounceThreshold = Physics.bounceThreshold,
                sleepThreshold = Physics.sleepThreshold,
                defaultContactOffset = Physics.defaultContactOffset,
                autoSyncTransforms = Physics.autoSyncTransforms,
                reuseCollisionCallbacks = Physics.reuseCollisionCallbacks,
                message = "Physics settings retrieved"
            };
        }

        private PhysicsConfigResult ExecuteSet(PhysicsConfigParams p)
        {
            if (EditorApplication.isPlaying)
            {
                return new PhysicsConfigResult
                {
                    success = false,
                    operation = "set",
                    message = "Cannot modify physics settings in play mode."
                };
            }

            if (p.gravity != null && p.gravity.isSet)
                Physics.gravity = new Vector3(p.gravity.x, p.gravity.y, p.gravity.z);

            if (p.defaultSolverIterations >= 0)
                Physics.defaultSolverIterations = p.defaultSolverIterations;

            if (p.bounceThreshold >= 0)
                Physics.bounceThreshold = p.bounceThreshold;

            if (p.sleepThreshold >= 0)
                Physics.sleepThreshold = p.sleepThreshold;

            if (p.defaultContactOffset > 0)
                Physics.defaultContactOffset = p.defaultContactOffset;

            if (p.setAutoSyncTransforms)
                Physics.autoSyncTransforms = p.autoSyncTransforms;

            if (p.setReuseCollisionCallbacks)
                Physics.reuseCollisionCallbacks = p.reuseCollisionCallbacks;

            EditorUtility.SetDirty(
                UnityEditor.AssetDatabase.LoadMainAssetAtPath(
                    "ProjectSettings/DynamicsManager.asset"));

            return ExecuteGet();
        }

        private PhysicsConfigResult ExecuteCollisionMatrixGet()
        {
            var result = new PhysicsConfigResult
            {
                success = true,
                operation = "collision-matrix-get",
                message = "Collision matrix retrieved"
            };

            for (int i = 0; i < 32; i++)
            {
                string layerName = LayerMask.LayerToName(i);
                if (string.IsNullOrEmpty(layerName)) continue;

                for (int j = i; j < 32; j++)
                {
                    string otherName = LayerMask.LayerToName(j);
                    if (string.IsNullOrEmpty(otherName)) continue;

                    bool ignoring = Physics.GetIgnoreLayerCollision(i, j);
                    result.collisionEntries.Add(new CollisionMatrixEntry
                    {
                        layer1 = i,
                        layer1Name = layerName,
                        layer2 = j,
                        layer2Name = otherName,
                        collides = !ignoring
                    });
                }
            }

            return result;
        }

        private PhysicsConfigResult ExecuteCollisionMatrixSet(PhysicsConfigParams p)
        {
            if (EditorApplication.isPlaying)
            {
                return new PhysicsConfigResult
                {
                    success = false,
                    operation = "collision-matrix-set",
                    message = "Cannot modify collision matrix in play mode."
                };
            }

            if (p.layer1 < 0 || p.layer1 > 31 || p.layer2 < 0 || p.layer2 > 31)
            {
                return new PhysicsConfigResult
                {
                    success = false,
                    operation = "collision-matrix-set",
                    message = "Layer indices must be 0-31."
                };
            }

            Physics.IgnoreLayerCollision(p.layer1, p.layer2, p.ignoreCollision);

            EditorUtility.SetDirty(
                UnityEditor.AssetDatabase.LoadMainAssetAtPath(
                    "ProjectSettings/DynamicsManager.asset"));

            bool ignoring = Physics.GetIgnoreLayerCollision(p.layer1, p.layer2);
            return new PhysicsConfigResult
            {
                success = true,
                operation = "collision-matrix-set",
                message = $"Layers {p.layer1} and {p.layer2}: "
                    + (ignoring ? "ignoring collisions" : "colliding")
            };
        }
    }

    // -----------------------------------------------------------------
    // Models
    // -----------------------------------------------------------------

    [Serializable]
    public class PhysicsConfigParams
    {
        public string operation;

        // set operation
        public SerializableVector3 gravity;
        public int defaultSolverIterations = -1;
        public float bounceThreshold = -1f;
        public float sleepThreshold = -1f;
        public float defaultContactOffset = -1f;
        public bool autoSyncTransforms;
        public bool setAutoSyncTransforms;
        public bool reuseCollisionCallbacks;
        public bool setReuseCollisionCallbacks;

        // collision-matrix-set
        public int layer1 = -1;
        public int layer2 = -1;
        public bool ignoreCollision;
    }

    [Serializable]
    public class PhysicsConfigResult
    {
        public bool success;
        public string operation;
        public string message;

        // get result fields
        public float gravityX;
        public float gravityY;
        public float gravityZ;
        public int defaultSolverIterations;
        public float bounceThreshold;
        public float sleepThreshold;
        public float defaultContactOffset;
        public bool autoSyncTransforms;
        public bool reuseCollisionCallbacks;

        // collision matrix
        public List<CollisionMatrixEntry> collisionEntries = new List<CollisionMatrixEntry>();
    }

    [Serializable]
    public class CollisionMatrixEntry
    {
        public int layer1;
        public string layer1Name;
        public int layer2;
        public string layer2Name;
        public bool collides;
    }
}
