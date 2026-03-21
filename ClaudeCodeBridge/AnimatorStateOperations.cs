using System;
using System.Collections.Generic;
using System.Linq;
using UnityEditor;
using UnityEditor.Animations;
using UnityEngine;

namespace BWS.Editor.ClaudeCodeBridge
{
    /// <summary>
    /// Partial class: state operations for AnimatorOperationCommandHandler.
    /// </summary>
    public partial class AnimatorOperationCommandHandler
    {
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

                var layer = Array.Find(controller.layers, l => l.name == parameters.layerName);
                if (layer == null)
                {
                    result.success = false;
                    result.message = $"Layer '{parameters.layerName}' not found";
                    return result;
                }

                if (layer.stateMachine.states.Any(s => s.state.name == parameters.stateName))
                {
                    result.success = false;
                    result.message = $"State '{parameters.stateName}' already exists in layer '{parameters.layerName}'";
                    return result;
                }

                var state = layer.stateMachine.AddState(parameters.stateName);
                state.speed = parameters.speed;

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

                var layer = Array.Find(controller.layers, l => l.name == parameters.layerName);
                if (layer == null)
                {
                    result.success = false;
                    result.message = $"Layer '{parameters.layerName}' not found";
                    return result;
                }

                var stateEntry = Array.Find(layer.stateMachine.states, s => s.state.name == parameters.stateName);
                if (stateEntry.state == null)
                {
                    result.success = false;
                    result.message = $"State '{parameters.stateName}' not found in layer '{parameters.layerName}'";
                    return result;
                }

                var clip = AssetDatabase.LoadAssetAtPath<AnimationClip>(parameters.animationClipPath);
                if (clip == null)
                {
                    result.success = false;
                    result.message = $"Animation clip not found at path: {parameters.animationClipPath}";
                    return result;
                }

                stateEntry.state.motion = clip;
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

                var layer = Array.Find(controller.layers, l => l.name == parameters.layerName);
                if (layer == null)
                {
                    result.success = false;
                    result.message = $"Layer '{parameters.layerName}' not found";
                    return result;
                }

                var stateEntry = Array.Find(layer.stateMachine.states, s => s.state.name == parameters.stateName);
                if (stateEntry.state == null)
                {
                    result.success = false;
                    result.message = $"State '{parameters.stateName}' not found in layer '{parameters.layerName}'";
                    return result;
                }

                stateEntry.state.speed = parameters.speed;
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

                var layer = Array.Find(controller.layers, l => l.name == parameters.layerName);
                if (layer == null)
                {
                    result.success = false;
                    result.message = $"Layer '{parameters.layerName}' not found";
                    return result;
                }

                var stateEntry = Array.Find(layer.stateMachine.states, s => s.state.name == parameters.stateName);
                if (stateEntry.state == null)
                {
                    result.success = false;
                    result.message = $"State '{parameters.stateName}' not found in layer '{parameters.layerName}'";
                    return result;
                }

                layer.stateMachine.defaultState = stateEntry.state;
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

                var layer = Array.Find(controller.layers, l => l.name == parameters.layerName);
                if (layer == null)
                {
                    result.success = false;
                    result.message = $"Layer '{parameters.layerName}' not found";
                    return result;
                }

                var stateEntry = Array.Find(layer.stateMachine.states, s => s.state.name == parameters.stateName);
                if (stateEntry.state == null)
                {
                    result.success = false;
                    result.message = $"State '{parameters.stateName}' not found in layer '{parameters.layerName}'";
                    return result;
                }

                layer.stateMachine.RemoveState(stateEntry.state);
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
    }
}
