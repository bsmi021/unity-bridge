using System;
using System.Collections.Generic;
using System.Linq;
using UnityEditor;
using UnityEditor.Rendering;
using UnityEngine;
using UnityEngine.Rendering;

namespace BWS.Editor.ClaudeCodeBridge
{
    /// <summary>
    /// Command handler for read-only shader inspection operations.
    ///
    /// PURPOSE:
    /// Provides Claude Code with the ability to enumerate shaders, inspect their
    /// properties, check compilation errors, and search by property name. All
    /// operations are read-only and safe for parallel execution.
    ///
    /// SUPPORTED OPERATIONS:
    /// 1. "list" - List all available shaders (optionally errors-only)
    /// 2. "info" - Get detailed info about a specific shader
    /// 3. "errors" - Get compilation errors/warnings for a shader
    /// 4. "properties" - Enumerate all shader properties
    /// 5. "find-by-property" - Find shaders declaring a specific property
    /// 6. "keywords" - List shader keywords (global and/or local)
    ///
    /// GUARDS:
    /// - EditorApplication.isCompiling: blocks all operations
    /// - All operations are read-only (no play mode guard needed)
    /// </summary>
    public class ShaderInspectionCommandHandler : ICommandHandler
    {
        public string CommandType => "shader-inspection";

        public BridgeResponse Execute(BridgeCommand command)
        {
            try
            {
                if (EditorApplication.isCompiling)
                {
                    return BridgeResponse.Error(
                        command.commandId,
                        command.commandType,
                        "Cannot inspect shaders while scripts are compiling."
                    );
                }

                var parameters = JsonUtility.FromJson<ShaderInspectionParams>(
                    command.parametersJson ?? "{}"
                );
                if (parameters == null)
                    parameters = new ShaderInspectionParams();

                BridgeLogger.LogDebug($"Executing shader operation: {parameters.operation}");

                switch (parameters.operation?.ToLower())
                {
                    case "list":
                        return ExecuteList(command, parameters.errorsOnly);

                    case "info":
                        return ExecuteInfo(command, parameters.shaderName);

                    case "errors":
                        return ExecuteErrors(command, parameters.shaderName);

                    case "properties":
                        return ExecuteProperties(command, parameters.shaderName);

                    case "find-by-property":
                        return ExecuteFindByProperty(command, parameters.propertyName);

                    case "keywords":
                        return ExecuteKeywords(command, parameters.shaderName, parameters.keywordFilter);

                    default:
                        return BridgeResponse.Error(
                            command.commandId,
                            command.commandType,
                            $"Unknown operation: {parameters.operation}. "
                            + "Supported: list, info, errors, properties, find-by-property, keywords"
                        );
                }
            }
            catch (Exception ex)
            {
                BridgeLogger.LogError($"Shader inspection error: {ex}");
                return BridgeResponse.Error(command.commandId, command.commandType, ex.ToString());
            }
        }

        /// <summary>
        /// List all available shaders with name, supported, and hasErrors fields.
        /// Optionally filter to only those with compilation errors.
        /// </summary>
        private BridgeResponse ExecuteList(BridgeCommand command, bool errorsOnly)
        {
            var result = new ShaderListResult { operation = "list" };

            var allShaderInfos = ShaderUtil.GetAllShaderInfo();
            int totalShaderCount = allShaderInfos.Length;

            foreach (var info in allShaderInfos)
            {
                var shader = Shader.Find(info.name);
                bool hasErrors = shader is not null && ShaderUtil.ShaderHasError(shader);
                bool supported = shader is not null && shader.isSupported;

                if (errorsOnly && !hasErrors)
                    continue;

                result.shaders.Add(new ShaderListEntry
                {
                    name = info.name,
                    supported = supported,
                    hasErrors = hasErrors
                });
            }

            result.totalCount = totalShaderCount;
            result.success = true;
            result.message = errorsOnly
                ? $"Found {result.shaders.Count} shaders with errors (of {totalShaderCount} total)"
                : $"Found {totalShaderCount} shaders";

            var resultJson = JsonUtility.ToJson(result);
            BridgeLogger.LogInfo($"Shader list: {result.totalCount} shaders");
            return BridgeResponse.Success(command.commandId, command.commandType, resultJson);
        }

        /// <summary>
        /// Get detailed information about a specific shader.
        /// </summary>
        private BridgeResponse ExecuteInfo(BridgeCommand command, string shaderName)
        {
            if (string.IsNullOrEmpty(shaderName))
            {
                return BridgeResponse.Error(
                    command.commandId, command.commandType,
                    "shaderName is required for 'info' operation"
                );
            }

            var shader = Shader.Find(shaderName);
            if (shader is null)
            {
                return BridgeResponse.Error(
                    command.commandId, command.commandType,
                    $"Shader not found: {shaderName}"
                );
            }

            var result = new ShaderInfoResult
            {
                operation = "info",
                shaderName = shaderName,
                supported = shader.isSupported,
                hasErrors = ShaderUtil.ShaderHasError(shader),
                isCompiling = EditorApplication.isCompiling,
                renderQueue = shader.renderQueue,
                passCount = shader.passCount,
                propertyCount = shader.GetPropertyCount(),
                subShaderCount = shader.subshaderCount,
                success = true,
                message = "Shader info retrieved"
            };

            var resultJson = JsonUtility.ToJson(result);
            BridgeLogger.LogInfo($"Shader info: {shaderName}");
            return BridgeResponse.Success(command.commandId, command.commandType, resultJson);
        }

