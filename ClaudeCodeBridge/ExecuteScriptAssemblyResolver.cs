using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Reflection;

namespace BWS.Editor.ClaudeCodeBridge
{
    internal sealed class ExecuteScriptAssemblyCandidate
    {
        public string Name { get; }
        public string Location { get; }
        public string FullName { get; }
        public string Mvid { get; }
        public bool IsDynamic { get; }
        public bool IsFacade { get; }
        public Assembly Assembly { get; }
        public ExecuteScriptAssemblyIdentity Identity => new ExecuteScriptAssemblyIdentity
        {
            name = Name,
            fullName = FullName,
            mvid = Mvid,
            path = Location,
        };

        public ExecuteScriptAssemblyCandidate(
            string name, string location, bool isDynamic, bool isFacade)
            : this(name, location, name, "", isDynamic, isFacade, null)
        {
        }

        public ExecuteScriptAssemblyCandidate(
            string name,
            string location,
            string fullName,
            string mvid,
            bool isDynamic,
            bool isFacade)
            : this(name, location, fullName, mvid, isDynamic, isFacade, null)
        {
        }

        private ExecuteScriptAssemblyCandidate(
            string name,
            string location,
            string fullName,
            string mvid,
            bool isDynamic,
            bool isFacade,
            Assembly assembly)
        {
            Name = name ?? "";
            Location = ExecuteScriptAssemblyResolver.NormalizeLoadedPath(location);
            FullName = fullName ?? "";
            Mvid = NormalizeMvid(mvid);
            IsDynamic = isDynamic;
            IsFacade = isFacade;
            Assembly = assembly;
        }

        public static ExecuteScriptAssemblyCandidate FromAssembly(Assembly assembly)
        {
            try
            {
                var name = assembly.GetName().Name ?? "";
                return new ExecuteScriptAssemblyCandidate(
                    name,
                    assembly.IsDynamic ? "" : assembly.Location,
                    assembly.FullName,
                    assembly.ManifestModule.ModuleVersionId.ToString("D"),
                    assembly.IsDynamic,
                    IsKnownFacade(name),
                    assembly);
            }
            catch
            {
                return new ExecuteScriptAssemblyCandidate("", "", "", "", true, false, assembly);
            }
        }

        private static string NormalizeMvid(string value)
        {
            return Guid.TryParse(value, out var parsed) ? parsed.ToString("D") : value ?? "";
        }

        private static bool IsKnownFacade(string name)
        {
            return name == "netstandard"
                || name == "System.Runtime"
                || name == "System.Private.CoreLib"
                || name == "mscorlib";
        }
    }

    internal static class ExecuteScriptAssemblyResolver
    {
        public static List<Assembly> Resolve(
            IEnumerable<Assembly> loadedAssemblies,
            IEnumerable<string> baselineNames,
            IEnumerable<string> expectedNames,
            IEnumerable<ExecuteScriptAssemblyRequest> expectedIdentities,
            out List<ExecuteScriptAssemblyIdentity> resolvedIdentities,
            out ExecuteScriptAssemblyResolutionIssue issue)
        {
            var requested = SimpleRequests(baselineNames.Concat(expectedNames))
                .Concat(expectedIdentities ?? Enumerable.Empty<ExecuteScriptAssemblyRequest>());
            var candidates = loadedAssemblies.Select(ExecuteScriptAssemblyCandidate.FromAssembly);
            var selected = SelectCandidates(candidates, requested, out issue);
            resolvedIdentities = selected.Select(candidate => candidate.Identity).ToList();
            if (issue != null)
                return new List<Assembly>();
            return selected.Select(candidate => candidate.Assembly)
                .Where(assembly => assembly != null)
                .ToList();
        }

        public static List<ExecuteScriptAssemblyCandidate> SelectCandidates(
            IEnumerable<ExecuteScriptAssemblyCandidate> candidates,
            IEnumerable<string> requestedNames,
            out string message)
        {
            var selected = SelectCandidates(candidates, SimpleRequests(requestedNames), out var issue);
            message = issue?.message ?? "";
            return selected;
        }

        public static List<ExecuteScriptAssemblyCandidate> SelectCandidates(
            IEnumerable<ExecuteScriptAssemblyCandidate> candidates,
            IEnumerable<ExecuteScriptAssemblyRequest> requests,
            out ExecuteScriptAssemblyResolutionIssue issue)
        {
            var usable = UsableCandidates(candidates);
            var selected = new List<ExecuteScriptAssemblyCandidate>();
            foreach (var request in OrderRequests(requests))
            {
                var matches = Match(usable, request);
                if (matches.Count != 1)
                {
                    issue = BuildIssue(request, matches, usable);
                    return new List<ExecuteScriptAssemblyCandidate>();
                }
                AddUnique(selected, matches[0]);
            }
            issue = null;
            return selected;
        }

