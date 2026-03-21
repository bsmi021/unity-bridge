using System;
using System.Collections.Generic;
using System.Linq;
using UnityEditor;
using UnityEditor.Animations;
using UnityEngine;

namespace BWS.Editor.ClaudeCodeBridge
{
    /// <summary>
    /// Partial class: layer operations for AnimatorOperationCommandHandler.
    /// </summary>
    public partial class AnimatorOperationCommandHandler
    {
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

                if (controller.layers.Any(l => l.name == parameters.layerName))
                {
                    result.success = false;
                    result.message = $"Layer '{parameters.layerName}' already exists";
                    return result;
                }

                var layer = new AnimatorControllerLayer
                {
                    name = parameters.layerName,
                    defaultWeight = parameters.weight,
                    blendingMode = parameters.blendingMode.ToLower() == "additive"
                        ? AnimatorLayerBlendingMode.Additive
                        : AnimatorLayerBlendingMode.Override,
                    stateMachine = new AnimatorStateMachine()
                };

                controller.AddLayer(layer);
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

                var layerIndex = Array.FindIndex(controller.layers, l => l.name == parameters.layerName);
                if (layerIndex < 0)
                {
                    result.success = false;
                    result.message = $"Layer '{parameters.layerName}' not found";
                    return result;
                }

                var layers = controller.layers;
                layers[layerIndex].defaultWeight = Mathf.Clamp01(parameters.weight);
                controller.layers = layers;

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

                var layerIndex = Array.FindIndex(controller.layers, l => l.name == parameters.layerName);
                if (layerIndex < 0)
                {
                    result.success = false;
                    result.message = $"Layer '{parameters.layerName}' not found";
                    return result;
                }

                var layers = controller.layers;
                layers[layerIndex].blendingMode = parameters.blendingMode.ToLower() == "additive"
                    ? AnimatorLayerBlendingMode.Additive
                    : AnimatorLayerBlendingMode.Override;
                controller.layers = layers;

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

                var layerIndex = Array.FindIndex(controller.layers, l => l.name == parameters.layerName);
                if (layerIndex < 0)
                {
                    result.success = false;
                    result.message = $"Layer '{parameters.layerName}' not found";
                    return result;
                }

                if (layerIndex == 0)
                {
                    result.success = false;
                    result.message = "Cannot delete Base Layer (index 0)";
                    return result;
                }

                controller.RemoveLayer(layerIndex);
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
    }
}
