using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using UnityEditor;
using UnityEditor.PackageManager;
using UnityEditor.PackageManager.Requests;
using UnityEngine;

namespace BWS.Editor.ClaudeCodeBridge
{
    /// <summary>
    /// Command handler for Unity Package Manager operations.
    ///
    /// Uses async polling pattern: PackageManager.Client methods return Request objects
    /// that must be polled via EditorApplication.update until completed.
    ///
    /// SUPPORTED OPERATIONS:
    /// 1. "list"         - List installed packages
    /// 2. "search"       - Search for a package by ID/name
    /// 3. "search-all"   - List all available registry packages
    /// 4. "add"          - Add a package by identifier (name@version or git URL)
    /// 5. "remove"       - Remove a package by name
    /// 6. "info"         - Get detailed info for a package
    /// 7. "embed"        - Embed a package into the Packages/ folder
    /// 8. "resolve"      - Trigger package resolution (returns void, immediate success)
    /// </summary>
    public class PackageManagerCommandHandler : ICommandHandler
    {
        public string CommandType => "package-operation";

        private static readonly HashSet<string> MUTATING_OPERATIONS = new HashSet<string>(
            StringComparer.OrdinalIgnoreCase)
        {
            "add", "remove", "embed", "resolve"
        };

        private static readonly Dictionary<string, PendingPackageRequest> _pending =
            new Dictionary<string, PendingPackageRequest>();

        private static bool _pollRegistered;

        public BridgeResponse Execute(BridgeCommand command)
        {
            try
            {
                if (EditorApplication.isCompiling)
                {
                    return BridgeResponse.Error(command.commandId, CommandType,
                        "Unity is compiling. Wait for compilation to finish before sending commands.");
                }

                var parameters = JsonUtility.FromJson<PackageOperationParams>(
                    command.parametersJson ?? "{}");
                if (parameters == null)
                    parameters = new PackageOperationParams();

                if (EditorApplication.isPlaying &&
                    MUTATING_OPERATIONS.Contains(parameters.operation ?? ""))
                {
                    return BridgeResponse.Error(command.commandId, CommandType,
                        "Cannot perform mutating operations during play mode. Exit play mode first.");
                }

                BridgeLogger.LogDebug($"Package operation: {parameters.operation}");

                switch (parameters.operation?.ToLower())
                {
                    case "list":
                        return StartListRequest(command, parameters);
                    case "search":
                        return StartSearchRequest(command, parameters);
                    case "search-all":
                        return StartSearchAllRequest(command);
                    case "add":
                        return StartAddRequest(command, parameters);
                    case "remove":
                        return StartRemoveRequest(command, parameters);
                    case "info":
                        return StartInfoRequest(command, parameters);
                    case "embed":
                        return StartEmbedRequest(command, parameters);
                    case "resolve":
                        return ExecuteResolve(command);
                    default:
                        return BridgeResponse.Error(command.commandId, CommandType,
                            $"Unknown operation: {parameters.operation}. " +
                            "Supported: list, search, search-all, add, remove, info, embed, resolve");
                }
            }
            catch (Exception ex)
            {
                BridgeLogger.LogError($"Package operation error: {ex}");
                return BridgeResponse.Error(command.commandId, command.commandType, ex.ToString());
            }
        }

        private BridgeResponse StartListRequest(BridgeCommand command, PackageOperationParams parameters)
        {
            var request = Client.List(parameters.offlineMode, parameters.includeIndirectDependencies);
            RegisterPending(command, request, "list");
            return BridgeResponse.Running(command.commandId, CommandType,
                "{\"operation\":\"list\",\"success\":true,\"message\":\"Listing packages...\"}");
        }

        private BridgeResponse StartSearchRequest(BridgeCommand command, PackageOperationParams parameters)
        {
            if (string.IsNullOrEmpty(parameters.query))
            {
                return BridgeResponse.Error(command.commandId, CommandType,
                    "query is required for search operation");
            }

            var request = Client.Search(parameters.query);
            RegisterPending(command, request, "search", parameters.query);
            return BridgeResponse.Running(command.commandId, CommandType,
                $"{{\"operation\":\"search\",\"success\":true,\"message\":\"Searching for '{parameters.query}'...\"}}");
        }

        private BridgeResponse StartSearchAllRequest(BridgeCommand command)
        {
            var request = Client.SearchAll();
            RegisterPending(command, request, "search-all");
            return BridgeResponse.Running(command.commandId, CommandType,
                "{\"operation\":\"search-all\",\"success\":true,\"message\":\"Listing all available packages...\"}");
        }

