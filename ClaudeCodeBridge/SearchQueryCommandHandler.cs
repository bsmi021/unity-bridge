using System;
using System.Collections.Generic;
using System.Linq;
using System.Reflection;
using UnityEditor;
using UnityEngine;

namespace BWS.Editor.ClaudeCodeBridge
{
    /// <summary>
    /// Executes Unity Search queries against the built-in Quick Search API
    /// (com.unity.search). The Search service is bundled with the Editor on
    /// Unity 2021.2+ but lives in the UnityEditor.Search namespace which
    /// is only loaded when the package is active; we access it by reflection
    /// to keep the bridge compilable across Unity versions.
    ///
    /// SUPPORTED OPERATIONS:
    /// 1. "query"           - Run a Quick Search query and return ranked results.
    /// 2. "providers"       - List registered Search providers (asset, scene, menu, ...).
    /// </summary>
    public class SearchQueryCommandHandler : ICommandHandler
    {
        public string CommandType => "search-query";

        private const int DEFAULT_MAX_RESULTS = 100;

        public BridgeResponse Execute(BridgeCommand command)
        {
            try
            {
                var parameters = JsonUtility.FromJson<SearchQueryParams>(
                    command.parametersJson ?? "{}") ?? new SearchQueryParams();
                var operation = parameters.operation?.ToLower() ?? "query";

                switch (operation)
                {
                    case "query":
                        return HandleQuery(command, parameters);
                    case "providers":
                        return HandleProviders(command);
                    default:
                        return BridgeResponse.Error(
                            command.commandId, command.commandType,
                            $"Unknown operation: {parameters.operation}. Supported: query, providers");
                }
            }
            catch (Exception ex)
            {
                BridgeLogger.LogError($"Search query error: {ex}");
                return BridgeResponse.Error(command.commandId, command.commandType, ex.ToString());
            }
        }

        private BridgeResponse HandleQuery(BridgeCommand command, SearchQueryParams p)
        {
            if (string.IsNullOrEmpty(p.query))
            {
                return BridgeResponse.Error(
                    command.commandId, command.commandType,
                    "query parameter is required for operation 'query'.");
            }

            var searchServiceType = FindType("UnityEditor.Search.SearchService");
            var contextType = FindType("UnityEditor.Search.SearchContext");
            var itemType = FindType("UnityEditor.Search.SearchItem");
            if (searchServiceType == null || contextType == null || itemType == null)
            {
                return BridgeResponse.Error(
                    command.commandId, command.commandType,
                    "UnityEditor.Search API not available in this Unity version.");
            }

            // Build a SearchContext from the query string.
            // Prefer SearchService.CreateContext(string, SearchFlags) when present.
            object ctx = CreateContext(searchServiceType, contextType, p.query);
            if (ctx == null)
            {
                return BridgeResponse.Error(
                    command.commandId, command.commandType,
                    "Could not create SearchContext.");
            }

            // Execute synchronous request: SearchService.Request(SearchContext, SearchFlags.Synchronous)
            var items = ExecuteRequest(searchServiceType, ctx);
            if (items == null)
            {
                return BridgeResponse.Error(
                    command.commandId, command.commandType,
                    "SearchService.Request did not return a usable enumerable.");
            }

            int max = p.maxResults > 0 ? p.maxResults : DEFAULT_MAX_RESULTS;
            var results = new List<SearchResultItem>();
            foreach (var item in items)
            {
                if (item == null) continue;
                if (results.Count >= max) break;

                results.Add(new SearchResultItem
                {
                    id = SafeGetString(item, "id"),
                    label = SafeInvokeString(item, "GetLabel", ctx, true)
                            ?? SafeGetString(item, "label"),
                    description = SafeInvokeString(item, "GetDescription", ctx, true)
                                  ?? SafeGetString(item, "description"),
                    provider = SafeGetNestedString(item, "provider", "name"),
                    score = SafeGetInt(item, "score"),
                });
            }

            var response = new SearchQueryResult
            {
                success = true,
                query = p.query,
                total = results.Count,
                truncated = results.Count >= max,
                items = results,
            };
            return BridgeResponse.Success(
                command.commandId, command.commandType,
                JsonUtility.ToJson(response));
        }

        private BridgeResponse HandleProviders(BridgeCommand command)
        {
            var searchServiceType = FindType("UnityEditor.Search.SearchService");
            if (searchServiceType == null)
            {
                return BridgeResponse.Error(
                    command.commandId, command.commandType,
                    "UnityEditor.Search API not available in this Unity version.");
            }

            var providersProp = searchServiceType.GetProperty(
                "Providers", BindingFlags.Public | BindingFlags.Static);
            var providersObj = providersProp?.GetValue(null) as System.Collections.IEnumerable;
            var response = new SearchProvidersResult { success = true, providers = new List<SearchProviderInfo>() };
            if (providersObj != null)
            {
                foreach (var provider in providersObj)
                {
                    response.providers.Add(new SearchProviderInfo
                    {
                        id = SafeGetString(provider, "id") ?? SafeGetString(provider, "name"),
                        name = SafeGetString(provider, "name"),
                        active = SafeGetBool(provider, "active"),
                        filterId = SafeGetString(provider, "filterId"),
                    });
                }
            }
            return BridgeResponse.Success(
                command.commandId, command.commandType,
                JsonUtility.ToJson(response));
        }

