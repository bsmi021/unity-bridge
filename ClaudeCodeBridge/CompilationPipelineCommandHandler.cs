using System;
using System.Collections.Generic;
using System.Linq;
using UnityEditor;
using UnityEditor.Compilation;
using UnityEngine;

namespace BWS.Editor.ClaudeCodeBridge
{
    /// <summary>
    /// Command handler for querying the Unity compilation pipeline.
    ///
    /// PURPOSE:
    /// Provides Claude Code with introspection into project assembly structure,
    /// scripting defines, script-to-assembly mapping, and code optimization settings.
    ///
    /// SUPPORTED OPERATIONS:
    /// 1. "assemblies" - List all project assemblies with metadata
    /// 2. "defines" - Get scripting defines for a named assembly
    /// 3. "which" - Determine which assembly owns a given script file
    /// 4. "optimization" - Get or set the code optimization level
    ///
    /// GUARDS:
    /// - EditorApplication.isCompiling: blocks all operations
    /// - NOT added to PARALLEL_SAFE_COMMANDS (optimization is a write operation)
    /// </summary>
    public class CompilationPipelineCommandHandler : ICommandHandler
    {
        public string CommandType => "compilation-pipeline";

        public BridgeResponse Execute(BridgeCommand command)
        {
            try
            {
                if (EditorApplication.isCompiling)
                {
                    return BridgeResponse.Error(
                        command.commandId,
                        command.commandType,
                        "Cannot query compilation pipeline while scripts are compiling."
                    );
                }

                var parameters = JsonUtility.FromJson<CompilationPipelineParams>(
                    command.parametersJson ?? "{}"
                );
                if (parameters == null)
                    parameters = new CompilationPipelineParams();

                BridgeLogger.LogDebug($"Executing operation: {parameters.operation}");

                switch (parameters.operation?.ToLower())
                {
                    case "assemblies":
                        return ExecuteAssemblies(command);

                    case "defines":
                        return ExecuteDefines(command, parameters.assemblyName);

                    case "which":
                        return ExecuteWhich(command, parameters.scriptPath);

                    case "optimization":
                        return ExecuteOptimization(command, parameters.mode);

                    default:
                        return BridgeResponse.Error(
                            command.commandId,
                            command.commandType,
                            $"Unknown operation: {parameters.operation}. "
                            + "Supported operations: assemblies, defines, which, optimization"
                        );
                }
            }
            catch (Exception ex)
            {
                BridgeLogger.LogError($"Error: {ex}");
                return BridgeResponse.Error(command.commandId, command.commandType, ex.ToString());
            }
        }

        /// <summary>
        /// List all project assemblies with name, path, source file count,
        /// defines, and references.
        /// </summary>
        private BridgeResponse ExecuteAssemblies(BridgeCommand command)
        {
            var playerAssemblies = CompilationPipeline.GetAssemblies(
                AssembliesType.PlayerWithoutTestAssemblies
            );
            var editorAssemblies = CompilationPipeline.GetAssemblies(AssembliesType.Editor);
            var allAssemblies = playerAssemblies.Concat(editorAssemblies);

            var result = new CompilationPipelineResult
            {
                success = true,
                operation = "assemblies"
            };

            foreach (var asm in allAssemblies)
            {
                var info = new AssemblyInfoResult
                {
                    name = asm.name,
                    path = asm.outputPath,
                    sourceFileCount = asm.sourceFiles.Length,
                };
                info.defines.AddRange(asm.defines);
                info.references.AddRange(
                    asm.assemblyReferences.Select(r => r.name)
                );
                result.assemblies.Add(info);
            }

            var resultJson = JsonUtility.ToJson(result);
            BridgeLogger.LogInfo(
                $"Assemblies query complete: {result.assemblies.Count} assemblies found"
            );
            return BridgeResponse.Success(command.commandId, command.commandType, resultJson);
        }

