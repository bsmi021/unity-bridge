using System;
using System.Collections;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Reflection;
using UnityEngine;

namespace BWS.Editor.ClaudeCodeBridge
{
    public class EntitiesCommandHandler : ICommandHandler
    {
        private const string PackageName = "com.unity.entities";
        private const string WorldTypeName = "Unity.Entities.World";
        private const int DefaultMaxSystems = 100;
        private const int DefaultMaxArchetypes = 100;
        private const int DefaultMaxComponents = 64;

        public string CommandType => "entities";

        public BridgeResponse Execute(BridgeCommand command)
        {
            string operation = "availability";
            try
            {
                var p = JsonUtility.FromJson<EntitiesParams>(
                    command.parametersJson ?? "{}") ?? new EntitiesParams();
                operation = string.IsNullOrEmpty(p.operation)
                    ? "availability"
                    : p.operation.ToLowerInvariant();

                switch (operation)
                {
                    case "availability":
                        return Reply(command, Availability(operation));
                    case "list-worlds":
                        return Reply(command, ListWorlds(operation, p));
                    case "world-summary":
                        return Reply(command, WorldSummary(operation, p));
                    case "list-systems":
                        return Reply(command, ListSystems(operation, p));
                    case "list-archetypes":
                        return Reply(command, ListArchetypes(operation, p));
                    default:
                        return Reply(command, Fail(operation,
                            "Unknown operation. Supported: availability, list-worlds, "
                            + "world-summary, list-systems, list-archetypes"));
                }
            }
            catch (Exception ex)
            {
                BridgeLogger.LogError($"Entities error: {ex}");
                return Reply(command, Fail(operation, ex.ToString()));
            }
        }

        private static BridgeResponse Reply(BridgeCommand command, EntitiesResult result)
        {
            string json = JsonUtility.ToJson(result);
            if (result.success) return BridgeResponse.Success(command.commandId, command.commandType, json);
            return BridgeResponse.Error(command.commandId, command.commandType, result.message);
        }

        private static EntitiesResult Availability(string operation)
        {
            Type worldType = FindType(WorldTypeName);
            var result = BaseResult(operation, worldType);
            result.worldCount = worldType == null ? 0 : GetWorlds(worldType).Count;
            result.message = result.apiAvailable
                ? "Unity Entities API is available."
                : "Unity Entities API is not available.";
            return result;
        }

        private static EntitiesResult ListWorlds(string operation, EntitiesParams p)
        {
            Type worldType = FindType(WorldTypeName);
            if (worldType == null) return Unavailable(operation);

            var result = BaseResult(operation, worldType);
            int max = MaxSystems(p.maxSystems);
            foreach (object world in GetWorlds(worldType))
                result.worlds.Add(BuildWorldInfo(world, p.includeSystems, max));

            result.worldCount = result.worlds.Count;
            result.message = $"Found {result.worldCount} Entities world(s).";
            return result;
        }

        private static EntitiesResult WorldSummary(string operation, EntitiesParams p)
        {
            Type worldType = FindType(WorldTypeName);
            if (worldType == null) return Unavailable(operation);

            object world = FindWorld(worldType, p.worldName);
            if (world == null) return Fail(operation, WorldMissingMessage(p.worldName));

            var result = BaseResult(operation, worldType);
            result.world = BuildWorldInfo(world, p.includeSystems, MaxSystems(p.maxSystems));
            result.worldCount = 1;
            result.message = $"Summarized Entities world: {result.world.name}";
            return result;
        }

        private static EntitiesResult ListSystems(string operation, EntitiesParams p)
        {
            Type worldType = FindType(WorldTypeName);
            if (worldType == null) return Unavailable(operation);

            object world = FindWorld(worldType, p.worldName);
            if (world == null) return Fail(operation, WorldMissingMessage(p.worldName));

            var result = BaseResult(operation, worldType);
            foreach (var system in FilterSystems(world, p.namespaceFilter, MaxSystems(p.maxSystems)))
                result.systems.Add(BuildSystemInfo(system));

            result.world = BuildWorldInfo(world, false, 0);
            result.message = $"Found {result.systems.Count} managed Entities system(s).";
            return result;
        }

