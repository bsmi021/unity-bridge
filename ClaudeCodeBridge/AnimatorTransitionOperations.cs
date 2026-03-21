using System;
using System.Collections.Generic;
using UnityEditor;
using UnityEditor.Animations;
using UnityEngine;

namespace BWS.Editor.ClaudeCodeBridge
{
    /// <summary>
    /// Partial class: transition operations for AnimatorOperationCommandHandler.
    /// </summary>
    public partial class AnimatorOperationCommandHandler
    {
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

                var layer = Array.Find(controller.layers, l => l.name == parameters.layerName);
                if (layer == null)
                {
                    result.success = false;
                    result.message = $"Layer '{parameters.layerName}' not found";
                    return result;
                }

                var destStateEntry = Array.Find(
                    layer.stateMachine.states, s => s.state.name == parameters.destinationState);
                if (destStateEntry.state == null)
                {
                    result.success = false;
                    result.message = $"Destination state '{parameters.destinationState}' not found in layer '{parameters.layerName}'";
                    return result;
                }

                if (parameters.sourceState == "Entry")
                {
                    layer.stateMachine.AddEntryTransition(destStateEntry.state);
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
                        var sourceStateEntry = Array.Find(
                            layer.stateMachine.states, s => s.state.name == parameters.sourceState);
                        if (sourceStateEntry.state == null)
                        {
                            result.success = false;
                            result.message = $"Source state '{parameters.sourceState}' not found in layer '{parameters.layerName}'";
                            return result;
                        }

                        transition = sourceStateEntry.state.AddTransition(destStateEntry.state);
                    }

                    transition.duration = parameters.duration;
                    transition.hasExitTime = parameters.hasExitTime;
                    transition.exitTime = parameters.exitTime;
                }

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

                var layer = Array.Find(controller.layers, l => l.name == parameters.layerName);
                if (layer == null)
                {
                    result.success = false;
                    result.message = $"Layer '{parameters.layerName}' not found";
                    return result;
                }

                var transition = FindTransition(layer, parameters.sourceState, parameters.destinationState);
                if (transition == null)
                {
                    result.success = false;
                    result.message = $"Transition not found from '{parameters.sourceState}' to '{parameters.destinationState}'";
                    return result;
                }

                transition.duration = parameters.duration;
                EditorUtility.SetDirty(controller);
                AssetDatabase.SaveAssets();

                result.success = true;
                result.message = $"Transition duration set to {parameters.duration}";

                BridgeLogger.LogDebug(
                    $"Set transition duration: {parameters.sourceState} -> {parameters.destinationState} = {parameters.duration}");
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
        /// Sets conditions on a transition. Replaces any existing conditions.
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

                var layer = Array.Find(controller.layers, l => l.name == parameters.layerName);
                if (layer == null)
                {
                    result.success = false;
                    result.message = $"Layer '{parameters.layerName}' not found";
                    return result;
                }

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

                EditorUtility.SetDirty(controller);
                AssetDatabase.SaveAssets();

                result.success = true;
                result.message = $"Set {parameters.conditions.Count} conditions on transition";

                BridgeLogger.LogDebug(
                    $"Set transition conditions: {parameters.sourceState} -> {parameters.destinationState}");
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

                var layer = Array.Find(controller.layers, l => l.name == parameters.layerName);
                if (layer == null)
                {
                    result.success = false;
                    result.message = $"Layer '{parameters.layerName}' not found";
                    return result;
                }

                if (parameters.sourceState == "Any State")
                {
                    var destEntry = Array.Find(
                        layer.stateMachine.states, s => s.state.name == parameters.destinationState);
                    if (destEntry.state == null)
                    {
                        result.success = false;
                        result.message = $"Destination state '{parameters.destinationState}' not found";
                        return result;
                    }

                    var anyTransitions = layer.stateMachine.anyStateTransitions;
                    var idx = Array.FindIndex(anyTransitions, t => t.destinationState == destEntry.state);
                    if (idx < 0)
                    {
                        result.success = false;
                        result.message = $"Any State transition to '{parameters.destinationState}' not found";
                        return result;
                    }

                    layer.stateMachine.RemoveAnyStateTransition(anyTransitions[idx]);
                }
                else
                {
                    var srcEntry = Array.Find(
                        layer.stateMachine.states, s => s.state.name == parameters.sourceState);
                    if (srcEntry.state == null)
                    {
                        result.success = false;
                        result.message = $"Source state '{parameters.sourceState}' not found";
                        return result;
                    }

                    var destEntry = Array.Find(
                        layer.stateMachine.states, s => s.state.name == parameters.destinationState);
                    if (destEntry.state == null)
                    {
                        result.success = false;
                        result.message = $"Destination state '{parameters.destinationState}' not found";
                        return result;
                    }

                    var transitions = srcEntry.state.transitions;
                    var idx = Array.FindIndex(transitions, t => t.destinationState == destEntry.state);
                    if (idx < 0)
                    {
                        result.success = false;
                        result.message = $"Transition not found from '{parameters.sourceState}' to '{parameters.destinationState}'";
                        return result;
                    }

                    srcEntry.state.RemoveTransition(transitions[idx]);
                }

                EditorUtility.SetDirty(controller);
                AssetDatabase.SaveAssets();

                result.success = true;
                result.message = $"Transition deleted from '{parameters.sourceState}' to '{parameters.destinationState}'";

                BridgeLogger.LogDebug(
                    $"Deleted transition: {parameters.sourceState} -> {parameters.destinationState}");
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

                var layer = Array.Find(controller.layers, l => l.name == parameters.layerName);
                if (layer == null)
                {
                    result.success = false;
                    result.message = $"Layer '{parameters.layerName}' not found";
                    return result;
                }

                if (parameters.sourceState == "Any State")
                {
                    foreach (var transition in layer.stateMachine.anyStateTransitions)
                    {
                        result.transitions.Add(CreateTransitionInfo("Any State", transition));
                    }
                }
                else
                {
                    var sourceEntry = Array.Find(
                        layer.stateMachine.states, s => s.state.name == parameters.sourceState);
                    if (sourceEntry.state == null)
                    {
                        result.success = false;
                        result.message = $"Source state '{parameters.sourceState}' not found";
                        return result;
                    }

                    foreach (var transition in sourceEntry.state.transitions)
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
    }
}
