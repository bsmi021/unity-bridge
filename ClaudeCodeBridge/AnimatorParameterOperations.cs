using System;
using System.Collections.Generic;
using System.Linq;
using UnityEditor;
using UnityEditor.Animations;
using UnityEngine;

namespace BWS.Editor.ClaudeCodeBridge
{
    /// <summary>
    /// Partial class: parameter operations for AnimatorOperationCommandHandler.
    /// </summary>
    public partial class AnimatorOperationCommandHandler
    {
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

                if (controller.parameters.Any(p => p.name == parameters.parameterName))
                {
                    result.success = false;
                    result.message = $"Parameter '{parameters.parameterName}' already exists";
                    return result;
                }

                var paramType = ParseParameterType(parameters.parameterType);
                controller.AddParameter(parameters.parameterName, paramType);

                if (!string.IsNullOrEmpty(parameters.defaultValue))
                {
                    var param = Array.Find(
                        controller.parameters, p => p.name == parameters.parameterName);
                    if (param != null)
                    {
                        SetParameterDefaultValue(param, paramType, parameters.defaultValue);
                    }
                }

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

                var paramIndex = Array.FindIndex(
                    controller.parameters, p => p.name == parameters.parameterName);
                if (paramIndex < 0)
                {
                    result.success = false;
                    result.message = $"Parameter '{parameters.parameterName}' not found";
                    return result;
                }

                var param = controller.parameters[paramIndex];

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

                var paramIndex = Array.FindIndex(
                    controller.parameters, p => p.name == parameters.parameterName);
                if (paramIndex < 0)
                {
                    result.success = false;
                    result.message = $"Parameter '{parameters.parameterName}' not found";
                    return result;
                }

                controller.RemoveParameter(paramIndex);
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

        /// <summary>
        /// Helper to set default value on a parameter based on its type.
        /// </summary>
        private static void SetParameterDefaultValue(
            AnimatorControllerParameter param,
            AnimatorControllerParameterType paramType,
            string defaultValue)
        {
            switch (paramType)
            {
                case AnimatorControllerParameterType.Float:
                    param.defaultFloat = float.Parse(defaultValue);
                    break;
                case AnimatorControllerParameterType.Int:
                    param.defaultInt = int.Parse(defaultValue);
                    break;
                case AnimatorControllerParameterType.Bool:
                    param.defaultBool = bool.Parse(defaultValue);
                    break;
            }
        }
    }
}
