using System;
using System.Collections.Generic;
using System.Linq;
using System.Reflection;

namespace BWS.Editor.ClaudeCodeBridge
{
    internal static class EntitiesArchetypeReflection
    {
        private const string EntityArchetypeTypeName = "Unity.Entities.EntityArchetype";
        private const string NativeListTypeName = "Unity.Collections.NativeList`1";
        private const string AllocatorTypeName = "Unity.Collections.Allocator";
        private const string AllocatorManagerTypeName = "Unity.Collections.AllocatorManager";

        public static List<EntitiesArchetypeInfo> List(
            object world,
            int maxArchetypes,
            bool includeComponents,
            int maxComponents,
            out string message,
            out bool succeeded)
        {
            var archetypes = new List<EntitiesArchetypeInfo>();
            succeeded = false;
            object entityManager = GetValue(world, "EntityManager");
            if (entityManager == null)
            {
                message = "Entities world has no readable EntityManager.";
                return archetypes;
            }

            object nativeList = null;
            try
            {
                nativeList = CreateArchetypeList();
                FillArchetypeList(entityManager, nativeList);
                int total = Length(nativeList);
                for (int i = 0; i < Math.Min(total, maxArchetypes); i++)
                {
                    object archetype = Index(nativeList, i);
                    archetypes.Add(BuildInfo(archetype, includeComponents, maxComponents));
                }
                succeeded = true;
                message = $"Found {total} Entities archetype(s); returned {archetypes.Count}.";
                return archetypes;
            }
            catch (Exception ex)
            {
                message = "Entities archetype reflection failed: " + ex.Message;
                return archetypes;
            }
            finally
            {
                DisposeIfPossible(nativeList);
            }
        }

        private static void FillArchetypeList(object entityManager, object nativeList)
        {
            MethodInfo method = FindGetAllArchetypes(entityManager.GetType(), nativeList.GetType());
            if (method == null) throw new InvalidOperationException("GetAllArchetypes not found.");
            object[] args = { nativeList };
            method.Invoke(entityManager, args);
        }

        private static MethodInfo FindGetAllArchetypes(Type managerType, Type listType)
        {
            return managerType.GetMethods(BindingFlags.Public | BindingFlags.Instance)
                .FirstOrDefault(m => IsGetAllArchetypes(m, listType));
        }

        private static bool IsGetAllArchetypes(MethodInfo method, Type listType)
        {
            var parameters = method.GetParameters();
            return method.Name == "GetAllArchetypes"
                && parameters.Length == 1
                && parameters[0].ParameterType == listType;
        }

        private static object CreateArchetypeList()
        {
            Type archetypeType = RequireType(EntityArchetypeTypeName);
            Type nativeListType = RequireType(NativeListTypeName).MakeGenericType(archetypeType);
            foreach (ConstructorInfo ctor in nativeListType.GetConstructors())
            {
                object[] args = BuildConstructorArgs(ctor);
                if (args != null) return ctor.Invoke(args);
            }
            throw new InvalidOperationException("NativeList<EntityArchetype> constructor not found.");
        }

        private static object[] BuildConstructorArgs(ConstructorInfo ctor)
        {
            ParameterInfo[] parameters = ctor.GetParameters();
            if (parameters.Length == 2 && parameters[0].ParameterType == typeof(int))
            {
                object allocator = AllocatorValue(parameters[1].ParameterType);
                if (allocator != null) return new[] { (object)0, allocator };
            }
            if (parameters.Length == 1)
            {
                object allocator = AllocatorValue(parameters[0].ParameterType);
                if (allocator != null) return new[] { allocator };
            }
            return null;
        }

        private static EntitiesArchetypeInfo BuildInfo(
            object archetype,
            bool includeComponents,
            int maxComponents)
        {
            var info = new EntitiesArchetypeInfo
            {
                description = archetype?.ToString() ?? "",
                valid = Bool(GetValue(archetype, "Valid")),
                typesCount = Int(GetValue(archetype, "TypesCount"), -1),
                chunkCount = Int(GetValue(archetype, "ChunkCount"), -1),
                chunkCapacity = Int(GetValue(archetype, "ChunkCapacity"), -1),
                prefab = Bool(GetValue(archetype, "Prefab")),
                disabled = Bool(GetValue(archetype, "Disabled")),
                stableHash = Text(GetValue(archetype, "StableHash"))
            };
            if (includeComponents) AddComponents(archetype, info, maxComponents);
            return info;
        }

