/// <summary>
/// Animator Operation Command Handler - provides programmatic control over Unity Animator Controllers.
///
/// Supports 22 operations across 5 categories:
/// - Controller: create-controller, get-controller-info
/// - Layer: add-layer, set-layer-weight, set-layer-blending, delete-layer, get-layers
/// - State: add-state, set-state-motion, set-state-speed, set-default-state, delete-state, get-states
/// - Transition: add-transition, set-transition-duration, set-transition-conditions, delete-transition, get-transitions
/// - Parameter: add-parameter, set-parameter-default, delete-parameter, get-parameters
///
/// Implementation split across partial class files:
/// - AnimatorOperationCommandHandler.cs (this file): Execute, controller ops, helper methods
/// - AnimatorLayerOperations.cs: Layer operations
/// - AnimatorStateOperations.cs: State operations
/// - AnimatorTransitionOperations.cs: Transition operations
/// - AnimatorParameterOperations.cs: Parameter operations
/// </summary>

using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;

using UnityEditor;
using UnityEditor.Animations;
using UnityEngine;

namespace BWS.Editor.ClaudeCodeBridge
{
    /// <summary>
    /// Command handler for animator controller operations.
    /// Provides comprehensive programmatic control over Unity Animator Controllers.
    /// </summary>
    public partial class AnimatorOperationCommandHandler : ICommandHandler
    {
        public string CommandType => "animator-operation";

        public BridgeResponse Execute(BridgeCommand command)
        {
            try
            {
                var parameters = JsonUtility.FromJson<AnimatorOperationParams>(command.parametersJson ?? "{}");
                if (parameters == null || string.IsNullOrEmpty(parameters.operation))
                {
                    return BridgeResponse.Error(
                        command.commandId, command.commandType, "Missing required parameter: operation");
                }

                BridgeLogger.LogDebug($"Executing operation: {parameters.operation}");

                AnimatorOperationResult result;
                switch (parameters.operation.ToLower())
                {
                    // Controller operations
                    case "create-controller":
                        result = CreateController(parameters);
                        break;
                    case "get-controller-info":
                        result = GetControllerInfo(parameters);
                        break;

                    // Layer operations (AnimatorLayerOperations.cs)
                    case "add-layer":
                        result = AddLayer(parameters);
                        break;
                    case "set-layer-weight":
                        result = SetLayerWeight(parameters);
                        break;
                    case "set-layer-blending":
                        result = SetLayerBlending(parameters);
                        break;
                    case "delete-layer":
                        result = DeleteLayer(parameters);
                        break;
                    case "get-layers":
                        result = GetLayers(parameters);
                        break;

                    // State operations (AnimatorStateOperations.cs)
                    case "add-state":
                        result = AddState(parameters);
                        break;
                    case "set-state-motion":
                        result = SetStateMotion(parameters);
                        break;
                    case "set-state-speed":
                        result = SetStateSpeed(parameters);
                        break;
                    case "set-default-state":
                        result = SetDefaultState(parameters);
                        break;
                    case "delete-state":
                        result = DeleteState(parameters);
                        break;
                    case "get-states":
                        result = GetStates(parameters);
                        break;

                    // Transition operations (AnimatorTransitionOperations.cs)
                    case "add-transition":
                        result = AddTransition(parameters);
                        break;
                    case "set-transition-duration":
                        result = SetTransitionDuration(parameters);
                        break;
                    case "set-transition-conditions":
                        result = SetTransitionConditions(parameters);
                        break;
                    case "delete-transition":
                        result = DeleteTransition(parameters);
                        break;
                    case "get-transitions":
                        result = GetTransitions(parameters);
                        break;

                    // Parameter operations (AnimatorParameterOperations.cs)
                    case "add-parameter":
                        result = AddParameter(parameters);
                        break;
                    case "set-parameter-default":
                        result = SetParameterDefault(parameters);
                        break;
                    case "delete-parameter":
                        result = DeleteParameter(parameters);
                        break;
                    case "get-parameters":
                        result = GetParameters(parameters);
                        break;

                    default:
                        return BridgeResponse.Error(
                            command.commandId,
                            command.commandType,
                            $"Unknown operation: {parameters.operation}. See documentation for supported operations."
                        );
                }

                var resultJson = JsonUtility.ToJson(result);
                if (result.success)
                {
                    BridgeLogger.LogInfo($"Operation '{parameters.operation}' completed successfully");
                    return BridgeResponse.Success(command.commandId, command.commandType, resultJson);
                }
                else
                {
                    BridgeLogger.LogWarning($"Operation '{parameters.operation}' failed: {result.message}");
                    return BridgeResponse.Error(command.commandId, command.commandType, result.message);
                }
            }
            catch (Exception ex)
            {
                BridgeLogger.LogError($"Error: {ex}");
                return BridgeResponse.Error(command.commandId, command.commandType, ex.ToString());
            }
        }

