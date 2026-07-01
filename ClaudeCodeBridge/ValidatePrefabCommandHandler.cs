using System;
using System.Collections.Generic;
using UnityEditor;
using UnityEngine;

namespace BWS.Editor.ClaudeCodeBridge
{
    /// <summary>
    /// Command handler for validating prefab configurations.
    ///
    /// PURPOSE:
    /// Validates Unity prefabs for missing references, missing components, and
    /// configuration issues. Critical for maintaining asset integrity and catching
    /// errors before runtime.
    ///
    /// USE CASES:
    /// - Automated prefab validation in CI/CD pipelines
    /// - Pre-build validation checks
    /// - Asset integrity verification after refactoring
    /// - Finding broken prefab references
    /// - Quality assurance for content pipeline
    ///
    /// COMMAND JSON:
    /// {
    ///   "commandId": "guid",
    ///   "commandType": "validate-prefab",
    ///   "timestamp": "2025-10-05T18:00:00Z",
    ///   "parametersJson": "{\"prefabPath\":\"Assets/Prefabs/Player.prefab\",\"checkMissingReferences\":true,\"checkMissingComponents\":true}"
    /// }
    ///
    /// USAGE EXAMPLES:
    ///
    /// 1. Validate single prefab:
    ///    send-command.ps1 -CommandType "validate-prefab" -Parameters @{prefabPath="Assets/Prefabs/Player.prefab"}
    ///
    /// 2. Quick check (references only):
    ///    send-command.ps1 -CommandType "validate-prefab" -Parameters @{prefabPath="Assets/Prefabs/Enemy.prefab"; checkMissingComponents=$false}
    ///
    /// 3. Full validation:
    ///    send-command.ps1 -CommandType "validate-prefab" -Parameters @{prefabPath="Assets/Prefabs/Weapon.prefab"; checkMissingReferences=$true; checkMissingComponents=$true}
    /// </summary>
    public class ValidatePrefabCommandHandler : ICommandHandler
    {
        public string CommandType => "validate-prefab";

        public BridgeResponse Execute(BridgeCommand command)
        {
            try
            {
                var parameters = JsonUtility.FromJson<ValidatePrefabParams>(command.parametersJson ?? "{}");
                if (parameters == null || string.IsNullOrEmpty(parameters.prefabPath))
                {
                    return BridgeResponse.Error(command.commandId, command.commandType, "Missing required parameter: prefabPath");
                }

                BridgeLogger.LogDebug($"Validating prefab: {parameters.prefabPath}");

                // Load prefab
                var prefab = AssetDatabase.LoadAssetAtPath<GameObject>(parameters.prefabPath);
                if (prefab == null)
                {
                    return BridgeResponse.Error(command.commandId, command.commandType, $"Prefab not found: {parameters.prefabPath}");
                }

                var result = new ValidatePrefabResult
                {
                    prefabPath = parameters.prefabPath,
                    isValid = true
                };

                // Validate prefab hierarchy
                ValidateGameObject(prefab, "", parameters, result);

                result.isValid = result.issues.Count == 0;

                var resultJson = JsonUtility.ToJson(result);
                BridgeLogger.LogInfo($"Validation complete: {result.issues.Count} issues found");

                return BridgeResponse.Success(command.commandId, command.commandType, resultJson);
            }
            catch (Exception ex)
            {
                BridgeLogger.LogError($"Error: {ex}");
                return BridgeResponse.Error(command.commandId, command.commandType, ex.ToString());
            }
        }

        /// <summary>
        /// Recursively validate GameObject and its children.
        /// </summary>
        private void ValidateGameObject(GameObject go, string path, ValidatePrefabParams parameters, ValidatePrefabResult result)
        {
            var currentPath = string.IsNullOrEmpty(path) ? go.name : $"{path}/{go.name}";

            // Get all components
            var components = go.GetComponents<Component>();

            foreach (var component in components)
            {
                // Check for missing component
                if (component == null)
                {
                    if (parameters.checkMissingComponents)
                    {
                        result.issues.Add(new ValidationIssue
                        {
                            severity = "error",
                            message = "Missing component (script may have been deleted)",
                            objectPath = currentPath
                        });
                    }
                    continue;
                }

                // Check for missing references
                if (parameters.checkMissingReferences)
                {
                    var serializedObject = new SerializedObject(component);
                    var property = serializedObject.GetIterator();

                    while (property.NextVisible(true))
                    {
                        if (property.propertyType == SerializedPropertyType.ObjectReference)
                        {
#if UNITY_6000_5_OR_NEWER
                            var hasDanglingReference = property.objectReferenceValue == null
                                && property.objectReferenceEntityIdValue.IsValid();
#else
                            var hasDanglingReference = property.objectReferenceValue == null
                                && property.objectReferenceInstanceIDValue != 0;
#endif
                            if (hasDanglingReference)
                            {
                                result.issues.Add(new ValidationIssue
                                {
                                    severity = "error",
                                    message = $"Missing reference in component {component.GetType().Name}: {property.propertyPath}",
                                    objectPath = currentPath
                                });
                            }
                        }
                    }
                }
            }

            // Validate children
            for (int i = 0; i < go.transform.childCount; i++)
            {
                var child = go.transform.GetChild(i).gameObject;
                ValidateGameObject(child, currentPath, parameters, result);
            }
        }
    }
}