        private BridgeResponse StartAddRequest(BridgeCommand command, PackageOperationParams parameters)
        {
            if (string.IsNullOrEmpty(parameters.identifier))
            {
                return BridgeResponse.Error(command.commandId, CommandType,
                    "identifier is required for add operation");
            }

            var request = Client.Add(parameters.identifier);
            RegisterPending(command, request, "add");
            return BridgeResponse.Running(command.commandId, CommandType,
                $"{{\"operation\":\"add\",\"success\":true,\"message\":\"Adding {parameters.identifier}...\"}}");
        }

        private BridgeResponse StartRemoveRequest(BridgeCommand command, PackageOperationParams parameters)
        {
            if (string.IsNullOrEmpty(parameters.packageName))
            {
                return BridgeResponse.Error(command.commandId, CommandType,
                    "packageName is required for remove operation");
            }

            var request = Client.Remove(parameters.packageName);
            RegisterPending(command, request, "remove", parameters.packageName);
            return BridgeResponse.Running(command.commandId, CommandType,
                $"{{\"operation\":\"remove\",\"success\":true,\"message\":\"Removing {parameters.packageName}...\"}}");
        }

        private BridgeResponse StartInfoRequest(BridgeCommand command, PackageOperationParams parameters)
        {
            if (string.IsNullOrEmpty(parameters.packageName))
            {
                return BridgeResponse.Error(command.commandId, CommandType,
                    "packageName is required for info operation");
            }

            var request = Client.Search(parameters.packageName);
            RegisterPending(command, request, "info", parameters.packageName);
            return BridgeResponse.Running(command.commandId, CommandType,
                $"{{\"operation\":\"info\",\"success\":true,\"message\":\"Retrieving info for {parameters.packageName}...\"}}");
        }

        private BridgeResponse StartEmbedRequest(BridgeCommand command, PackageOperationParams parameters)
        {
            if (string.IsNullOrEmpty(parameters.packageName))
            {
                return BridgeResponse.Error(command.commandId, CommandType,
                    "packageName is required for embed operation");
            }

            var request = Client.Embed(parameters.packageName);
            RegisterPending(command, request, "embed");
            return BridgeResponse.Running(command.commandId, CommandType,
                $"{{\"operation\":\"embed\",\"success\":true,\"message\":\"Embedding {parameters.packageName}...\"}}");
        }

        private BridgeResponse ExecuteResolve(BridgeCommand command)
        {
            // M1: Client.Resolve() returns void — immediate success
            Client.Resolve();

            var result = new PackageOperationResult
            {
                operation = "resolve",
                success = true,
                message = "Package resolution requested. Client.Resolve() returns void; " +
                    "resolution proceeds asynchronously."
            };

            return BridgeResponse.Success(command.commandId, CommandType, JsonUtility.ToJson(result));
        }

        // --- Async polling infrastructure ---

        private void RegisterPending(BridgeCommand command, Request request, string operation,
            string context = null)
        {
            _pending[command.commandId] = new PendingPackageRequest
            {
                CommandId = command.commandId,
                CommandType = command.commandType,
                Request = request,
                Operation = operation,
                Context = context,
                StartTime = DateTime.UtcNow
            };

            if (!_pollRegistered)
            {
                EditorApplication.update += PollPendingRequests;
                _pollRegistered = true;
            }
        }

        private static void PollPendingRequests()
        {
            if (_pending.Count == 0)
            {
                EditorApplication.update -= PollPendingRequests;
                _pollRegistered = false;
                return;
            }

            var completed = new List<string>();

            foreach (var kvp in _pending)
            {
                var pending = kvp.Value;

                if (pending.Request.IsCompleted)
                {
                    WriteFinalResponse(pending);
                    completed.Add(kvp.Key);
                }
                else if ((DateTime.UtcNow - pending.StartTime).TotalSeconds > 60)
                {
                    WriteTimeoutResponse(pending);
                    completed.Add(kvp.Key);
                }
            }

            foreach (var id in completed)
                _pending.Remove(id);

            if (_pending.Count == 0)
            {
                EditorApplication.update -= PollPendingRequests;
                _pollRegistered = false;
            }
        }

        private static void WriteFinalResponse(PendingPackageRequest pending)
        {
            try
            {
                var result = BuildResultFromRequest(pending);
                var resultJson = JsonUtility.ToJson(result);
                var response = BridgeResponse.Success(pending.CommandId, pending.CommandType, resultJson);

                BridgeLogger.LogInfo($"Package {pending.Operation} completed, success={result.success}");
                ClaudeUnityBridge.WriteResponseStatic(response);
            }
            catch (Exception ex)
            {
                BridgeLogger.LogError($"Package poll error: {ex}");
                var response = BridgeResponse.Error(pending.CommandId, pending.CommandType, ex.ToString());
                ClaudeUnityBridge.WriteResponseStatic(response);
            }
        }

