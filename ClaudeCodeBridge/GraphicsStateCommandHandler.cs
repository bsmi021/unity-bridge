using System;
using System.IO;
using Unity.Jobs;
using UnityEditor;
using UnityEngine;
using UnityEngine.Experimental.Rendering;

namespace BWS.Editor.ClaudeCodeBridge
{
    /// <summary>
    /// Command handler for GraphicsStateCollection / PSO trace and warmup operations.
    /// </summary>
    public class GraphicsStateCommandHandler : ICommandHandler
    {
        private static GraphicsStateCollection activeTraceCollection;

        public string CommandType => "graphics-state";

        public BridgeResponse Execute(BridgeCommand command)
        {
            try
            {
                if (EditorApplication.isCompiling)
                {
                    return BridgeResponse.Error(command.commandId, command.commandType,
                        "Cannot execute graphics-state operations while scripts are compiling.");
                }

                var parameters = JsonUtility.FromJson<GraphicsStateParams>(
                    command.parametersJson ?? "{}") ?? new GraphicsStateParams();
                var operation = parameters.operation?.ToLowerInvariant();

                switch (operation)
                {
                    case "create":
                        return HandleCreate(command, parameters);
                    case "load-info":
                        return HandleLoadInfo(command, parameters);
                    case "begin-trace":
                        return HandleBeginTrace(command);
                    case "end-trace-save":
                        return HandleEndTraceSave(command, parameters);
                    case "warmup":
                        return HandleWarmup(command, parameters);
                    case "clear-variants":
                        return HandleClearVariants(command, parameters);
                    default:
                        return BridgeResponse.Error(command.commandId, command.commandType,
                            $"Unknown graphics-state operation: {parameters.operation}. " +
                            "Supported: create, load-info, begin-trace, end-trace-save, warmup, clear-variants");
                }
            }
            catch (Exception ex)
            {
                BridgeLogger.LogError($"GraphicsState operation error: {ex}");
                return BridgeResponse.Error(command.commandId, command.commandType, ex.ToString());
            }
        }

        private BridgeResponse HandleCreate(BridgeCommand command, GraphicsStateParams p)
        {
            string outputPath = ResolveOutputPath(p);
            if (string.IsNullOrEmpty(outputPath))
                return Missing(command, "outputPath or assetPath is required for create operation.");

            var collection = new GraphicsStateCollection();
            string filePath = ToFilePath(outputPath);
            EnsureDirectory(filePath);
            if (!collection.SaveToFile(filePath))
                return BridgeResponse.Error(command.commandId, command.commandType,
                    $"Failed to save graphics state collection: {outputPath}");

            RefreshAssetPath(outputPath);
            var result = BuildResult("create", p.assetPath, outputPath, collection,
                $"Created graphics state collection at {outputPath}");
            return Success(command, result);
        }

        private BridgeResponse HandleLoadInfo(BridgeCommand command, GraphicsStateParams p)
        {
            var loaded = LoadCollection(command, p.assetPath, out var collection, out var error);
            if (!loaded)
                return error;

            var result = BuildResult("load-info", p.assetPath, null, collection,
                $"Loaded graphics state collection from {p.assetPath}");
            return Success(command, result);
        }

        private BridgeResponse HandleBeginTrace(BridgeCommand command)
        {
            if (activeTraceCollection != null)
            {
                return BridgeResponse.Error(command.commandId, command.commandType,
                    "A graphics-state trace is already active. End it before beginning another trace.");
            }

            activeTraceCollection = new GraphicsStateCollection();
            if (!activeTraceCollection.BeginTrace())
            {
                activeTraceCollection = null;
                return BridgeResponse.Error(command.commandId, command.commandType,
                    "Failed to begin graphics-state trace.");
            }

            var result = BuildResult("begin-trace", null, null, activeTraceCollection,
                "Graphics-state tracing started");
            return Success(command, result);
        }

        private BridgeResponse HandleEndTraceSave(BridgeCommand command, GraphicsStateParams p)
        {
            if (activeTraceCollection == null)
                return BridgeResponse.Error(command.commandId, command.commandType,
                    "No active graphics-state trace exists.");
            if (string.IsNullOrEmpty(p.outputPath))
                return Missing(command, "outputPath is required for end-trace-save operation.");

            if (activeTraceCollection.isTracing)
                activeTraceCollection.EndTrace();

            string filePath = ToFilePath(p.outputPath);
            EnsureDirectory(filePath);
            if (!activeTraceCollection.SaveToFile(filePath))
                return BridgeResponse.Error(command.commandId, command.commandType,
                    $"Failed to save graphics-state trace: {p.outputPath}");

            RefreshAssetPath(p.outputPath);
            var result = BuildResult("end-trace-save", p.assetPath, p.outputPath,
                activeTraceCollection, $"Saved graphics-state trace to {p.outputPath}");
            activeTraceCollection = null;
            return Success(command, result);
        }