        /// <summary>
        /// Get shader compilation errors and warnings.
        /// M13: ShaderHasError (errors only) vs GetShaderMessages (errors+warnings).
        /// </summary>
        private BridgeResponse ExecuteErrors(BridgeCommand command, string shaderName)
        {
            if (string.IsNullOrEmpty(shaderName))
            {
                return BridgeResponse.Error(
                    command.commandId, command.commandType,
                    "shaderName is required for 'errors' operation"
                );
            }

            var shader = Shader.Find(shaderName);
            if (shader is null)
            {
                return BridgeResponse.Error(
                    command.commandId, command.commandType,
                    $"Shader not found: {shaderName}"
                );
            }

            var result = new ShaderErrorsResult
            {
                operation = "errors",
                shaderName = shaderName,
                hasErrors = ShaderUtil.ShaderHasError(shader)
            };

            var shaderMessages = ShaderUtil.GetShaderMessages(shader);
            foreach (var msg in shaderMessages)
            {
                result.messages.Add(new ShaderMessageEntry
                {
                    message = msg.message,
                    messageDetails = msg.messageDetails,
                    severity = msg.severity == ShaderCompilerMessageSeverity.Error ? "error" : "warning",
                    platform = msg.platform.ToString(),
                    line = msg.line,
                    file = msg.file
                });
            }

            result.messageCount = result.messages.Count;
            result.success = true;
            result.message = $"Found {result.messageCount} shader message(s)";

            var resultJson = JsonUtility.ToJson(result);
            BridgeLogger.LogInfo($"Shader errors: {shaderName} — {result.messageCount} messages");
            return BridgeResponse.Success(command.commandId, command.commandType, resultJson);
        }

        /// <summary>
        /// Enumerate all properties of a shader.
        /// M12: ShaderPropertyType.TexEnv is serialized as "Texture".
        /// </summary>
        private BridgeResponse ExecuteProperties(BridgeCommand command, string shaderName)
        {
            if (string.IsNullOrEmpty(shaderName))
            {
                return BridgeResponse.Error(
                    command.commandId, command.commandType,
                    "shaderName is required for 'properties' operation"
                );
            }

            var shader = Shader.Find(shaderName);
            if (shader is null)
            {
                return BridgeResponse.Error(
                    command.commandId, command.commandType,
                    $"Shader not found: {shaderName}"
                );
            }

            var result = new ShaderPropertiesResult
            {
                operation = "properties",
                shaderName = shaderName
            };

            int count = shader.GetPropertyCount();
            for (int i = 0; i < count; i++)
            {
                var entry = BuildPropertyEntry(shader, i);
                result.properties.Add(entry);
            }

            result.propertyCount = result.properties.Count;
            result.success = true;
            result.message = $"Found {result.propertyCount} properties";

            var resultJson = JsonUtility.ToJson(result);
            BridgeLogger.LogInfo($"Shader properties: {shaderName} — {result.propertyCount}");
            return BridgeResponse.Success(command.commandId, command.commandType, resultJson);
        }

        /// <summary>
        /// Find all shaders that declare a specific property name.
        /// Iterates all shaders and their properties — may be slow for large projects.
        /// </summary>
        private BridgeResponse ExecuteFindByProperty(BridgeCommand command, string propertyName)
        {
            if (string.IsNullOrEmpty(propertyName))
            {
                return BridgeResponse.Error(
                    command.commandId, command.commandType,
                    "propertyName is required for 'find-by-property' operation"
                );
            }

            var result = new ShaderFindByPropertyResult
            {
                operation = "find-by-property",
                propertyName = propertyName
            };

            var allShaderInfos = ShaderUtil.GetAllShaderInfo();
            foreach (var info in allShaderInfos)
            {
                var shader = Shader.Find(info.name);
                if (shader is null) continue;

                int propCount = shader.GetPropertyCount();
                for (int i = 0; i < propCount; i++)
                {
                    if (shader.GetPropertyName(i) == propertyName)
                    {
                        result.shaders.Add(new ShaderPropertyMatch
                        {
                            name = info.name,
                            propertyType = MapPropertyType(shader.GetPropertyType(i)),
                            propertyDescription = shader.GetPropertyDescription(i)
                        });
                        break;
                    }
                }
            }

            result.matchCount = result.shaders.Count;
            result.success = true;
            result.message = $"Found {result.matchCount} shaders with property '{propertyName}'";

            var resultJson = JsonUtility.ToJson(result);
            BridgeLogger.LogInfo($"Find by property: '{propertyName}' — {result.matchCount} matches");
            return BridgeResponse.Success(command.commandId, command.commandType, resultJson);
        }