        #region Controller Operations

        /// <summary>
        /// Creates a new Animator Controller asset.
        /// </summary>
        private AnimatorOperationResult CreateController(AnimatorOperationParams parameters)
        {
            var result = new AnimatorOperationResult
            {
                operation = "create-controller",
                controllerPath = parameters.controllerPath
            };

            try
            {
                if (string.IsNullOrEmpty(parameters.controllerPath))
                {
                    result.success = false;
                    result.message = "Controller path is required";
                    return result;
                }

                if (File.Exists(Path.Combine(Application.dataPath, "..", parameters.controllerPath)))
                {
                    result.success = false;
                    result.message = $"Controller already exists at path: {parameters.controllerPath}";
                    return result;
                }

                var directory = Path.GetDirectoryName(parameters.controllerPath);
                var fullDirectoryPath = Path.Combine(Application.dataPath, "..", directory);
                if (!Directory.Exists(fullDirectoryPath))
                {
                    Directory.CreateDirectory(fullDirectoryPath);
                    AssetDatabase.Refresh();
                }

                var controller = AnimatorController.CreateAnimatorControllerAtPath(parameters.controllerPath);
                if (controller == null)
                {
                    result.success = false;
                    result.message = "Failed to create controller";
                    return result;
                }

                AssetDatabase.SaveAssets();
                AssetDatabase.Refresh();

                result.success = true;
                result.message = $"Controller created successfully at {parameters.controllerPath}";
                result.layers = GetControllerLayers(controller);
                result.parameters = GetControllerParameters(controller);

                BridgeLogger.LogDebug($"Created controller: {parameters.controllerPath}");
            }
            catch (Exception ex)
            {
                result.success = false;
                result.message = $"Failed to create controller: {ex.Message}";
                BridgeLogger.LogError($"Create controller failed: {ex}");
            }

            return result;
        }

        /// <summary>
        /// Gets comprehensive information about a controller.
        /// </summary>
        private AnimatorOperationResult GetControllerInfo(AnimatorOperationParams parameters)
        {
            var result = new AnimatorOperationResult
            {
                operation = "get-controller-info",
                controllerPath = parameters.controllerPath
            };

            try
            {
                var controller = LoadController(parameters.controllerPath);
                if (controller == null)
                {
                    result.success = false;
                    result.message = $"Controller not found at path: {parameters.controllerPath}";
                    return result;
                }

                result.layers = GetControllerLayers(controller);
                result.parameters = GetControllerParameters(controller);

                foreach (var layer in controller.layers)
                {
                    result.states.AddRange(GetLayerStates(layer));
                }

                result.success = true;
                result.message = $"Retrieved controller info: {result.layers.Count} layers, " +
                    $"{result.states.Count} states, {result.parameters.Count} parameters";

                BridgeLogger.LogDebug($"Retrieved controller info: {parameters.controllerPath}");
            }
            catch (Exception ex)
            {
                result.success = false;
                result.message = $"Failed to get controller info: {ex.Message}";
                BridgeLogger.LogError($"Get controller info failed: {ex}");
            }

            return result;
        }

        #endregion

        #region Helper Methods

        private AnimatorController LoadController(string controllerPath)
        {
            if (string.IsNullOrEmpty(controllerPath))
                return null;

            return AssetDatabase.LoadAssetAtPath<AnimatorController>(controllerPath);
        }

        private List<AnimatorLayerInfo> GetControllerLayers(AnimatorController controller)
        {
            var layers = new List<AnimatorLayerInfo>();
            foreach (var layer in controller.layers)
            {
                layers.Add(new AnimatorLayerInfo
                {
                    name = layer.name,
                    weight = layer.defaultWeight,
                    blendingMode = layer.blendingMode.ToString(),
                    stateCount = layer.stateMachine.states.Length,
                    iKPass = layer.iKPass,
                    avatarMask = layer.avatarMask != null
                        ? AssetDatabase.GetAssetPath(layer.avatarMask) : null
                });
            }
            return layers;
        }