        private BridgeResponse HandleWarmup(BridgeCommand command, GraphicsStateParams p)
        {
            var loaded = LoadCollection(command, p.assetPath, out var collection, out var error);
            if (!loaded)
                return error;

            JobHandle handle = p.progressiveBatchSize > 0
                ? collection.WarmUpProgressively(p.progressiveBatchSize, default)
                : collection.WarmUp(default);
            handle.Complete();

            string mode = p.progressiveBatchSize > 0 ? "progressive" : "full";
            var result = BuildResult("warmup", p.assetPath, null, collection,
                $"Completed {mode} graphics-state warmup");
            return Success(command, result);
        }

        private BridgeResponse HandleClearVariants(BridgeCommand command, GraphicsStateParams p)
        {
            var loaded = LoadCollection(command, p.assetPath, out var collection, out var error);
            if (!loaded)
                return error;
            if (string.IsNullOrEmpty(p.outputPath))
                return Missing(command, "outputPath is required for clear-variants operation.");

            collection.ClearVariants();
            string filePath = ToFilePath(p.outputPath);
            EnsureDirectory(filePath);
            if (!collection.SaveToFile(filePath))
                return BridgeResponse.Error(command.commandId, command.commandType,
                    $"Failed to save graphics state collection: {p.outputPath}");

            RefreshAssetPath(p.outputPath);
            var result = BuildResult("clear-variants", p.assetPath, p.outputPath, collection,
                $"Cleared variants and saved graphics state collection to {p.outputPath}");
            return Success(command, result);
        }

        private static bool LoadCollection(BridgeCommand command, string assetPath,
            out GraphicsStateCollection collection, out BridgeResponse error)
        {
            collection = null;
            error = null;
            if (string.IsNullOrEmpty(assetPath))
            {
                error = BridgeResponse.Error(command.commandId, command.commandType,
                    "assetPath is required.");
                return false;
            }
            string filePath = ToFilePath(assetPath);
            if (!File.Exists(filePath))
            {
                error = BridgeResponse.Error(command.commandId, command.commandType,
                    $"Graphics state collection file not found: {assetPath}");
                return false;
            }

            collection = new GraphicsStateCollection();
            if (collection.LoadFromFile(filePath))
                return true;

            error = BridgeResponse.Error(command.commandId, command.commandType,
                $"Failed to load graphics state collection: {assetPath}");
            return false;
        }

        private static GraphicsStateResult BuildResult(string operation, string assetPath,
            string outputPath, GraphicsStateCollection collection, string message)
        {
            return new GraphicsStateResult
            {
                success = true,
                operation = operation,
                assetPath = assetPath,
                outputPath = outputPath,
                isTracing = collection.isTracing,
                isWarmedUp = collection.isWarmedUp,
                version = collection.version,
                graphicsDeviceType = collection.graphicsDeviceType.ToString(),
                runtimePlatform = collection.runtimePlatform.ToString(),
                qualityLevelName = collection.qualityLevelName,
                variantCount = collection.variantCount,
                totalGraphicsStateCount = collection.totalGraphicsStateCount,
                completedWarmupCount = collection.completedWarmupCount,
                message = message
            };
        }

        private static string ResolveOutputPath(GraphicsStateParams p)
        {
            return string.IsNullOrEmpty(p.outputPath) ? p.assetPath : p.outputPath;
        }

        private static string ToFilePath(string path)
        {
            if (Path.IsPathRooted(path))
                return path;

            string projectRoot = Directory.GetParent(Application.dataPath)?.FullName;
            return string.IsNullOrEmpty(projectRoot) ? path : Path.Combine(projectRoot, path);
        }

        private static void EnsureDirectory(string path)
        {
            string directory = Path.GetDirectoryName(path);
            if (!string.IsNullOrEmpty(directory) && !Directory.Exists(directory))
                Directory.CreateDirectory(directory);
        }

        private static void RefreshAssetPath(string path)
        {
            string normalized = path.Replace('\\', '/');
            if (normalized.StartsWith("Assets/", StringComparison.Ordinal) ||
                normalized == "Assets")
                AssetDatabase.Refresh();
        }

        private static BridgeResponse Missing(BridgeCommand command, string message)
        {
            return BridgeResponse.Error(command.commandId, command.commandType, message);
        }

        private static BridgeResponse Success(BridgeCommand command, GraphicsStateResult result)
        {
            return BridgeResponse.Success(command.commandId, command.commandType,
                JsonUtility.ToJson(result));
        }
    }

    [Serializable]
    public class GraphicsStateParams
    {
        public string operation;
        public string assetPath;
        public string outputPath;
        public int progressiveBatchSize;
    }

    [Serializable]
    public class GraphicsStateResult
    {
        public bool success;
        public string operation;
        public string assetPath;
        public string outputPath;
        public bool isTracing;
        public bool isWarmedUp;
        public int version;
        public string graphicsDeviceType;
        public string runtimePlatform;
        public string qualityLevelName;
        public int variantCount;
        public int totalGraphicsStateCount;
        public int completedWarmupCount;
        public string message;
    }
}
