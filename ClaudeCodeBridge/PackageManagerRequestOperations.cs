using System;
using System.Collections.Generic;
using System.Linq;
using UnityEditor.PackageManager;
using UnityEditor.PackageManager.Requests;

namespace BWS.Editor.ClaudeCodeBridge
{
    public partial class PackageManagerCommandHandler
    {
        private BridgeResponse StartBatchRequest(
            BridgeCommand command, PackageOperationParams parameters)
        {
            string[] toAdd = CleanPackageArray(parameters.packagesToAdd);
            string[] toRemove = CleanPackageArray(parameters.packagesToRemove);
            if (toAdd.Length == 0 && toRemove.Length == 0)
            {
                return BridgeResponse.Error(command.commandId, CommandType,
                    "batch requires at least one packagesToAdd or packagesToRemove value");
            }

            var request = Client.AddAndRemove(toAdd, toRemove);
            RegisterPending(command, request, "batch", null, toAdd, toRemove);
            return BridgeResponse.Running(command.commandId, CommandType,
                "{\"operation\":\"batch\",\"success\":true,\"message\":\"Updating packages...\"}");
        }

        private BridgeResponse StartPackRequest(
            BridgeCommand command, PackageOperationParams parameters)
        {
            if (string.IsNullOrEmpty(parameters.packageFolder))
            {
                return BridgeResponse.Error(command.commandId, CommandType,
                    "packageFolder is required for pack operation");
            }
            if (string.IsNullOrEmpty(parameters.targetFolder))
            {
                return BridgeResponse.Error(command.commandId, CommandType,
                    "targetFolder is required for pack operation");
            }

            var request = Client.Pack(parameters.packageFolder, parameters.targetFolder);
            RegisterPending(command, request, "pack", null, null, null,
                parameters.packageFolder, parameters.targetFolder);
            return BridgeResponse.Running(command.commandId, CommandType,
                "{\"operation\":\"pack\",\"success\":true,\"message\":\"Packing package...\"}");
        }

        private BridgeResponse StartClearCacheRequest(
            BridgeCommand command, PackageOperationParams parameters)
        {
            if (!parameters.confirmClearCache)
            {
                return BridgeResponse.Error(command.commandId, CommandType,
                    "confirmClearCache must be true for clear-cache operation");
            }

            var request = Client.ClearCache();
            RegisterPending(command, request, "clear-cache");
            return BridgeResponse.Running(command.commandId, CommandType,
                "{\"operation\":\"clear-cache\",\"success\":true,\"message\":\"Clearing package cache...\"}");
        }

        private static void BuildBatchResult(
            PendingPackageRequest pending, PackageOperationResult result)
        {
            var request = (AddAndRemoveRequest)pending.Request;
            result.packagesToAdd = pending.PackagesToAdd ?? new string[0];
            result.packagesToRemove = pending.PackagesToRemove ?? new string[0];
            foreach (var pkg in request.Result)
                result.packages.Add(ConvertPackageInfo(pkg));
            result.totalCount = result.packages.Count;
            result.message = "Updated packages: added " + result.packagesToAdd.Length
                + ", removed " + result.packagesToRemove.Length;
        }

        private static void BuildAddResult(
            PendingPackageRequest pending, PackageOperationResult result)
        {
            var request = (AddRequest)pending.Request;
            result.package = ConvertPackageInfo(request.Result);
            result.message = $"Added {request.Result.name}@{request.Result.version}";
        }

        private static void BuildRemoveResult(
            PendingPackageRequest pending, PackageOperationResult result)
        {
            result.packageName = pending.Context;
            result.message = $"Removed {pending.Context}";
        }

        private static void BuildEmbedResult(
            PendingPackageRequest pending, PackageOperationResult result)
        {
            var request = (EmbedRequest)pending.Request;
            result.package = ConvertPackageInfo(request.Result);
            result.message = $"Embedded {request.Result.name} to Packages/";
        }

        private static void BuildPackResult(
            PendingPackageRequest pending, PackageOperationResult result)
        {
            var request = (PackRequest)pending.Request;
            result.packageFolder = pending.PackageFolder;
            result.targetFolder = pending.TargetFolder;
            result.tarballPath = request.Result.tarballPath;
            result.message = $"Packed {pending.PackageFolder} to {result.tarballPath}";
        }

        private static void BuildClearCacheResult(
            PendingPackageRequest pending, PackageOperationResult result)
        {
            result.message = "Cleared Unity Package Manager global cache";
        }

        private static PackageInfoData ConvertPackageInfo(
            UnityEditor.PackageManager.PackageInfo pkg)
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
                data.keywords = new List<string>(pkg.keywords);

            if (pkg.author is not null)
                data.author = pkg.author.name;

            data.documentationUrl = pkg.documentationUrl;
            return data;
        }

        private static string[] CleanPackageArray(string[] values)
        {
            if (values == null)
                return new string[0];

            var cleaned = new List<string>();
            foreach (string value in values)
            {
                if (!string.IsNullOrWhiteSpace(value))
                    cleaned.Add(value.Trim());
            }
            return cleaned.ToArray();
        }
    }
}