        /// <summary>
        /// Get scripting defines for a named assembly.
        /// Returns error if assembly name is missing or not found (M7).
        /// </summary>
        private BridgeResponse ExecuteDefines(BridgeCommand command, string assemblyName)
        {
            if (string.IsNullOrEmpty(assemblyName))
            {
                return BridgeResponse.Error(
                    command.commandId,
                    command.commandType,
                    "assemblyName is required for 'defines' operation"
                );
            }

            var defines = CompilationPipeline.GetDefinesFromAssemblyName(assemblyName);

            // M7: GetDefinesFromAssemblyName can return null
            if (defines == null)
            {
                return BridgeResponse.Error(
                    command.commandId,
                    command.commandType,
                    $"Assembly not found: {assemblyName}"
                );
            }

            var result = new CompilationPipelineResult
            {
                success = true,
                operation = "defines",
                assembly = assemblyName
            };
            result.defines.AddRange(defines);

            var resultJson = JsonUtility.ToJson(result);
            BridgeLogger.LogInfo(
                $"Defines query complete: {result.defines.Count} defines for {assemblyName}"
            );
            return BridgeResponse.Success(command.commandId, command.commandType, resultJson);
        }

        /// <summary>
        /// Determine which assembly owns a given script path.
        /// Returns error if script path is missing or no assembly found (M8).
        /// </summary>
        private BridgeResponse ExecuteWhich(BridgeCommand command, string scriptPath)
        {
            if (string.IsNullOrEmpty(scriptPath))
            {
                return BridgeResponse.Error(
                    command.commandId,
                    command.commandType,
                    "scriptPath is required for 'which' operation"
                );
            }

            var assemblyName = CompilationPipeline.GetAssemblyNameFromScriptPath(scriptPath);

            // M8: GetAssemblyNameFromScriptPath can return null
            if (string.IsNullOrEmpty(assemblyName))
            {
                return BridgeResponse.Error(
                    command.commandId,
                    command.commandType,
                    $"No assembly found for script: {scriptPath}"
                );
            }

            // Strip .dll extension if present for clean display
            var cleanName = assemblyName.EndsWith(".dll")
                ? assemblyName.Substring(0, assemblyName.Length - 4)
                : assemblyName;

            var result = new CompilationPipelineResult
            {
                success = true,
                operation = "which",
                scriptPath = scriptPath,
                assembly = cleanName,
                assemblyPath = assemblyName
            };

            var resultJson = JsonUtility.ToJson(result);
            BridgeLogger.LogInfo($"Which query complete: {scriptPath} -> {cleanName}");
            return BridgeResponse.Success(command.commandId, command.commandType, resultJson);
        }

        /// <summary>
        /// Get or set the code optimization level.
        /// When mode is null/empty, returns current mode.
        /// When mode is provided, sets it and returns changed=true.
        /// m3: CodeOptimization enum has 3 values: None, Debug, Release.
        /// </summary>
        private BridgeResponse ExecuteOptimization(BridgeCommand command, string mode)
        {
            // Guard: setting optimization during play mode can cause issues
            if (!string.IsNullOrEmpty(mode) && EditorApplication.isPlaying)
            {
                return BridgeResponse.Error(
                    command.commandId,
                    command.commandType,
                    "Cannot change code optimization mode during play mode."
                );
            }

            var result = new CompilationPipelineResult
            {
                success = true,
                operation = "optimization"
            };

            if (string.IsNullOrEmpty(mode))
            {
                // Get current optimization mode
                var current = CompilationPipeline.codeOptimization;
                result.mode = current.ToString();
                result.changed = false;
            }
            else
            {
                // Set optimization mode
                if (!TryParseOptimization(mode, out var newMode))
                {
                    return BridgeResponse.Error(
                        command.commandId,
                        command.commandType,
                        $"Invalid optimization mode: '{mode}'. "
                        + "Must be one of: None, Debug, Release"
                    );
                }

                var previous = CompilationPipeline.codeOptimization;
                CompilationPipeline.codeOptimization = newMode;
                result.mode = newMode.ToString();
                result.changed = previous != newMode;
            }

            var resultJson = JsonUtility.ToJson(result);
            BridgeLogger.LogInfo($"Optimization: mode={result.mode}, changed={result.changed}");
            return BridgeResponse.Success(command.commandId, command.commandType, resultJson);
        }

        /// <summary>
        /// Parse a string optimization mode to the CodeOptimization enum.
        /// Supports case-insensitive matching.
        /// </summary>
        private static bool TryParseOptimization(string mode, out CodeOptimization result)
        {
            switch (mode?.ToLower())
            {
                case "none":
                    result = CodeOptimization.None;
                    return true;
                case "debug":
                    result = CodeOptimization.Debug;
                    return true;
                case "release":
                    result = CodeOptimization.Release;
                    return true;
                default:
                    result = CodeOptimization.None;
                    return false;
            }
        }
    }
}