        private static void WriteTimeoutResponse(PendingPackageRequest pending)
        {
            var result = new PackageOperationResult
            {
                operation = pending.Operation,
                success = false,
                message = $"Package operation '{pending.Operation}' timed out after 60 seconds."
            };
            var response = BridgeResponse.Error(pending.CommandId, pending.CommandType,
                JsonUtility.ToJson(result));
            ClaudeUnityBridge.WriteResponseStatic(response);
        }

        private static PackageOperationResult BuildResultFromRequest(PendingPackageRequest pending)
        {
            var result = new PackageOperationResult { operation = pending.Operation };

            if (pending.Request.Status == StatusCode.Failure)
            {
                result.success = false;
                result.message = pending.Request.Error?.message ?? "Unknown package manager error";
                return result;
            }

            result.success = true;

            switch (pending.Operation)
            {
                case "list":
                    BuildListResult(pending, result);
                    break;
                case "search":
                case "info":
                    BuildSearchResult(pending, result);
                    break;
                case "search-all":
                    BuildSearchAllResult(pending, result);
                    break;
                case "add":
                    BuildAddResult(pending, result);
                    break;
                case "remove":
                    BuildRemoveResult(pending, result);
                    break;
                case "embed":
                    BuildEmbedResult(pending, result);
                    break;
            }

            return result;
        }

        private static void BuildListResult(PendingPackageRequest pending, PackageOperationResult result)
        {
            var listRequest = (ListRequest)pending.Request;
            foreach (var pkg in listRequest.Result)
            {
                result.packages.Add(ConvertPackageInfo(pkg));
            }
            result.totalCount = result.packages.Count;
            result.message = $"Listed {result.totalCount} packages";
        }

        private static void BuildSearchResult(PendingPackageRequest pending, PackageOperationResult result)
        {
            var searchRequest = (SearchRequest)pending.Request;
            if (pending.Operation == "info")
            {
                // For info, find the exact match by package name
                foreach (var pkg in searchRequest.Result)
                {
                    if (pkg.name == pending.Context)
                    {
                        result.package = ConvertPackageInfo(pkg);
                        result.message = $"Retrieved info for {pending.Context}";
                        return;
                    }
                }
                result.success = false;
                result.message = $"Package not found: {pending.Context}";
            }
            else
            {
                foreach (var pkg in searchRequest.Result)
                {
                    result.packages.Add(ConvertPackageInfo(pkg));
                }
                result.totalCount = result.packages.Count;
                result.message = $"Found {result.totalCount} package(s) matching '{pending.Context}'";
            }
        }

        private static void BuildSearchAllResult(PendingPackageRequest pending, PackageOperationResult result)
        {
            var searchRequest = (SearchRequest)pending.Request;
            foreach (var pkg in searchRequest.Result)
            {
                result.packages.Add(ConvertPackageInfo(pkg));
            }
            result.totalCount = result.packages.Count;
            result.message = $"Found {result.totalCount} available packages";
        }

        private static void BuildAddResult(PendingPackageRequest pending, PackageOperationResult result)
        {
            var addRequest = (AddRequest)pending.Request;
            result.package = ConvertPackageInfo(addRequest.Result);
            result.message = $"Added {addRequest.Result.name}@{addRequest.Result.version}";
        }

        private static void BuildRemoveResult(PendingPackageRequest pending, PackageOperationResult result)
        {
            result.packageName = pending.Context;
            result.message = $"Removed {pending.Context}";
        }

        private static void BuildEmbedResult(PendingPackageRequest pending, PackageOperationResult result)
        {
            var embedRequest = (EmbedRequest)pending.Request;
            result.package = ConvertPackageInfo(embedRequest.Result);
            result.message = $"Embedded {embedRequest.Result.name} to Packages/";
        }

        private static PackageInfoData ConvertPackageInfo(UnityEditor.PackageManager.PackageInfo pkg)
        {
            var data = new PackageInfoData
            {
                name = pkg.name,
                version = pkg.version,
                displayName = pkg.displayName,
                description = pkg.description,
                source = pkg.source.ToString().ToLower(),
                resolvedPath = pkg.resolvedPath,
            };

            if (pkg.dependencies is not null)
            {
                foreach (var dep in pkg.dependencies)
                {
                    data.dependencies.Add(new PackageDependency
                    {
                        name = dep.name,
                        version = dep.version
                    });
                }
            }

            if (pkg.keywords is not null)
            {
                data.keywords = new List<string>(pkg.keywords);
            }

            if (pkg.author is not null)
            {
                data.author = pkg.author.name;
            }

            data.documentationUrl = pkg.documentationUrl;
            return data;
        }

        private class PendingPackageRequest
        {
            public string CommandId;
            public string CommandType;
            public Request Request;
            public string Operation;
            public string Context;
            public DateTime StartTime;
        }
    }
}
