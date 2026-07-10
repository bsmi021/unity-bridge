using System;
using System.Collections.Generic;
using System.IO;

namespace BWS.Editor.ClaudeCodeBridge
{
    internal static class ExecuteScriptManifestValidator
    {
        private static readonly HashSet<string> ReturnSchemas = new HashSet<string>(
            new[] { "auto", "void", "scalar", "collection", "dictionary", "unity-object", "dto" },
            StringComparer.Ordinal);

        public static bool Validate(ExecuteScriptManifest manifest, out string message)
        {
            message = "";
            if (manifest == null)
            {
                message = "execution manifest is required";
                return false;
            }

            manifest.intent = (manifest.intent ?? "").Trim().ToLowerInvariant();
            manifest.returnSchema = (manifest.returnSchema ?? "").Trim().ToLowerInvariant();
            manifest.undoLabel = (manifest.undoLabel ?? "").Trim();
            manifest.expectedAssemblies ??= new List<string>();
            manifest.expectedAssemblyIdentities ??= new List<ExecuteScriptAssemblyRequest>();
            manifest.declaredObjectIds ??= new List<string>();
            manifest.declaredFilePaths ??= new List<string>();
            if (manifest.intent != "read-only" && manifest.intent != "mutating")
                return Fail("manifest intent must be read-only or mutating", out message);
            if (manifest.timeoutMs <= 0 || manifest.timeoutMs > 3600000)
                return Fail("manifest timeoutMs must be between 1 and 3600000", out message);
            if (!ReturnSchemas.Contains(manifest.returnSchema))
                return Fail($"unsupported return schema: {manifest.returnSchema}", out message);
            if (manifest.intent == "mutating" && string.IsNullOrWhiteSpace(manifest.undoLabel))
                return Fail("manifest undoLabel is required for mutating intent", out message);
            if (manifest.intent == "mutating"
                && manifest.declaredObjectIds.Count == 0
                && manifest.declaredFilePaths.Count == 0)
            {
                return Fail(
                    "mutating intent requires at least one declared object or file target",
                    out message);
            }
            if (!ValidateAssemblies(manifest.expectedAssemblies, out message))
                return false;
            if (!ValidateAssemblyIdentities(manifest.expectedAssemblyIdentities, out message))
                return false;
            if (!ValidateDistinctValues(
                manifest.declaredObjectIds, "declared object ID", out message))
            {
                return false;
            }
            return ValidateDistinctValues(
                manifest.declaredFilePaths, "declared file path", out message);
        }

        private static bool ValidateAssemblyIdentities(
            List<ExecuteScriptAssemblyRequest> requests, out string message)
        {
            var seen = new HashSet<string>(StringComparer.OrdinalIgnoreCase);
            foreach (var request in requests)
            {
                if (!NormalizeExactRequest(request, out message))
                    return false;
                var key = $"{request.fullName}\n{request.mvid}\n{request.path}";
                if (!seen.Add(key))
                    return Fail("duplicate expected assembly identity", out message);
            }
            message = "";
            return true;
        }

        private static bool NormalizeExactRequest(
            ExecuteScriptAssemblyRequest request, out string message)
        {
            if (request == null)
                return Fail("expected assembly identities cannot contain null", out message);
            request.name = (request.name ?? "").Trim();
            request.fullName = (request.fullName ?? "").Trim();
            request.mvid = (request.mvid ?? "").Trim();
            request.path = (request.path ?? "").Trim();
            if (request.name.Length > 0)
                return Fail("exact assembly identity cannot include a simple name", out message);
            if (request.fullName.Length == 0 || request.mvid.Length == 0 || request.path.Length == 0)
                return Fail("exact assembly identity requires fullName, mvid, and path", out message);
            if (!Guid.TryParse(request.mvid, out var parsedMvid))
                return Fail($"invalid assembly MVID: {request.mvid}", out message);
            if (!Path.IsPathFullyQualified(request.path))
                return Fail($"assembly identity path must be fully qualified: {request.path}", out message);
            request.mvid = parsedMvid.ToString("D");
            request.path = ExecuteScriptAssemblyResolver.NormalizeLoadedPath(request.path);
            message = "";
            return true;
        }

        private static bool ValidateAssemblies(List<string> names, out string message)
        {
            var seen = new HashSet<string>(StringComparer.Ordinal);
            for (var index = 0; index < names.Count; index++)
            {
                names[index] = (names[index] ?? "").Trim();
                if (names[index].Length == 0)
                    return Fail("expected assembly names cannot be empty", out message);
                if (!seen.Add(names[index]))
                    return Fail($"duplicate expected assembly name: {names[index]}", out message);
            }
            message = "";
            return true;
        }

        private static bool ValidateDistinctValues(
            List<string> values, string label, out string message)
        {
            var seen = new HashSet<string>(StringComparer.Ordinal);
            for (var index = 0; index < values.Count; index++)
            {
                values[index] = (values[index] ?? "").Trim();
                if (values[index].Length == 0)
                    return Fail($"{label}s cannot be empty", out message);
                if (!seen.Add(values[index]))
                    return Fail($"duplicate {label}: {values[index]}", out message);
            }
            message = "";
            return true;
        }

        private static bool Fail(string error, out string message)
        {
            message = error;
            return false;
        }
    }
}