        /// <summary>
        /// List shader keywords (global and/or local).
        /// </summary>
        private BridgeResponse ExecuteKeywords(
            BridgeCommand command, string shaderName, string keywordFilter)
        {
            if (string.IsNullOrEmpty(shaderName))
            {
                return BridgeResponse.Error(
                    command.commandId, command.commandType,
                    "shaderName is required for 'keywords' operation"
                );
            }

            var shader = Shader.Find(shaderName);
            if (shader is null)
            {
                return BridgeResponse.Error(
                    command.commandId, command.commandType,
                    $"Shader not found: {shaderName}"
                );
            }

            var result = new ShaderKeywordsResult
            {
                operation = "keywords",
                shaderName = shaderName
            };

            var filterLower = keywordFilter?.ToLower();
            bool includeGlobal = filterLower != "local";
            bool includeLocal = filterLower != "global";

            // shader.keywordSpace.keywords returns LocalKeyword[] in Unity 6
            foreach (var kw in shader.keywordSpace.keywords)
            {
                // LocalKeyword doesn't have a .type filter — include all
                if (includeLocal)
                    result.localKeywords.Add(kw.name);
            }

            // Global keywords via GlobalKeyword API
            if (includeGlobal)
            {
                // Global keywords are accessible via Shader.globalKeywords
                foreach (var gkw in Shader.globalKeywords)
                {
                    result.globalKeywords.Add(gkw.name);
                }
            }

            result.globalCount = result.globalKeywords.Count;
            result.localCount = result.localKeywords.Count;
            int total = result.globalCount + result.localCount;
            result.success = true;
            result.message = $"Found {total} keywords ({result.globalCount} global, {result.localCount} local)";

            var resultJson = JsonUtility.ToJson(result);
            BridgeLogger.LogInfo($"Shader keywords: {shaderName} — {total} keywords");
            return BridgeResponse.Success(command.commandId, command.commandType, resultJson);
        }

        // -----------------------------------------------------------------------
        // Helpers
        // -----------------------------------------------------------------------

        /// <summary>
        /// Build a ShaderPropertyEntry from a shader property at the given index.
        /// M12: TexEnv is serialized as "Texture".
        /// </summary>
        private static ShaderPropertyEntry BuildPropertyEntry(Shader shader, int index)
        {
            var propType = shader.GetPropertyType(index);
            var entry = new ShaderPropertyEntry
            {
                name = shader.GetPropertyName(index),
                displayName = shader.GetPropertyDescription(index),
                type = MapPropertyType(propType),
                // Unity has no separate description API; display name is the best available
                description = shader.GetPropertyDescription(index),
            };

            // Flags
            var propFlags = shader.GetPropertyFlags(index);
            foreach (ShaderPropertyFlags flag in Enum.GetValues(typeof(ShaderPropertyFlags)))
            {
                if (flag == ShaderPropertyFlags.None) continue;
                if ((propFlags & flag) != 0)
                    entry.flags.Add(flag.ToString());
            }

            // Type-dependent fields
            switch (propType)
            {
                case ShaderPropertyType.Range:
                    var range = shader.GetPropertyRangeLimits(index);
                    entry.rangeMin = range.x;
                    entry.rangeMax = range.y;
                    entry.defaultValue = shader.GetPropertyDefaultFloatValue(index).ToString("G");
                    break;

                case ShaderPropertyType.Float:
                    entry.defaultValue = shader.GetPropertyDefaultFloatValue(index).ToString("G");
                    break;

                case ShaderPropertyType.Int:
                    entry.defaultValue = shader.GetPropertyDefaultIntValue(index).ToString();
                    break;

                case ShaderPropertyType.Color:
                    var c = shader.GetPropertyDefaultVectorValue(index);
                    entry.defaultValue = $"{{\"r\":{c.x},\"g\":{c.y},\"b\":{c.z},\"a\":{c.w}}}";
                    break;

                case ShaderPropertyType.Vector:
                    var v = shader.GetPropertyDefaultVectorValue(index);
                    entry.defaultValue = $"{{\"x\":{v.x},\"y\":{v.y},\"z\":{v.z},\"w\":{v.w}}}";
                    break;

                case ShaderPropertyType.Texture:
                    entry.textureDimension = shader.GetPropertyTextureDimension(index).ToString();
                    entry.defaultValue = shader.GetPropertyTextureDefaultName(index);
                    break;
            }

            return entry;
        }

        /// <summary>
        /// Map ShaderPropertyType to the bridge protocol string.
        /// M12: TexEnv -> "Texture" for clarity.
        /// </summary>
        private static string MapPropertyType(ShaderPropertyType propType)
        {
            return propType switch
            {
                ShaderPropertyType.Texture => "Texture",
                _ => propType.ToString()
            };
        }

    }
}