        private static EntitiesResult ListArchetypes(string operation, EntitiesParams p)
        {
            Type worldType = FindType(WorldTypeName);
            if (worldType == null) return Unavailable(operation);

            object world = FindWorld(worldType, p.worldName);
            if (world == null) return Fail(operation, WorldMissingMessage(p.worldName));

            var result = BaseResult(operation, worldType);
            result.world = BuildWorldInfo(world, false, 0);
            result.archetypes = EntitiesArchetypeReflection.List(
                world,
                MaxValue(p.maxArchetypes, DefaultMaxArchetypes),
                p.includeComponents,
                MaxValue(p.maxComponents, DefaultMaxComponents),
                out string message,
                out bool succeeded);
            result.archetypeCount = result.archetypes.Count;
            result.success = succeeded;
            result.message = message;
            return result;
        }

        private static EntitiesWorldInfo BuildWorldInfo(
            object world, bool includeSystems, int maxSystems)
        {
            var systems = ToList(GetValue(world, "Systems"), maxSystems <= 0 ? int.MaxValue : maxSystems);
            var info = new EntitiesWorldInfo
            {
                name = Text(GetValue(world, "Name")),
                flags = Text(GetValue(world, "Flags")),
                version = Text(GetValue(world, "Version")),
                sequenceNumber = Text(GetValue(world, "SequenceNumber")),
                isCreated = Bool(GetValue(world, "IsCreated")),
                isDefault = ReferenceEquals(world, GetDefaultWorld(world.GetType())),
                entityCount = QueryCount(world, "UniversalQuery"),
                systemEntityCount = QueryCount(world, "UniversalQueryWithSystems"),
                systemCount = CountEnumerable(GetValue(world, "Systems"))
            };
            if (includeSystems)
                foreach (object system in systems) info.systems.Add(BuildSystemInfo(system));
            return info;
        }

        private static List<object> FilterSystems(object world, string namespaceFilter, int max)
        {
            var systems = ToList(GetValue(world, "Systems"), int.MaxValue);
            if (!string.IsNullOrEmpty(namespaceFilter))
                systems = systems.Where(s => StartsWithNamespace(s, namespaceFilter)).ToList();
            return systems.Take(max).ToList();
        }

        private static bool StartsWithNamespace(object system, string namespaceFilter)
        {
            return (system.GetType().Namespace ?? "").StartsWith(
                namespaceFilter, StringComparison.Ordinal);
        }

        private static EntitiesSystemInfo BuildSystemInfo(object system)
        {
            Type type = system.GetType();
            return new EntitiesSystemInfo
            {
                name = type.Name,
                fullName = type.FullName,
                namespaceName = type.Namespace,
                enabled = Bool(GetValue(system, "Enabled")),
                entityQueryCount = CountEnumerable(GetValue(system, "EntityQueries")),
                lastSystemVersion = Text(GetValue(system, "LastSystemVersion")),
                worldName = Text(GetValue(GetValue(system, "World"), "Name"))
            };
        }

        private static int QueryCount(object world, string queryProperty)
        {
            try
            {
                object entityManager = GetValue(world, "EntityManager");
                object query = GetValue(entityManager, queryProperty);
                object count = query?.GetType().GetMethod("CalculateEntityCount", Type.EmptyTypes)
                    ?.Invoke(query, null);
                return Int(count, -1);
            }
            catch
            {
                return -1;
            }
        }

        private static object FindWorld(Type worldType, string worldName)
        {
            if (!string.IsNullOrEmpty(worldName))
                return GetWorlds(worldType).FirstOrDefault(w => Text(GetValue(w, "Name")) == worldName);
            return GetDefaultWorld(worldType) ?? GetWorlds(worldType).FirstOrDefault();
        }

        private static object GetDefaultWorld(Type worldType)
        {
            return GetStaticValue(worldType, "DefaultGameObjectInjectionWorld");
        }

        private static List<object> GetWorlds(Type worldType)
        {
            return ToList(GetStaticValue(worldType, "All"), int.MaxValue);
        }

        private static object GetStaticValue(Type type, string name)
        {
            const BindingFlags flags = BindingFlags.Public | BindingFlags.Static;
            return (object)type.GetProperty(name, flags)?.GetValue(null)
                ?? type.GetField(name, flags)?.GetValue(null);
        }