        private List<AnimatorStateInfo> GetLayerStates(AnimatorControllerLayer layer)
        {
            var states = new List<AnimatorStateInfo>();
            foreach (var stateEntry in layer.stateMachine.states)
            {
                var state = stateEntry.state;
                states.Add(new AnimatorStateInfo
                {
                    name = state.name,
                    layerName = layer.name,
                    motionPath = state.motion != null
                        ? AssetDatabase.GetAssetPath(state.motion) : null,
                    speed = state.speed,
                    isDefaultState = layer.stateMachine.defaultState == state,
                    tag = state.tag
                });
            }
            return states;
        }

        private List<AnimatorParameterInfo> GetControllerParameters(AnimatorController controller)
        {
            var parameters = new List<AnimatorParameterInfo>();
            foreach (var param in controller.parameters)
            {
                var paramInfo = new AnimatorParameterInfo
                {
                    name = param.name,
                    type = param.type.ToString()
                };

                switch (param.type)
                {
                    case AnimatorControllerParameterType.Float:
                        paramInfo.defaultValue = param.defaultFloat.ToString();
                        break;
                    case AnimatorControllerParameterType.Int:
                        paramInfo.defaultValue = param.defaultInt.ToString();
                        break;
                    case AnimatorControllerParameterType.Bool:
                        paramInfo.defaultValue = param.defaultBool.ToString();
                        break;
                    case AnimatorControllerParameterType.Trigger:
                        paramInfo.defaultValue = "trigger";
                        break;
                }
                parameters.Add(paramInfo);
            }
            return parameters;
        }

        private AnimatorStateTransition FindTransition(
            AnimatorControllerLayer layer, string sourceState, string destinationState)
        {
            var destEntry = Array.Find(layer.stateMachine.states, s => s.state.name == destinationState);
            if (destEntry.state == null)
                return null;

            if (sourceState == "Any State")
            {
                return Array.Find(
                    layer.stateMachine.anyStateTransitions,
                    t => t.destinationState == destEntry.state);
            }

            var srcEntry = Array.Find(layer.stateMachine.states, s => s.state.name == sourceState);
            if (srcEntry.state == null)
                return null;

            return Array.Find(srcEntry.state.transitions, t => t.destinationState == destEntry.state);
        }

        private AnimatorTransitionInfo CreateTransitionInfo(
            string sourceStateName, AnimatorStateTransition transition)
        {
            var info = new AnimatorTransitionInfo
            {
                sourceState = sourceStateName,
                destinationState = transition.destinationState != null
                    ? transition.destinationState.name : "null",
                duration = transition.duration,
                hasExitTime = transition.hasExitTime,
                exitTime = transition.exitTime,
                conditionCount = transition.conditions.Length
            };

            foreach (var condition in transition.conditions)
            {
                info.conditions.Add(new TransitionCondition
                {
                    parameter = condition.parameter,
                    mode = condition.mode.ToString(),
                    threshold = condition.threshold
                });
            }
            return info;
        }

        private AnimatorControllerParameterType ParseParameterType(string typeString)
        {
            switch (typeString.ToLower())
            {
                case "float":  return AnimatorControllerParameterType.Float;
                case "int":    return AnimatorControllerParameterType.Int;
                case "bool":   return AnimatorControllerParameterType.Bool;
                case "trigger": return AnimatorControllerParameterType.Trigger;
                default:
                    throw new ArgumentException(
                        $"Invalid parameter type: {typeString}. Must be Float, Int, Bool, or Trigger");
            }
        }

        private AnimatorConditionMode ParseConditionMode(string modeString)
        {
            switch (modeString.ToLower())
            {
                case "if":       return AnimatorConditionMode.If;
                case "ifnot":    return AnimatorConditionMode.IfNot;
                case "greater":  return AnimatorConditionMode.Greater;
                case "less":     return AnimatorConditionMode.Less;
                case "equals":   return AnimatorConditionMode.Equals;
                case "notequal": return AnimatorConditionMode.NotEqual;
                default:
                    throw new ArgumentException(
                        $"Invalid condition mode: {modeString}. Must be If, IfNot, Greater, Less, Equals, or NotEqual");
            }
        }

        #endregion
    }
}