        // --- Reflection helpers ---

        private static Type FindType(string fullName)
        {
            foreach (var asm in AppDomain.CurrentDomain.GetAssemblies())
            {
                var t = asm.GetType(fullName);
                if (t != null) return t;
            }
            return null;
        }

        private static object CreateContext(Type searchServiceType, Type contextType, string query)
        {
            // Preferred: SearchService.CreateContext(string)
            var createCtx = searchServiceType.GetMethods(BindingFlags.Public | BindingFlags.Static)
                .FirstOrDefault(m => m.Name == "CreateContext"
                                     && m.GetParameters().Length == 1
                                     && m.GetParameters()[0].ParameterType == typeof(string));
            if (createCtx != null)
            {
                return createCtx.Invoke(null, new object[] { query });
            }

            // Fallback: new SearchContext(IEnumerable<SearchProvider>, string)
            var ctor = contextType.GetConstructors()
                .FirstOrDefault(c => c.GetParameters().Length == 1
                                     && c.GetParameters()[0].ParameterType == typeof(string));
            return ctor?.Invoke(new object[] { query });
        }

        private static IEnumerable<object> ExecuteRequest(Type searchServiceType, object ctx)
        {
            // Look for Request(SearchContext, SearchFlags) with Synchronous flag.
            var requestMethods = searchServiceType.GetMethods(BindingFlags.Public | BindingFlags.Static)
                .Where(m => m.Name == "Request")
                .ToList();

            // Prefer the synchronous overload.
            var sync = requestMethods.FirstOrDefault(m =>
            {
                var ps = m.GetParameters();
                return ps.Length == 2 && ps[1].ParameterType.Name == "SearchFlags";
            });
            if (sync != null)
            {
                var flagsType = sync.GetParameters()[1].ParameterType;
                var syncFlag = Enum.Parse(flagsType, "Synchronous");
                var resultObj = sync.Invoke(null, new object[] { ctx, syncFlag });
                return AsEnumerable(resultObj);
            }

            // Fallback: single-arg Request returns an async enumerable; take a best-effort snapshot.
            var single = requestMethods.FirstOrDefault(m => m.GetParameters().Length == 1);
            if (single != null)
            {
                var resultObj = single.Invoke(null, new object[] { ctx });
                return AsEnumerable(resultObj);
            }
            return null;
        }

        private static IEnumerable<object> AsEnumerable(object source)
        {
            if (source == null) yield break;
            if (source is System.Collections.IEnumerable e)
            {
                foreach (var o in e) yield return o;
            }
        }

        private static string SafeGetString(object obj, string name)
        {
            if (obj == null) return null;
            var t = obj.GetType();
            var f = t.GetField(name, BindingFlags.Public | BindingFlags.Instance);
            if (f != null) return f.GetValue(obj)?.ToString();
            var p = t.GetProperty(name, BindingFlags.Public | BindingFlags.Instance);
            return p?.GetValue(obj)?.ToString();
        }

        private static bool SafeGetBool(object obj, string name)
        {
            var v = SafeGetString(obj, name);
            return v != null && bool.TryParse(v, out var b) && b;
        }

        private static int SafeGetInt(object obj, string name)
        {
            var v = SafeGetString(obj, name);
            return v != null && int.TryParse(v, out var i) ? i : 0;
        }

        private static string SafeGetNestedString(object obj, string outer, string inner)
        {
            if (obj == null) return null;
            var t = obj.GetType();
            var p = t.GetProperty(outer, BindingFlags.Public | BindingFlags.Instance)?.GetValue(obj)
                    ?? t.GetField(outer, BindingFlags.Public | BindingFlags.Instance)?.GetValue(obj);
            return p == null ? null : SafeGetString(p, inner);
        }

        private static string SafeInvokeString(object obj, string methodName, params object[] args)
        {
            if (obj == null) return null;
            try
            {
                var m = obj.GetType().GetMethods(BindingFlags.Public | BindingFlags.Instance)
                    .FirstOrDefault(x => x.Name == methodName && x.GetParameters().Length == args.Length);
                return m?.Invoke(obj, args)?.ToString();
            }
            catch { return null; }
        }
    }

    [Serializable]
    public class SearchQueryParams
    {
        public string operation;
        public string query;
        public int maxResults;
    }

    [Serializable]
    public class SearchResultItem
    {
        public string id;
        public string label;
        public string description;
        public string provider;
        public int score;
    }

    [Serializable]
    public class SearchQueryResult
    {
        public bool success;
        public string query;
        public int total;
        public bool truncated;
        public List<SearchResultItem> items;
    }

    [Serializable]
    public class SearchProviderInfo
    {
        public string id;
        public string name;
        public bool active;
        public string filterId;
    }

    [Serializable]
    public class SearchProvidersResult
    {
        public bool success;
        public List<SearchProviderInfo> providers;
    }
}
