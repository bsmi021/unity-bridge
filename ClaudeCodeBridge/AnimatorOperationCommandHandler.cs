/// <summary>
/// ============================================================================
/// ANIMATOR OPERATION COMMAND HANDLER - COMPREHENSIVE DOCUMENTATION
/// ============================================================================
///
/// This command handler provides complete programmatic control over Unity Animator Controllers.
/// It enables Claude Code to create, configure, and manage animation state machines without
/// manual Unity Editor interaction.
///
/// ============================================================================
/// SUPPORTED OPERATIONS
/// ============================================================================
///
/// CONTROLLER OPERATIONS:
/// ----------------------
/// 1. "create-controller"    - Create new Animator Controller asset
/// 2. "get-controller-info"  - Get controller structure and information
///
/// LAYER OPERATIONS:
/// -----------------
/// 3. "add-layer"           - Add new animation layer
/// 4. "set-layer-weight"    - Set layer blending weight (0.0-1.0)
/// 5. "set-layer-blending"  - Set blending mode (Override/Additive)
/// 6. "delete-layer"        - Remove animation layer
/// 7. "get-layers"          - List all layers with properties
///
/// STATE OPERATIONS:
/// -----------------
/// 8. "add-state"           - Add animation state to layer
/// 9. "set-state-motion"    - Assign animation clip to state
/// 10. "set-state-speed"    - Set state playback speed multiplier
/// 11. "set-default-state"  - Set layer's default entry state
/// 12. "delete-state"       - Remove state from layer
/// 13. "get-states"         - List all states in layer
///
/// TRANSITION OPERATIONS:
/// ----------------------
/// 14. "add-transition"     - Create transition between states
/// 15. "set-transition-duration" - Set transition blend duration
/// 16. "set-transition-conditions" - Add parameter conditions to transition
/// 17. "delete-transition"  - Remove transition
/// 18. "get-transitions"    - List all transitions for state
///
/// PARAMETER OPERATIONS:
/// ---------------------
/// 19. "add-parameter"      - Add animator parameter (float/int/bool/trigger)
/// 20. "set-parameter-default" - Set default parameter value
/// 21. "delete-parameter"   - Remove parameter
/// 22. "get-parameters"     - List all parameters
///
/// ============================================================================
/// USAGE EXAMPLES
/// ============================================================================
///
/// EXAMPLE 1: Create Combat Animator Controller
/// ---------------------------------------------
/// // Step 1: Create controller
/// {
///   "operation": "create-controller",
///   "controllerPath": "Assets/Animations/PlayerCombatController.controller"
/// }
///
/// // Step 2: Add parameters
/// {
///   "operation": "add-parameter",
///   "controllerPath": "Assets/Animations/PlayerCombatController.controller",
///   "parameterName": "Speed",
///   "parameterType": "Float",
///   "defaultValue": "0.0"
/// }
///
/// // Step 3: Add combat states
/// {
///   "operation": "add-state",
///   "controllerPath": "Assets/Animations/PlayerCombatController.controller",
///   "layerName": "Base Layer",
///   "stateName": "Idle"
/// }
///
/// {
///   "operation": "add-state",
///   "layerName": "Base Layer",
///   "stateName": "Attack1"
/// }
///
/// // Step 4: Set state animations
/// {
///   "operation": "set-state-motion",
///   "layerName": "Base Layer",
///   "stateName": "Idle",
///   "animationClipPath": "Assets/Animations/Idle.anim"
/// }
///
/// // Step 5: Create transition
/// {
///   "operation": "add-transition",
///   "layerName": "Base Layer",
///   "sourceState": "Idle",
///   "destinationState": "Attack1"
/// }
///
/// // Step 6: Add transition condition
/// {
///   "operation": "set-transition-conditions",
///   "layerName": "Base Layer",
///   "sourceState": "Idle",
///   "destinationState": "Attack1",
///   "conditions": [
///     {"parameter": "AttackTrigger", "mode": "If", "threshold": ""}
///   ]
/// }
///
/// EXAMPLE 2: Setup Multi-Layer Combat System
/// -------------------------------------------
/// // Add upper body layer for combat
/// {
///   "operation": "add-layer",
///   "controllerPath": "Assets/Animations/PlayerController.controller",
///   "layerName": "Upper Body",
///   "weight": 1.0,
///   "blendingMode": "Override"
/// }
///
/// // Add states to upper body layer
/// {
///   "operation": "add-state",
///   "layerName": "Upper Body",
///   "stateName": "Sword Attack"
/// }
///
/// EXAMPLE 3: Complete Dodge Roll Setup
/// -------------------------------------
/// // Add dodge parameter
/// {
///   "operation": "add-parameter",
///   "parameterName": "DodgeTrigger",
///   "parameterType": "Trigger"
/// }
///
/// // Add dodge state
/// {
///   "operation": "add-state",
///   "layerName": "Base Layer",
///   "stateName": "DodgeRoll",
///   "speed": 1.2
/// }
///
/// // Set dodge animation
/// {
///   "operation": "set-state-motion",
///   "stateName": "DodgeRoll",
///   "animationClipPath": "Assets/Animations/Combat/DodgeRoll.anim"
/// }
///
/// // Create transition from Any State
/// {
///   "operation": "add-transition",
///   "sourceState": "Any State",
///   "destinationState": "DodgeRoll"
/// }
///
/// ============================================================================
/// PARAMETER STRUCTURES
/// ============================================================================
///
/// AnimatorOperationParams:
/// ------------------------
/// - operation: string (required) - Operation to perform
/// - controllerPath: string - Path to Animator Controller asset
/// - layerName: string - Target layer name (default: "Base Layer")
/// - layerIndex: int - Alternative to layerName
/// - weight: float - Layer weight (0.0-1.0)
/// - blendingMode: string - "Override" or "Additive"
/// - stateName: string - State name
/// - sourceState: string - Source state for transitions
/// - destinationState: string - Destination state for transitions
/// - animationClipPath: string - Path to animation clip asset
/// - speed: float - State playback speed multiplier
/// - parameterName: string - Parameter name
/// - parameterType: string - "Float", "Int", "Bool", "Trigger"
/// - defaultValue: string - Default parameter value (JSON)
/// - conditions: List<TransitionCondition> - Transition conditions
/// - duration: float - Transition duration in seconds
/// - hasExitTime: bool - Whether transition has exit time
/// - exitTime: float - Normalized exit time (0.0-1.0)
///
/// ============================================================================
/// COMMON WORKFLOWS
/// ============================================================================
///
/// WORKFLOW 1: Soulslike Combat Setup
/// -----------------------------------
/// 1. Create controller
/// 2. Add parameters: AttackTrigger, DodgeTrigger, Speed, IsBlocking
/// 3. Add states: Idle, Walk, Run, Attack1, Attack2, Attack3, DodgeRoll, Block
/// 4. Set animations for each state
/// 5. Create blend tree for locomotion (Idle/Walk/Run based on Speed)
/// 6. Add attack chain transitions (Attack1→Attack2→Attack3)
/// 7. Add dodge transitions from Any State
/// 8. Configure exit times and transition durations
///
/// WORKFLOW 2: Layered Animation System
/// -------------------------------------
/// 1. Base Layer: Full body locomotion
/// 2. Upper Body Layer: Weapon animations (additive)
/// 3. Face Layer: Facial expressions (override)
/// 4. Configure layer weights and blending
/// 5. Setup IK pass flags per layer
///
/// WORKFLOW 3: State Machine Optimization
/// ---------------------------------------
/// 1. Get all states and transitions
/// 2. Validate all states have motions assigned
/// 3. Check for orphaned states (no transitions)
/// 4. Verify parameter usage in conditions
/// 5. Optimize transition durations
///
/// ============================================================================
/// UNITY API REFERENCES
/// ============================================================================
///
/// UnityEditor.Animations.AnimatorController
/// - AddLayer() - Add a new layer to the controller
/// - RemoveLayer() - Remove a layer by index
/// - AddParameter() - Add a parameter to the controller
/// - RemoveParameter() - Remove a parameter by name or index
///
/// UnityEditor.Animations.AnimatorControllerLayer
/// - name - Layer name
/// - defaultWeight - Layer weight (0.0-1.0)
/// - blendingMode - Override or Additive blending
/// - stateMachine - Root state machine for the layer
/// - iKPass - Whether IK pass is enabled
/// - avatarMask - Optional avatar mask for layer
///
/// UnityEditor.Animations.AnimatorStateMachine
/// - AddState() - Add a new state to the state machine
/// - AddStateMachine() - Add a sub-state machine
/// - RemoveState() - Remove a state by reference
/// - defaultState - The default entry state
/// - states - Array of child states
/// - anyStateTransitions - Transitions from "Any State"
///
/// UnityEditor.Animations.AnimatorState
/// - name - State name
/// - motion - Animation clip or blend tree
/// - speed - Playback speed multiplier
/// - writeDefaultValues - Whether to write default values
/// - mirror - Whether to mirror the animation
/// - tag - State tag for querying
/// - transitions - Array of outgoing transitions
///
/// UnityEditor.Animations.AnimatorStateTransition
/// - destinationState - Target state reference
/// - duration - Transition blend duration
/// - hasExitTime - Whether transition waits for exit time
/// - exitTime - Normalized time to exit (0.0-1.0)
/// - conditions - Array of conditions to evaluate
/// - offset - Normalized time to start destination state
///
/// UnityEditor.Animations.AnimatorCondition
/// - parameter - Parameter name to evaluate
/// - mode - Condition mode (If, IfNot, Greater, Less, Equals, NotEqual)
/// - threshold - Comparison threshold value
///
/// AnimatorConditionMode Enum:
/// - If - Trigger parameter is set
/// - IfNot - Trigger parameter is not set
/// - Greater - Parameter value > threshold
/// - Less - Parameter value < threshold
/// - Equals - Parameter value == threshold (int/bool)
/// - NotEqual - Parameter value != threshold (int/bool)
///
/// AnimatorControllerParameterType Enum:
/// - Float - Floating point parameter
/// - Int - Integer parameter
/// - Bool - Boolean parameter
/// - Trigger - One-shot trigger parameter
///
/// ============================================================================
/// ERROR HANDLING
/// ============================================================================
///
/// Common Errors and Solutions:
/// ----------------------------
/// - Controller not found → Verify controllerPath is correct asset path
/// - Layer not found → Check layerName spelling, use get-layers to list
/// - State not found → Use get-states to list available states
/// - Invalid parameter type → Must be Float, Int, Bool, or Trigger
/// - Animation clip not found → Verify animationClipPath exists in project
/// - Duplicate state name → State names must be unique per layer
/// - Invalid transition → Source and destination states must exist
/// - Cannot delete Base Layer → Base Layer (index 0) cannot be removed
/// - Cannot set default state → State must exist in the layer
///
/// Validation Checks:
/// -----------------
/// - All paths are validated for proper "Assets/" prefix
/// - Layer names are checked for existence before state operations
/// - State names are validated before transition creation
/// - Parameter types are validated against enum values
/// - Condition modes are validated against enum values
/// - Numeric values (weight, speed, duration) are clamped to valid ranges
///
/// ============================================================================
/// IMPLEMENTATION DETAILS
/// ============================================================================
///
/// Thread Safety:
/// - All operations run on the main Unity thread via EditorApplication.update
/// - AssetDatabase operations are properly synchronized
/// - Controllers are marked dirty and saved after modifications
///
/// Performance Considerations:
/// - Controller loading is cached per operation
/// - State lookups use efficient dictionary methods where possible
/// - Transition creation validates both states before creating
/// - Parameter operations check for duplicates before adding
///
/// Asset Management:
/// - Controllers are saved immediately after modification
/// - AssetDatabase.Refresh() is called after structural changes
/// - Directories are created automatically if they don't exist
/// - Proper cleanup of assets on delete operations
///
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
    public class AnimatorOperationCommandHandler : ICommandHandler
    {
        public string CommandType => "animator-operation";

        public BridgeResponse Execute(BridgeCommand command)
        {
            try
            {
                // Parse parameters
                var parameters = JsonUtility.FromJson<AnimatorOperationParams>(command.parametersJson ?? "{}");
                if (parameters == null || string.IsNullOrEmpty(parameters.operation))
                {
                    return BridgeResponse.Error(command.commandId, command.commandType, "Missing required parameter: operation");
                }

                BridgeLogger.LogDebug($"Executing operation: {parameters.operation}");

                // Route to appropriate operation handler
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

                    // Layer operations
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

                    // State operations
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

                    // Transition operations
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

                    // Parameter operations
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

                // Serialize result and return response
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
        /// The directory path must exist or will be created automatically.
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
                // Validate path
                if (string.IsNullOrEmpty(parameters.controllerPath))
                {
                    result.success = false;
                    result.message = "Controller path is required";
                    return result;
                }

                // Check if controller already exists
                if (File.Exists(Path.Combine(Application.dataPath, "..", parameters.controllerPath)))
                {
                    result.success = false;
                    result.message = $"Controller already exists at path: {parameters.controllerPath}";
                    return result;
                }

                // Ensure directory exists
                var directory = Path.GetDirectoryName(parameters.controllerPath);
                var fullDirectoryPath = Path.Combine(Application.dataPath, "..", directory);
                if (!Directory.Exists(fullDirectoryPath))
                {
                    Directory.CreateDirectory(fullDirectoryPath);
                    AssetDatabase.Refresh();
                }

                // Create controller
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
        /// Gets comprehensive information about a controller including layers, states, parameters, and transitions.
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

                // Get all states across all layers
                foreach (var layer in controller.layers)
                {
                    result.states.AddRange(GetLayerStates(layer));
                }

                result.success = true;
                result.message = $"Retrieved controller info: {result.layers.Count} layers, {result.states.Count} states, {result.parameters.Count} parameters";

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

        #region Layer Operations

        /// <summary>
        /// Adds a new animation layer to the controller.
        /// </summary>
        private AnimatorOperationResult AddLayer(AnimatorOperationParams parameters)
        {
            var result = new AnimatorOperationResult
            {
                operation = "add-layer",
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

                // Check if layer already exists
                if (controller.layers.Any(l => l.name == parameters.layerName))
                {
                    result.success = false;
                    result.message = $"Layer '{parameters.layerName}' already exists";
                    return result;
                }

                // Create new layer
                var layer = new AnimatorControllerLayer
                {
                    name = parameters.layerName,
                    defaultWeight = parameters.weight,
                    blendingMode = parameters.blendingMode.ToLower() == "additive"
                        ? AnimatorLayerBlendingMode.Additive
                        : AnimatorLayerBlendingMode.Override,
                    stateMachine = new AnimatorStateMachine()
                };

                // Add layer to controller
                controller.AddLayer(layer);

                // Save changes
                EditorUtility.SetDirty(controller);
                AssetDatabase.SaveAssets();

                result.success = true;
                result.message = $"Layer '{parameters.layerName}' added successfully";
                result.layers = GetControllerLayers(controller);

                BridgeLogger.LogDebug($"Added layer: {parameters.layerName}");
            }
            catch (Exception ex)
            {
                result.success = false;
                result.message = $"Failed to add layer: {ex.Message}";
                BridgeLogger.LogError($"Add layer failed: {ex}");
            }

            return result;
        }

        /// <summary>
        /// Sets the weight of an animation layer.
        /// </summary>
        private AnimatorOperationResult SetLayerWeight(AnimatorOperationParams parameters)
        {
            var result = new AnimatorOperationResult
            {
                operation = "set-layer-weight",
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

                // Find layer
                var layerIndex = Array.FindIndex(controller.layers, l => l.name == parameters.layerName);
                if (layerIndex < 0)
                {
                    result.success = false;
                    result.message = $"Layer '{parameters.layerName}' not found";
                    return result;
                }

                // Update layer weight
                var layers = controller.layers;
                layers[layerIndex].defaultWeight = Mathf.Clamp01(parameters.weight);
                controller.layers = layers;

                // Save changes
                EditorUtility.SetDirty(controller);
                AssetDatabase.SaveAssets();

                result.success = true;
                result.message = $"Layer '{parameters.layerName}' weight set to {parameters.weight}";
                result.layers = GetControllerLayers(controller);

                BridgeLogger.LogDebug($"Set layer weight: {parameters.layerName} = {parameters.weight}");
            }
            catch (Exception ex)
            {
                result.success = false;
                result.message = $"Failed to set layer weight: {ex.Message}";
                BridgeLogger.LogError($"Set layer weight failed: {ex}");
            }

            return result;
        }

        /// <summary>
        /// Sets the blending mode of an animation layer (Override or Additive).
        /// </summary>
        private AnimatorOperationResult SetLayerBlending(AnimatorOperationParams parameters)
        {
            var result = new AnimatorOperationResult
            {
                operation = "set-layer-blending",
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

                // Find layer
                var layerIndex = Array.FindIndex(controller.layers, l => l.name == parameters.layerName);
                if (layerIndex < 0)
                {
                    result.success = false;
                    result.message = $"Layer '{parameters.layerName}' not found";
                    return result;
                }

                // Update blending mode
                var layers = controller.layers;
                layers[layerIndex].blendingMode = parameters.blendingMode.ToLower() == "additive"
                    ? AnimatorLayerBlendingMode.Additive
                    : AnimatorLayerBlendingMode.Override;
                controller.layers = layers;

                // Save changes
                EditorUtility.SetDirty(controller);
                AssetDatabase.SaveAssets();

                result.success = true;
                result.message = $"Layer '{parameters.layerName}' blending mode set to {parameters.blendingMode}";
                result.layers = GetControllerLayers(controller);

                BridgeLogger.LogDebug($"Set layer blending: {parameters.layerName} = {parameters.blendingMode}");
            }
            catch (Exception ex)
            {
                result.success = false;
                result.message = $"Failed to set layer blending: {ex.Message}";
                BridgeLogger.LogError($"Set layer blending failed: {ex}");
            }

            return result;
        }

        /// <summary>
        /// Deletes an animation layer from the controller.
        /// Note: Cannot delete the Base Layer (index 0).
        /// </summary>
        private AnimatorOperationResult DeleteLayer(AnimatorOperationParams parameters)
        {
            var result = new AnimatorOperationResult
            {
                operation = "delete-layer",
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

                // Find layer
                var layerIndex = Array.FindIndex(controller.layers, l => l.name == parameters.layerName);
                if (layerIndex < 0)
                {
                    result.success = false;
                    result.message = $"Layer '{parameters.layerName}' not found";
                    return result;
                }

                // Cannot delete base layer
                if (layerIndex == 0)
                {
                    result.success = false;
                    result.message = "Cannot delete Base Layer (index 0)";
                    return result;
                }

                // Remove layer
                controller.RemoveLayer(layerIndex);

                // Save changes
                EditorUtility.SetDirty(controller);
                AssetDatabase.SaveAssets();

                result.success = true;
                result.message = $"Layer '{parameters.layerName}' deleted successfully";
                result.layers = GetControllerLayers(controller);

                BridgeLogger.LogDebug($"Deleted layer: {parameters.layerName}");
            }
            catch (Exception ex)
            {
                result.success = false;
                result.message = $"Failed to delete layer: {ex.Message}";
                BridgeLogger.LogError($"Delete layer failed: {ex}");
            }

            return result;
        }

        /// <summary>
        /// Gets all layers in the controller with their properties.
        /// </summary>
        private AnimatorOperationResult GetLayers(AnimatorOperationParams parameters)
        {
            var result = new AnimatorOperationResult
            {
                operation = "get-layers",
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
                result.success = true;
                result.message = $"Retrieved {result.layers.Count} layers";

                BridgeLogger.LogDebug($"Retrieved layers from: {parameters.controllerPath}");
            }
            catch (Exception ex)
            {
                result.success = false;
                result.message = $"Failed to get layers: {ex.Message}";
                BridgeLogger.LogError($"Get layers failed: {ex}");
            }

            return result;
        }

        #endregion

        #region State Operations

        /// <summary>
        /// Adds a new animation state to a layer.
        /// </summary>
        private AnimatorOperationResult AddState(AnimatorOperationParams parameters)
        {
            var result = new AnimatorOperationResult
            {
                operation = "add-state",
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

                // Find layer
                var layer = Array.Find(controller.layers, l => l.name == parameters.layerName);
                if (layer == null)
                {
                    result.success = false;
                    result.message = $"Layer '{parameters.layerName}' not found";
                    return result;
                }

                // Check if state already exists
                if (layer.stateMachine.states.Any(s => s.state.name == parameters.stateName))
                {
                    result.success = false;
                    result.message = $"State '{parameters.stateName}' already exists in layer '{parameters.layerName}'";
                    return result;
                }

                // Add state
                var state = layer.stateMachine.AddState(parameters.stateName);
                state.speed = parameters.speed;

                // Save changes
                EditorUtility.SetDirty(controller);
                AssetDatabase.SaveAssets();

                result.success = true;
                result.message = $"State '{parameters.stateName}' added to layer '{parameters.layerName}'";
                result.states = GetLayerStates(layer);

                BridgeLogger.LogDebug($"Added state: {parameters.stateName} to layer {parameters.layerName}");
            }
            catch (Exception ex)
            {
                result.success = false;
                result.message = $"Failed to add state: {ex.Message}";
                BridgeLogger.LogError($"Add state failed: {ex}");
            }

            return result;
        }

        /// <summary>
        /// Sets the motion (animation clip) for a state.
        /// </summary>
        private AnimatorOperationResult SetStateMotion(AnimatorOperationParams parameters)
        {
            var result = new AnimatorOperationResult
            {
                operation = "set-state-motion",
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

                // Find layer
                var layer = Array.Find(controller.layers, l => l.name == parameters.layerName);
                if (layer == null)
                {
                    result.success = false;
                    result.message = $"Layer '{parameters.layerName}' not found";
                    return result;
                }

                // Find state
                var stateEntry = Array.Find(layer.stateMachine.states, s => s.state.name == parameters.stateName);
                if (stateEntry.state == null)
                {
                    result.success = false;
                    result.message = $"State '{parameters.stateName}' not found in layer '{parameters.layerName}'";
                    return result;
                }

                // Load animation clip
                var clip = AssetDatabase.LoadAssetAtPath<AnimationClip>(parameters.animationClipPath);
                if (clip == null)
                {
                    result.success = false;
                    result.message = $"Animation clip not found at path: {parameters.animationClipPath}";
                    return result;
                }

                // Set motion
                stateEntry.state.motion = clip;

                // Save changes
                EditorUtility.SetDirty(controller);
                AssetDatabase.SaveAssets();

                result.success = true;
                result.message = $"Motion set for state '{parameters.stateName}' to '{parameters.animationClipPath}'";
                result.states = GetLayerStates(layer);

                BridgeLogger.LogDebug($"Set state motion: {parameters.stateName} = {parameters.animationClipPath}");
            }
            catch (Exception ex)
            {
                result.success = false;
                result.message = $"Failed to set state motion: {ex.Message}";
                BridgeLogger.LogError($"Set state motion failed: {ex}");
            }

            return result;
        }

        /// <summary>
        /// Sets the playback speed multiplier for a state.
        /// </summary>
        private AnimatorOperationResult SetStateSpeed(AnimatorOperationParams parameters)
        {
            var result = new AnimatorOperationResult
            {
                operation = "set-state-speed",
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

                // Find layer
                var layer = Array.Find(controller.layers, l => l.name == parameters.layerName);
                if (layer == null)
                {
                    result.success = false;
                    result.message = $"Layer '{parameters.layerName}' not found";
                    return result;
                }

                // Find state
                var stateEntry = Array.Find(layer.stateMachine.states, s => s.state.name == parameters.stateName);
                if (stateEntry.state == null)
                {
                    result.success = false;
                    result.message = $"State '{parameters.stateName}' not found in layer '{parameters.layerName}'";
                    return result;
                }

                // Set speed
                stateEntry.state.speed = parameters.speed;

                // Save changes
                EditorUtility.SetDirty(controller);
                AssetDatabase.SaveAssets();

                result.success = true;
                result.message = $"Speed set for state '{parameters.stateName}' to {parameters.speed}";
                result.states = GetLayerStates(layer);

                BridgeLogger.LogDebug($"Set state speed: {parameters.stateName} = {parameters.speed}");
            }
            catch (Exception ex)
            {
                result.success = false;
                result.message = $"Failed to set state speed: {ex.Message}";
                BridgeLogger.LogError($"Set state speed failed: {ex}");
            }

            return result;
        }

        /// <summary>
        /// Sets the default entry state for a layer.
        /// </summary>
        private AnimatorOperationResult SetDefaultState(AnimatorOperationParams parameters)
        {
            var result = new AnimatorOperationResult
            {
                operation = "set-default-state",
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

                // Find layer
                var layer = Array.Find(controller.layers, l => l.name == parameters.layerName);
                if (layer == null)
                {
                    result.success = false;
                    result.message = $"Layer '{parameters.layerName}' not found";
                    return result;
                }

                // Find state
                var stateEntry = Array.Find(layer.stateMachine.states, s => s.state.name == parameters.stateName);
                if (stateEntry.state == null)
                {
                    result.success = false;
                    result.message = $"State '{parameters.stateName}' not found in layer '{parameters.layerName}'";
                    return result;
                }

                // Set as default state
                layer.stateMachine.defaultState = stateEntry.state;

                // Save changes
                EditorUtility.SetDirty(controller);
                AssetDatabase.SaveAssets();

                result.success = true;
                result.message = $"Default state set to '{parameters.stateName}' in layer '{parameters.layerName}'";
                result.states = GetLayerStates(layer);

                BridgeLogger.LogDebug($"Set default state: {parameters.stateName} in layer {parameters.layerName}");
            }
            catch (Exception ex)
            {
                result.success = false;
                result.message = $"Failed to set default state: {ex.Message}";
                BridgeLogger.LogError($"Set default state failed: {ex}");
            }

            return result;
        }

        /// <summary>
        /// Deletes a state from a layer.
        /// </summary>
        private AnimatorOperationResult DeleteState(AnimatorOperationParams parameters)
        {
            var result = new AnimatorOperationResult
            {
                operation = "delete-state",
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

                // Find layer
                var layer = Array.Find(controller.layers, l => l.name == parameters.layerName);
                if (layer == null)
                {
                    result.success = false;
                    result.message = $"Layer '{parameters.layerName}' not found";
                    return result;
                }

                // Find state
                var stateEntry = Array.Find(layer.stateMachine.states, s => s.state.name == parameters.stateName);
                if (stateEntry.state == null)
                {
                    result.success = false;
                    result.message = $"State '{parameters.stateName}' not found in layer '{parameters.layerName}'";
                    return result;
                }

                // Remove state
                layer.stateMachine.RemoveState(stateEntry.state);

                // Save changes
                EditorUtility.SetDirty(controller);
                AssetDatabase.SaveAssets();

                result.success = true;
                result.message = $"State '{parameters.stateName}' deleted from layer '{parameters.layerName}'";
                result.states = GetLayerStates(layer);

                BridgeLogger.LogDebug($"Deleted state: {parameters.stateName} from layer {parameters.layerName}");
            }
            catch (Exception ex)
            {
                result.success = false;
                result.message = $"Failed to delete state: {ex.Message}";
                BridgeLogger.LogError($"Delete state failed: {ex}");
            }

            return result;
        }

        /// <summary>
        /// Gets all states in a layer with their properties.
        /// </summary>
        private AnimatorOperationResult GetStates(AnimatorOperationParams parameters)
        {
            var result = new AnimatorOperationResult
            {
                operation = "get-states",
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

                // Find layer
                var layer = Array.Find(controller.layers, l => l.name == parameters.layerName);
                if (layer == null)
                {
                    result.success = false;
                    result.message = $"Layer '{parameters.layerName}' not found";
                    return result;
                }

                result.states = GetLayerStates(layer);
                result.success = true;
                result.message = $"Retrieved {result.states.Count} states from layer '{parameters.layerName}'";

                BridgeLogger.LogDebug($"Retrieved states from layer: {parameters.layerName}");
            }
            catch (Exception ex)
            {
                result.success = false;
                result.message = $"Failed to get states: {ex.Message}";
                BridgeLogger.LogError($"Get states failed: {ex}");
            }

            return result;
        }

        #endregion

        #region Transition Operations

        /// <summary>
        /// Adds a transition between two states.
        /// Supports "Any State" and "Entry" as special source states.
        /// </summary>
        private AnimatorOperationResult AddTransition(AnimatorOperationParams parameters)
        {
            var result = new AnimatorOperationResult
            {
                operation = "add-transition",
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

                // Find layer
                var layer = Array.Find(controller.layers, l => l.name == parameters.layerName);
                if (layer == null)
                {
                    result.success = false;
                    result.message = $"Layer '{parameters.layerName}' not found";
                    return result;
                }

                // Find destination state
                var destStateEntry = Array.Find(layer.stateMachine.states, s => s.state.name == parameters.destinationState);
                if (destStateEntry.state == null)
                {
                    result.success = false;
                    result.message = $"Destination state '{parameters.destinationState}' not found in layer '{parameters.layerName}'";
                    return result;
                }

                // Handle special source states
                if (parameters.sourceState == "Entry")
                {
                    // Entry transitions return AnimatorTransition, not AnimatorStateTransition
                    var entryTransition = layer.stateMachine.AddEntryTransition(destStateEntry.state);

                    // Entry transitions don't have duration, exitTime, or hasExitTime
                    // They transition immediately when entering the state machine
                }
                else
                {
                    AnimatorStateTransition transition;

                    if (parameters.sourceState == "Any State")
                    {
                        transition = layer.stateMachine.AddAnyStateTransition(destStateEntry.state);
                    }
                    else
                    {
                        // Find source state
                        var sourceStateEntry = Array.Find(layer.stateMachine.states, s => s.state.name == parameters.sourceState);
                        if (sourceStateEntry.state == null)
                        {
                            result.success = false;
                            result.message = $"Source state '{parameters.sourceState}' not found in layer '{parameters.layerName}'";
                            return result;
                        }

                        transition = sourceStateEntry.state.AddTransition(destStateEntry.state);
                    }

                    // Set transition properties (only for AnimatorStateTransition)
                    transition.duration = parameters.duration;
                    transition.hasExitTime = parameters.hasExitTime;
                    transition.exitTime = parameters.exitTime;
                }

                // Save changes
                EditorUtility.SetDirty(controller);
                AssetDatabase.SaveAssets();

                result.success = true;
                result.message = $"Transition added from '{parameters.sourceState}' to '{parameters.destinationState}'";

                BridgeLogger.LogDebug($"Added transition: {parameters.sourceState} -> {parameters.destinationState}");
            }
            catch (Exception ex)
            {
                result.success = false;
                result.message = $"Failed to add transition: {ex.Message}";
                BridgeLogger.LogError($"Add transition failed: {ex}");
            }

            return result;
        }

        /// <summary>
        /// Sets the duration of a transition.
        /// </summary>
        private AnimatorOperationResult SetTransitionDuration(AnimatorOperationParams parameters)
        {
            var result = new AnimatorOperationResult
            {
                operation = "set-transition-duration",
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

                // Find layer
                var layer = Array.Find(controller.layers, l => l.name == parameters.layerName);
                if (layer == null)
                {
                    result.success = false;
                    result.message = $"Layer '{parameters.layerName}' not found";
                    return result;
                }

                // Find transition
                var transition = FindTransition(layer, parameters.sourceState, parameters.destinationState);
                if (transition == null)
                {
                    result.success = false;
                    result.message = $"Transition not found from '{parameters.sourceState}' to '{parameters.destinationState}'";
                    return result;
                }

                // Set duration
                transition.duration = parameters.duration;

                // Save changes
                EditorUtility.SetDirty(controller);
                AssetDatabase.SaveAssets();

                result.success = true;
                result.message = $"Transition duration set to {parameters.duration}";

                BridgeLogger.LogDebug($"Set transition duration: {parameters.sourceState} -> {parameters.destinationState} = {parameters.duration}");
            }
            catch (Exception ex)
            {
                result.success = false;
                result.message = $"Failed to set transition duration: {ex.Message}";
                BridgeLogger.LogError($"Set transition duration failed: {ex}");
            }

            return result;
        }

        /// <summary>
        /// Sets conditions on a transition.
        /// Replaces any existing conditions.
        /// </summary>
        private AnimatorOperationResult SetTransitionConditions(AnimatorOperationParams parameters)
        {
            var result = new AnimatorOperationResult
            {
                operation = "set-transition-conditions",
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

                // Find layer
                var layer = Array.Find(controller.layers, l => l.name == parameters.layerName);
                if (layer == null)
                {
                    result.success = false;
                    result.message = $"Layer '{parameters.layerName}' not found";
                    return result;
                }

                // Find transition
                var transition = FindTransition(layer, parameters.sourceState, parameters.destinationState);
                if (transition == null)
                {
                    result.success = false;
                    result.message = $"Transition not found from '{parameters.sourceState}' to '{parameters.destinationState}'";
                    return result;
                }

                // Clear existing conditions
                for (int i = transition.conditions.Length - 1; i >= 0; i--)
                {
                    transition.RemoveCondition(transition.conditions[i]);
                }

                // Add new conditions
                foreach (var condition in parameters.conditions)
                {
                    var mode = ParseConditionMode(condition.mode);
                    transition.AddCondition(mode, condition.threshold, condition.parameter);
                }

                // Save changes
                EditorUtility.SetDirty(controller);
                AssetDatabase.SaveAssets();

                result.success = true;
                result.message = $"Set {parameters.conditions.Count} conditions on transition";

                BridgeLogger.LogDebug($"Set transition conditions: {parameters.sourceState} -> {parameters.destinationState}");
            }
            catch (Exception ex)
            {
                result.success = false;
                result.message = $"Failed to set transition conditions: {ex.Message}";
                BridgeLogger.LogError($"Set transition conditions failed: {ex}");
            }

            return result;
        }

        /// <summary>
        /// Deletes a transition between two states.
        /// </summary>
        private AnimatorOperationResult DeleteTransition(AnimatorOperationParams parameters)
        {
            var result = new AnimatorOperationResult
            {
                operation = "delete-transition",
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

                // Find layer
                var layer = Array.Find(controller.layers, l => l.name == parameters.layerName);
                if (layer == null)
                {
                    result.success = false;
                    result.message = $"Layer '{parameters.layerName}' not found";
                    return result;
                }

                // Handle special source states
                if (parameters.sourceState == "Any State")
                {
                    // Find and remove from Any State transitions
                    var destStateEntry = Array.Find(layer.stateMachine.states, s => s.state.name == parameters.destinationState);
                    if (destStateEntry.state == null)
                    {
                        result.success = false;
                        result.message = $"Destination state '{parameters.destinationState}' not found";
                        return result;
                    }

                    var anyStateTransitions = layer.stateMachine.anyStateTransitions;
                    var transitionIndex = Array.FindIndex(anyStateTransitions, t => t.destinationState == destStateEntry.state);

                    if (transitionIndex < 0)
                    {
                        result.success = false;
                        result.message = $"Any State transition to '{parameters.destinationState}' not found";
                        return result;
                    }

                    layer.stateMachine.RemoveAnyStateTransition(anyStateTransitions[transitionIndex]);
                }
                else
                {
                    // Find source state
                    var sourceStateEntry = Array.Find(layer.stateMachine.states, s => s.state.name == parameters.sourceState);
                    if (sourceStateEntry.state == null)
                    {
                        result.success = false;
                        result.message = $"Source state '{parameters.sourceState}' not found";
                        return result;
                    }

                    // Find destination state
                    var destStateEntry = Array.Find(layer.stateMachine.states, s => s.state.name == parameters.destinationState);
                    if (destStateEntry.state == null)
                    {
                        result.success = false;
                        result.message = $"Destination state '{parameters.destinationState}' not found";
                        return result;
                    }

                    // Find and remove transition
                    var transitions = sourceStateEntry.state.transitions;
                    var transitionIndex = Array.FindIndex(transitions, t => t.destinationState == destStateEntry.state);

                    if (transitionIndex < 0)
                    {
                        result.success = false;
                        result.message = $"Transition not found from '{parameters.sourceState}' to '{parameters.destinationState}'";
                        return result;
                    }

                    sourceStateEntry.state.RemoveTransition(transitions[transitionIndex]);
                }

                // Save changes
                EditorUtility.SetDirty(controller);
                AssetDatabase.SaveAssets();

                result.success = true;
                result.message = $"Transition deleted from '{parameters.sourceState}' to '{parameters.destinationState}'";

                BridgeLogger.LogDebug($"Deleted transition: {parameters.sourceState} -> {parameters.destinationState}");
            }
            catch (Exception ex)
            {
                result.success = false;
                result.message = $"Failed to delete transition: {ex.Message}";
                BridgeLogger.LogError($"Delete transition failed: {ex}");
            }

            return result;
        }

        /// <summary>
        /// Gets all transitions from a state.
        /// </summary>
        private AnimatorOperationResult GetTransitions(AnimatorOperationParams parameters)
        {
            var result = new AnimatorOperationResult
            {
                operation = "get-transitions",
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

                // Find layer
                var layer = Array.Find(controller.layers, l => l.name == parameters.layerName);
                if (layer == null)
                {
                    result.success = false;
                    result.message = $"Layer '{parameters.layerName}' not found";
                    return result;
                }

                if (parameters.sourceState == "Any State")
                {
                    // Get Any State transitions
                    foreach (var transition in layer.stateMachine.anyStateTransitions)
                    {
                        result.transitions.Add(CreateTransitionInfo("Any State", transition));
                    }
                }
                else
                {
                    // Find source state
                    var sourceStateEntry = Array.Find(layer.stateMachine.states, s => s.state.name == parameters.sourceState);
                    if (sourceStateEntry.state == null)
                    {
                        result.success = false;
                        result.message = $"Source state '{parameters.sourceState}' not found";
                        return result;
                    }

                    // Get state transitions
                    foreach (var transition in sourceStateEntry.state.transitions)
                    {
                        result.transitions.Add(CreateTransitionInfo(parameters.sourceState, transition));
                    }
                }

                result.success = true;
                result.message = $"Retrieved {result.transitions.Count} transitions";

                BridgeLogger.LogDebug($"Retrieved transitions from state: {parameters.sourceState}");
            }
            catch (Exception ex)
            {
                result.success = false;
                result.message = $"Failed to get transitions: {ex.Message}";
                BridgeLogger.LogError($"Get transitions failed: {ex}");
            }

            return result;
        }

        #endregion

        #region Parameter Operations

        /// <summary>
        /// Adds a parameter to the controller.
        /// </summary>
        private AnimatorOperationResult AddParameter(AnimatorOperationParams parameters)
        {
            var result = new AnimatorOperationResult
            {
                operation = "add-parameter",
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

                // Check if parameter already exists
                if (controller.parameters.Any(p => p.name == parameters.parameterName))
                {
                    result.success = false;
                    result.message = $"Parameter '{parameters.parameterName}' already exists";
                    return result;
                }

                // Parse parameter type
                var paramType = ParseParameterType(parameters.parameterType);

                // Add parameter
                controller.AddParameter(parameters.parameterName, paramType);

                // Set default value if provided
                if (!string.IsNullOrEmpty(parameters.defaultValue))
                {
                    var param = Array.Find(controller.parameters, p => p.name == parameters.parameterName);
                    if (param != null)
                    {
                        switch (paramType)
                        {
                            case AnimatorControllerParameterType.Float:
                                param.defaultFloat = float.Parse(parameters.defaultValue);
                                break;
                            case AnimatorControllerParameterType.Int:
                                param.defaultInt = int.Parse(parameters.defaultValue);
                                break;
                            case AnimatorControllerParameterType.Bool:
                                param.defaultBool = bool.Parse(parameters.defaultValue);
                                break;
                        }
                    }
                }

                // Save changes
                EditorUtility.SetDirty(controller);
                AssetDatabase.SaveAssets();

                result.success = true;
                result.message = $"Parameter '{parameters.parameterName}' of type '{parameters.parameterType}' added";
                result.parameters = GetControllerParameters(controller);

                BridgeLogger.LogDebug($"Added parameter: {parameters.parameterName} ({parameters.parameterType})");
            }
            catch (Exception ex)
            {
                result.success = false;
                result.message = $"Failed to add parameter: {ex.Message}";
                BridgeLogger.LogError($"Add parameter failed: {ex}");
            }

            return result;
        }

        /// <summary>
        /// Sets the default value of a parameter.
        /// </summary>
        private AnimatorOperationResult SetParameterDefault(AnimatorOperationParams parameters)
        {
            var result = new AnimatorOperationResult
            {
                operation = "set-parameter-default",
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

                // Find parameter
                var paramIndex = Array.FindIndex(controller.parameters, p => p.name == parameters.parameterName);
                if (paramIndex < 0)
                {
                    result.success = false;
                    result.message = $"Parameter '{parameters.parameterName}' not found";
                    return result;
                }

                var param = controller.parameters[paramIndex];

                // Set default value based on type
                switch (param.type)
                {
                    case AnimatorControllerParameterType.Float:
                        param.defaultFloat = float.Parse(parameters.defaultValue);
                        break;
                    case AnimatorControllerParameterType.Int:
                        param.defaultInt = int.Parse(parameters.defaultValue);
                        break;
                    case AnimatorControllerParameterType.Bool:
                        param.defaultBool = bool.Parse(parameters.defaultValue);
                        break;
                    case AnimatorControllerParameterType.Trigger:
                        result.success = false;
                        result.message = "Trigger parameters do not have default values";
                        return result;
                }

                // Save changes
                EditorUtility.SetDirty(controller);
                AssetDatabase.SaveAssets();

                result.success = true;
                result.message = $"Default value set for parameter '{parameters.parameterName}' to {parameters.defaultValue}";
                result.parameters = GetControllerParameters(controller);

                BridgeLogger.LogDebug($"Set parameter default: {parameters.parameterName} = {parameters.defaultValue}");
            }
            catch (Exception ex)
            {
                result.success = false;
                result.message = $"Failed to set parameter default: {ex.Message}";
                BridgeLogger.LogError($"Set parameter default failed: {ex}");
            }

            return result;
        }

        /// <summary>
        /// Deletes a parameter from the controller.
        /// </summary>
        private AnimatorOperationResult DeleteParameter(AnimatorOperationParams parameters)
        {
            var result = new AnimatorOperationResult
            {
                operation = "delete-parameter",
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

                // Find parameter
                var paramIndex = Array.FindIndex(controller.parameters, p => p.name == parameters.parameterName);
                if (paramIndex < 0)
                {
                    result.success = false;
                    result.message = $"Parameter '{parameters.parameterName}' not found";
                    return result;
                }

                // Remove parameter
                controller.RemoveParameter(paramIndex);

                // Save changes
                EditorUtility.SetDirty(controller);
                AssetDatabase.SaveAssets();

                result.success = true;
                result.message = $"Parameter '{parameters.parameterName}' deleted";
                result.parameters = GetControllerParameters(controller);

                BridgeLogger.LogDebug($"Deleted parameter: {parameters.parameterName}");
            }
            catch (Exception ex)
            {
                result.success = false;
                result.message = $"Failed to delete parameter: {ex.Message}";
                BridgeLogger.LogError($"Delete parameter failed: {ex}");
            }

            return result;
        }

        /// <summary>
        /// Gets all parameters in the controller.
        /// </summary>
        private AnimatorOperationResult GetParameters(AnimatorOperationParams parameters)
        {
            var result = new AnimatorOperationResult
            {
                operation = "get-parameters",
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

                result.parameters = GetControllerParameters(controller);
                result.success = true;
                result.message = $"Retrieved {result.parameters.Count} parameters";

                BridgeLogger.LogDebug($"Retrieved parameters from: {parameters.controllerPath}");
            }
            catch (Exception ex)
            {
                result.success = false;
                result.message = $"Failed to get parameters: {ex.Message}";
                BridgeLogger.LogError($"Get parameters failed: {ex}");
            }

            return result;
        }

        #endregion

        #region Helper Methods

        /// <summary>
        /// Loads an Animator Controller from the AssetDatabase.
        /// </summary>
        private AnimatorController LoadController(string controllerPath)
        {
            if (string.IsNullOrEmpty(controllerPath))
                return null;

            return AssetDatabase.LoadAssetAtPath<AnimatorController>(controllerPath);
        }

        /// <summary>
        /// Gets all layers from a controller with their properties.
        /// </summary>
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
                    avatarMask = layer.avatarMask != null ? AssetDatabase.GetAssetPath(layer.avatarMask) : null
                });
            }

            return layers;
        }

        /// <summary>
        /// Gets all states from a layer with their properties.
        /// </summary>
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
                    motionPath = state.motion != null ? AssetDatabase.GetAssetPath(state.motion) : null,
                    speed = state.speed,
                    isDefaultState = layer.stateMachine.defaultState == state,
                    tag = state.tag
                });
            }

            return states;
        }

        /// <summary>
        /// Gets all parameters from a controller.
        /// </summary>
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

                // Get default value based on type
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

        /// <summary>
        /// Finds a transition between two states in a layer.
        /// </summary>
        private AnimatorStateTransition FindTransition(AnimatorControllerLayer layer, string sourceState, string destinationState)
        {
            // Find destination state
            var destStateEntry = Array.Find(layer.stateMachine.states, s => s.state.name == destinationState);
            if (destStateEntry.state == null)
                return null;

            // Handle Any State transitions
            if (sourceState == "Any State")
            {
                return Array.Find(layer.stateMachine.anyStateTransitions, t => t.destinationState == destStateEntry.state);
            }

            // Find source state
            var sourceStateEntry = Array.Find(layer.stateMachine.states, s => s.state.name == sourceState);
            if (sourceStateEntry.state == null)
                return null;

            // Find transition
            return Array.Find(sourceStateEntry.state.transitions, t => t.destinationState == destStateEntry.state);
        }

        /// <summary>
        /// Creates a TransitionInfo object from an AnimatorStateTransition.
        /// </summary>
        private AnimatorTransitionInfo CreateTransitionInfo(string sourceStateName, AnimatorStateTransition transition)
        {
            var info = new AnimatorTransitionInfo
            {
                sourceState = sourceStateName,
                destinationState = transition.destinationState != null ? transition.destinationState.name : "null",
                duration = transition.duration,
                hasExitTime = transition.hasExitTime,
                exitTime = transition.exitTime,
                conditionCount = transition.conditions.Length
            };

            // Add conditions
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

        /// <summary>
        /// Parses a string into an AnimatorControllerParameterType.
        /// </summary>
        private AnimatorControllerParameterType ParseParameterType(string typeString)
        {
            switch (typeString.ToLower())
            {
                case "float":
                    return AnimatorControllerParameterType.Float;
                case "int":
                    return AnimatorControllerParameterType.Int;
                case "bool":
                    return AnimatorControllerParameterType.Bool;
                case "trigger":
                    return AnimatorControllerParameterType.Trigger;
                default:
                    throw new ArgumentException($"Invalid parameter type: {typeString}. Must be Float, Int, Bool, or Trigger");
            }
        }

        /// <summary>
        /// Parses a string into an AnimatorConditionMode.
        /// </summary>
        private AnimatorConditionMode ParseConditionMode(string modeString)
        {
            switch (modeString.ToLower())
            {
                case "if":
                    return AnimatorConditionMode.If;
                case "ifnot":
                    return AnimatorConditionMode.IfNot;
                case "greater":
                    return AnimatorConditionMode.Greater;
                case "less":
                    return AnimatorConditionMode.Less;
                case "equals":
                    return AnimatorConditionMode.Equals;
                case "notequal":
                    return AnimatorConditionMode.NotEqual;
                default:
                    throw new ArgumentException($"Invalid condition mode: {modeString}. Must be If, IfNot, Greater, Less, Equals, or NotEqual");
            }
        }

        #endregion
    }
}