        private static object GetValue(object target, string name)
        {
            if (target == null) return null;
            const BindingFlags flags = BindingFlags.Public | BindingFlags.Instance;
            Type type = target.GetType();
            return (object)type.GetProperty(name, flags)?.GetValue(target)
                ?? type.GetField(name, flags)?.GetValue(target);
        }

        private static List<object> ToList(object value, int max)
        {
            var list = new List<object>();
            if (value is IEnumerable enumerable)
                foreach (object item in enumerable)
                {
                    if (item != null) list.Add(item);
                    if (list.Count >= max) break;
                }
            return list;
        }

        private static int CountEnumerable(object value)
        {
            if (value == null) return 0;
            object count = GetValue(value, "Count");
            if (count != null) return Int(count, 0);
            return value is IEnumerable enumerable ? enumerable.Cast<object>().Count() : 0;
        }

        private static int MaxSystems(int requested)
        {
            return MaxValue(requested, DefaultMaxSystems);
        }

        private static int MaxValue(int requested, int fallback)
        {
            return requested > 0 ? requested : fallback;
        }

        private static Type FindType(string fullName)
        {
            foreach (var assembly in AppDomain.CurrentDomain.GetAssemblies())
            {
                Type type = assembly.GetType(fullName);
                if (type != null) return type;
            }
            return null;
        }

        private static bool IsPackageAvailable()
        {
            string root = Directory.GetParent(Application.dataPath)?.FullName;
            if (string.IsNullOrEmpty(root)) return false;
            if (Directory.Exists(Path.Combine(root, "Packages", PackageName))) return true;
            string manifest = Path.Combine(root, "Packages", "manifest.json");
            return File.Exists(manifest) && File.ReadAllText(manifest).Contains(PackageName);
        }

        private static EntitiesResult BaseResult(string operation, Type worldType)
        {
            bool apiAvailable = worldType != null;
            return new EntitiesResult
            {
                success = true,
                operation = operation,
                packageAvailable = IsPackageAvailable() || apiAvailable,
                apiAvailable = apiAvailable,
            };
        }

        private static EntitiesResult Unavailable(string operation)
        {
            return Fail(operation, "Unity Entities API is not available.");
        }

        private static EntitiesResult Fail(string operation, string message)
        {
            Type worldType = FindType(WorldTypeName);
            var result = BaseResult(operation, worldType);
            result.success = false;
            result.message = message;
            return result;
        }

        private static string WorldMissingMessage(string worldName)
        {
            return string.IsNullOrEmpty(worldName)
                ? "No Entities world is available."
                : $"Entities world not found: {worldName}";
        }

        private static string Text(object value, string fallback = "")
        {
            return value == null ? fallback : value.ToString();
        }

        private static bool Bool(object value)
        {
            return value is bool b && b;
        }

        private static int Int(object value, int fallback)
        {
            try { return value == null ? fallback : Convert.ToInt32(value); }
            catch { return fallback; }
        }
    }

    [Serializable]
    public class EntitiesParams
    {
        public string operation;
        public string worldName;
        public bool includeSystems;
        public bool includeComponents;
        public string namespaceFilter;
        public int maxSystems;
        public int maxArchetypes;
        public int maxComponents;
    }

    [Serializable]
    public class EntitiesResult
    {
        public bool success;
        public string operation;
        public bool packageAvailable;
        public bool apiAvailable;
        public int worldCount;
        public string message;
        public EntitiesWorldInfo world;
        public List<EntitiesWorldInfo> worlds = new List<EntitiesWorldInfo>();
        public List<EntitiesSystemInfo> systems = new List<EntitiesSystemInfo>();
        public int archetypeCount;
        public List<EntitiesArchetypeInfo> archetypes = new List<EntitiesArchetypeInfo>();
    }

    [Serializable]
    public class EntitiesWorldInfo
    {
        public string name;
        public string flags;
        public string version;
        public string sequenceNumber;
        public bool isCreated;
        public bool isDefault;
        public int entityCount;
        public int systemEntityCount;
        public int systemCount;
        public List<EntitiesSystemInfo> systems = new List<EntitiesSystemInfo>();
    }

    [Serializable]
    public class EntitiesSystemInfo
    {
        public string name;
        public string fullName;
        public string namespaceName;
        public bool enabled;
        public int entityQueryCount;
        public string lastSystemVersion;
        public string worldName;
    }
}