        public static string NormalizeLoadedPath(string value)
        {
            if (string.IsNullOrWhiteSpace(value))
                return "";
            try
            {
                return Path.GetFullPath(value.Trim()).Replace('\\', '/').TrimEnd('/');
            }
            catch
            {
                return value.Trim().Replace('\\', '/').TrimEnd('/');
            }
        }

        private static List<ExecuteScriptAssemblyCandidate> UsableCandidates(
            IEnumerable<ExecuteScriptAssemblyCandidate> candidates)
        {
            return candidates
                .Where(candidate => !candidate.IsDynamic)
                .Where(candidate => !candidate.IsFacade)
                .Where(candidate => candidate.Name.Length > 0 && candidate.Location.Length > 0)
                .ToList();
        }

        private static IEnumerable<ExecuteScriptAssemblyRequest> SimpleRequests(
            IEnumerable<string> requestedNames)
        {
            return (requestedNames ?? Enumerable.Empty<string>())
                .Distinct(StringComparer.Ordinal)
                .OrderBy(value => value, StringComparer.Ordinal)
                .Select(name => new ExecuteScriptAssemblyRequest { name = name });
        }

        private static IEnumerable<ExecuteScriptAssemblyRequest> OrderRequests(
            IEnumerable<ExecuteScriptAssemblyRequest> requests)
        {
            return (requests ?? Enumerable.Empty<ExecuteScriptAssemblyRequest>())
                .OrderBy(request => request.name ?? "", StringComparer.Ordinal)
                .ThenBy(request => request.fullName ?? "", StringComparer.Ordinal)
                .ThenBy(request => request.mvid ?? "", StringComparer.Ordinal)
                .ThenBy(request => NormalizeLoadedPath(request.path), StringComparer.OrdinalIgnoreCase);
        }

        private static List<ExecuteScriptAssemblyCandidate> Match(
            List<ExecuteScriptAssemblyCandidate> candidates,
            ExecuteScriptAssemblyRequest request)
        {
            IEnumerable<ExecuteScriptAssemblyCandidate> matches = candidates;
            if (!string.IsNullOrWhiteSpace(request.name))
                matches = matches.Where(candidate => candidate.Name == request.name);
            else
            {
                var path = NormalizeLoadedPath(request.path);
                matches = matches
                    .Where(candidate => candidate.FullName == request.fullName)
                    .Where(candidate => candidate.Mvid == request.mvid)
                    .Where(candidate => string.Equals(
                        candidate.Location, path, StringComparison.OrdinalIgnoreCase));
            }
            return matches.OrderBy(candidate => candidate.FullName, StringComparer.Ordinal)
                .ThenBy(candidate => candidate.Mvid, StringComparer.Ordinal)
                .ThenBy(candidate => candidate.Location, StringComparer.OrdinalIgnoreCase)
                .ToList();
        }

        private static ExecuteScriptAssemblyResolutionIssue BuildIssue(
            ExecuteScriptAssemblyRequest request,
            List<ExecuteScriptAssemblyCandidate> matches,
            List<ExecuteScriptAssemblyCandidate> usable)
        {
            var simple = !string.IsNullOrWhiteSpace(request.name);
            var ambiguous = matches.Count > 1;
            var candidates = ambiguous
                ? matches
                : RelatedCandidates(usable, request);
            var label = simple ? request.name : request.fullName;
            var code = ambiguous
                ? (simple ? "ambiguous_simple_name" : "ambiguous_identity")
                : (simple ? "assembly_not_loaded" : "assembly_identity_not_loaded");
            var message = ambiguous
                ? $"Assembly request is ambiguous: {label}"
                : $"Expected assembly is not loaded or safely referenceable: {label}";
            return new ExecuteScriptAssemblyResolutionIssue
            {
                code = code,
                message = message,
                request = request,
                candidates = candidates.Select(candidate => candidate.Identity).ToList(),
            };
        }

        private static List<ExecuteScriptAssemblyCandidate> RelatedCandidates(
            List<ExecuteScriptAssemblyCandidate> candidates,
            ExecuteScriptAssemblyRequest request)
        {
            var simpleName = request.name;
            if (string.IsNullOrEmpty(simpleName) && !string.IsNullOrEmpty(request.fullName))
            {
                try { simpleName = new AssemblyName(request.fullName).Name; }
                catch { simpleName = ""; }
            }
            return candidates.Where(candidate => candidate.Name == simpleName)
                .OrderBy(candidate => candidate.FullName, StringComparer.Ordinal)
                .ThenBy(candidate => candidate.Mvid, StringComparer.Ordinal)
                .ThenBy(candidate => candidate.Location, StringComparer.OrdinalIgnoreCase)
                .ToList();
        }

        private static void AddUnique(
            List<ExecuteScriptAssemblyCandidate> selected,
            ExecuteScriptAssemblyCandidate candidate)
        {
            if (!selected.Any(item => item.FullName == candidate.FullName
                && item.Mvid == candidate.Mvid
                && string.Equals(
                    item.Location, candidate.Location, StringComparison.OrdinalIgnoreCase)))
            {
                selected.Add(candidate);
            }
        }
    }
}