        private static void AddComponents(
            object archetype,
            EntitiesArchetypeInfo info,
            int maxComponents)
        {
            object componentArray = null;
            try
            {
                componentArray = GetComponentTypes(archetype);
                int total = Length(componentArray);
                info.componentCount = total;
                for (int i = 0; i < Math.Min(total, maxComponents); i++)
                    info.components.Add(BuildComponentInfo(Index(componentArray, i)));
            }
            catch (Exception ex)
            {
                info.message = "Component type reflection failed: " + ex.Message;
            }
            finally
            {
                DisposeIfPossible(componentArray);
            }
        }

        private static object GetComponentTypes(object archetype)
        {
            foreach (MethodInfo method in archetype.GetType().GetMethods())
            {
                if (method.Name != "GetComponentTypes") continue;
                var parameters = method.GetParameters();
                if (parameters.Length != 1) continue;
                object allocator = AllocatorValue(parameters[0].ParameterType);
                if (allocator != null) return method.Invoke(archetype, new[] { allocator });
            }
            throw new InvalidOperationException("EntityArchetype.GetComponentTypes not found.");
        }

        private static EntitiesComponentTypeInfo BuildComponentInfo(object component)
        {
            Type managedType = ManagedType(component);
            return new EntitiesComponentTypeInfo
            {
                name = managedType?.Name ?? Text(component),
                fullName = managedType?.FullName ?? "",
                typeIndex = Text(GetValue(component, "TypeIndex")),
                accessMode = Text(GetValue(component, "AccessModeType")),
                isBuffer = Bool(GetValue(component, "IsBuffer")),
                isCleanupComponent = Bool(GetValue(component, "IsCleanupComponent")),
                isSharedComponent = Bool(GetValue(component, "IsSharedComponent")),
                isManagedComponent = Bool(GetValue(component, "IsManagedComponent")),
                isZeroSized = Bool(GetValue(component, "IsZeroSized")),
                isChunkComponent = Bool(GetValue(component, "IsChunkComponent")),
                isEnableable = Bool(GetValue(component, "IsEnableable"))
            };
        }

        private static Type ManagedType(object component)
        {
            try
            {
                object value = component?.GetType().GetMethod("GetManagedType")?.Invoke(component, null);
                return value as Type;
            }
            catch
            {
                return null;
            }
        }

        private static int Length(object value)
        {
            return Int(GetValue(value, "Length") ?? GetValue(value, "Count"), 0);
        }

        private static object Index(object value, int index)
        {
            return value.GetType().GetProperty("Item")?.GetValue(value, new object[] { index });
        }

        private static object AllocatorValue(Type parameterType)
        {
            if (parameterType.IsEnum && parameterType.FullName == AllocatorTypeName)
                return Enum.Parse(parameterType, "Temp");

            Type managerType = FindType(AllocatorManagerTypeName);
            object handle = GetStaticValue(managerType, "Temp");
            return handle != null && parameterType.IsInstanceOfType(handle) ? handle : null;
        }

        private static Type RequireType(string fullName)
        {
            Type type = FindType(fullName);
            if (type != null) return type;
            throw new InvalidOperationException(fullName + " not found.");
        }

        private static Type FindType(string fullName)
        {
            foreach (Assembly assembly in AppDomain.CurrentDomain.GetAssemblies())
            {
                Type type = assembly.GetType(fullName);
                if (type != null) return type;
            }
            return null;
        }

        private static object GetStaticValue(Type type, string name)
        {
            if (type == null) return null;
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

        private static void DisposeIfPossible(object value)
        {
            value?.GetType().GetMethod("Dispose", Type.EmptyTypes)?.Invoke(value, null);
        }

        private static string Text(object value)
        {
            return value == null ? "" : value.ToString();
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
    public class EntitiesArchetypeInfo
    {
        public string description;
        public bool valid;
        public int typesCount;
        public int chunkCount;
        public int chunkCapacity;
        public bool prefab;
        public bool disabled;
        public string stableHash;
        public int componentCount;
        public string message;
        public List<EntitiesComponentTypeInfo> components = new List<EntitiesComponentTypeInfo>();
    }

    [Serializable]
    public class EntitiesComponentTypeInfo
    {
        public string name;
        public string fullName;
        public string typeIndex;
        public string accessMode;
        public bool isBuffer;
        public bool isCleanupComponent;
        public bool isSharedComponent;
        public bool isManagedComponent;
        public bool isZeroSized;
        public bool isChunkComponent;
        public bool isEnableable;
    }
}
