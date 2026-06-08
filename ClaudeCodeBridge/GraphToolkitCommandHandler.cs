using System;
using System.Collections;
using System.Collections.Generic;
using System.Reflection;
using UnityEditor;
using UnityEngine;

namespace BWS.Editor.ClaudeCodeBridge
{
    public class GraphToolkitCommandHandler : ICommandHandler
    {
        private const string FactoryTypeName = "Unity.GraphToolkit.Editor.GraphObjectFactory";
        public string CommandType => "graph-toolkit";

        public BridgeResponse Execute(BridgeCommand command)
        {
            try
            {
                var p = JsonUtility.FromJson<GraphToolkitParams>(
                    command.parametersJson ?? "{}") ?? new GraphToolkitParams();
                var operation = string.IsNullOrEmpty(p.operation)
                    ? "availability"
                    : p.operation.ToLowerInvariant();

                switch (operation)
                {
                    case "availability":
                        return Success(command, BuildAvailability(operation));
                    case "list-assets":
                        return Success(command, ListAssets(operation));
                    case "inspect":
                    case "export":
                        return Inspect(command, p, operation);
                    default:
                        return Error(command, operation,
                            "Unknown operation. Supported: availability, list-assets, inspect, export");
                }
            }
            catch (Exception ex)
            {
                BridgeLogger.LogError($"Graph Toolkit error: {ex}");
                return Error(command, "graph-toolkit", ex.ToString());
            }
        }

        private static GraphToolkitResult BuildAvailability(string operation)
        {
            var assembly = FindType(FactoryTypeName)?.Assembly;
            var result = NewResult(operation);
            result.moduleAvailable = assembly != null;
            result.moduleVersion = assembly != null ? assembly.GetName().Version.ToString() : "";
            result.extensions = GetExtensions();
            result.message = result.moduleAvailable
                ? "Graph Toolkit module is available."
                : "Graph Toolkit module is not available.";
            return result;
        }

        private static GraphToolkitResult ListAssets(string operation)
        {
            var result = BuildAvailability(operation);
            foreach (var path in FindGraphAssetPaths(result.extensions))
                result.assets.Add(BuildAssetInfo(path));

            result.message = $"Found {result.assets.Count} Graph Toolkit asset(s).";
            return result;
        }

        private static BridgeResponse Inspect(
            BridgeCommand command, GraphToolkitParams p, string operation)
        {
            if (string.IsNullOrEmpty(p.assetPath))
                return Error(command, operation, "assetPath is required.");

            var graphObject = LoadGraphObject(p.assetPath);
            if (graphObject == null)
                return Error(command, operation, $"Graph asset not found: {p.assetPath}");

            var result = BuildAvailability(operation);
            result.graph = BuildGraph(graphObject, p, operation == "export");
            result.message = $"Inspected Graph Toolkit asset: {p.assetPath}";
            return Success(command, result);
        }

        private static GraphToolkitGraphInfo BuildGraph(
            UnityEngine.Object graphObject, GraphToolkitParams p, bool forceDetails)
        {
            int max = p.maxElements <= 0 ? 1000 : p.maxElements;
            object graphModel = GetProperty(graphObject, "GraphModel") ?? graphObject;
            var info = NewGraphInfo(graphObject, graphModel, p.assetPath);
            var nodes = ToList(GetProperty(graphModel, "NodeModels"), max);
            var wires = ToList(GetProperty(graphModel, "WireModels"), max);
            var variables = ToList(GetProperty(graphModel, "VariableDeclarations"), max);
            var notes = ToList(GetProperty(graphModel, "StickyNoteModels"), max);
            var mats = ToList(GetProperty(graphModel, "PlacematModels"), max);
            SetCounts(info, nodes, wires, variables, notes, mats);

            if (forceDetails || p.includePorts)
                foreach (var node in nodes) info.nodes.Add(BuildNode(node, p.includePorts, max));
            if (forceDetails)
                foreach (var wire in wires) info.wires.Add(BuildWire(wire));
            if (forceDetails || p.includeVariables)
                foreach (var v in variables) info.variables.Add(BuildVariable(v));
            if (forceDetails || p.includeAnnotations)
                AddAnnotations(info, notes, mats);
            return info;
        }

        private static GraphToolkitGraphInfo NewGraphInfo(
            UnityEngine.Object graphObject, object graphModel, string assetPath)
        {
            return new GraphToolkitGraphInfo
            {
                assetPath = assetPath,
                name = graphObject.name,
                typeName = graphObject.GetType().FullName,
                guid = Text(GetProperty(graphModel, "Guid"), AssetDatabase.AssetPathToGUID(assetPath))
            };
        }

        private static void SetCounts(
            GraphToolkitGraphInfo info, List<object> nodes, List<object> wires,
            List<object> variables, List<object> notes, List<object> mats)
        {
            info.nodeCount = nodes.Count;
            info.wireCount = wires.Count;
            info.variableCount = variables.Count;
            info.stickyNoteCount = notes.Count;
            info.placematCount = mats.Count;
        }

        private static GraphToolkitNodeInfo BuildNode(object node, bool includePorts, int max)
        {
            var info = new GraphToolkitNodeInfo
            {
                guid = Text(GetProperty(node, "Guid")),
                title = Text(GetProperty(node, "Title")),
                subtitle = Text(GetProperty(node, "Subtitle")),
                tooltip = Text(GetProperty(node, "Tooltip")),
                typeName = node.GetType().FullName
            };
            SetVector2(GetProperty(node, "Position"), out info.x, out info.y);
            if (includePorts)
                AddPorts(info, node, max);
            return info;
        }

        private static void AddPorts(GraphToolkitNodeInfo info, object node, int max)
        {
            foreach (var port in ToList(GetProperty(node, "InputPorts"), max))
                info.ports.Add(BuildPort(port));
            foreach (var port in ToList(GetProperty(node, "OutputPorts"), max))
                info.ports.Add(BuildPort(port));
        }

        private static GraphToolkitPortInfo BuildPort(object port)
        {
            return new GraphToolkitPortInfo
            {
                guid = Text(GetProperty(port, "Guid")),
                title = Text(GetProperty(port, "Title")),
                uniqueName = Text(GetProperty(port, "UniqueName")),
                portId = Text(GetProperty(port, "PortId")),
                direction = Text(GetProperty(port, "Direction")),
                orientation = Text(GetProperty(port, "Orientation")),
                capacity = Text(GetProperty(port, "Capacity")),
                dataType = Text(GetProperty(port, "PortDataType"))
            };
        }

        private static GraphToolkitWireInfo BuildWire(object wire)
        {
            return new GraphToolkitWireInfo
            {
                guid = Text(GetProperty(wire, "Guid")),
                fromNodeGuid = Text(GetProperty(wire, "FromNodeGuid")),
                toNodeGuid = Text(GetProperty(wire, "ToNodeGuid")),
                fromPortId = Text(GetProperty(wire, "FromPortId")),
                toPortId = Text(GetProperty(wire, "ToPortId")),
                bubbleText = Text(GetProperty(wire, "WireBubbleText"))
            };
        }

        private static GraphToolkitVariableInfo BuildVariable(object variable)
        {
            return new GraphToolkitVariableInfo
            {
                guid = Text(GetProperty(variable, "Guid")),
                title = Text(GetProperty(variable, "Title")),
                uniqueId = Text(GetProperty(variable, "UniqueId")),
                dataType = Text(GetProperty(variable, "DataType")),
                scope = Text(GetProperty(variable, "Scope")),
                flags = Text(GetProperty(variable, "VariableFlags")),
                isInput = Bool(GetProperty(variable, "IsInput")),
                isOutput = Bool(GetProperty(variable, "IsOutput"))
            };
        }

        private static void AddAnnotations(
            GraphToolkitGraphInfo info, List<object> notes, List<object> mats)
        {
            foreach (var note in notes)
                info.stickyNotes.Add(BuildAnnotation(note, "Contents"));
            foreach (var mat in mats)
                info.placemats.Add(BuildAnnotation(mat, "Comment"));
        }

        private static GraphToolkitAnnotationInfo BuildAnnotation(object model, string bodyProperty)
        {
            var info = new GraphToolkitAnnotationInfo
            {
                guid = Text(GetProperty(model, "Guid")),
                title = Text(GetProperty(model, "Title")),
                body = Text(GetProperty(model, bodyProperty)),
                typeName = model.GetType().FullName
            };
            SetRect(GetProperty(model, "PositionAndSize"), info);
            return info;
        }

        private static UnityEngine.Object LoadGraphObject(string path)
        {
            var factory = FindType(FactoryTypeName);
            object graphType = GetGraphTypeForPath(factory, path);
            var method = factory?.GetMethod("LoadGraphObjectAtPath",
                BindingFlags.Public | BindingFlags.Static,
                null, new[] { typeof(string), typeof(Type), typeof(bool) }, null);
            var loaded = graphType != null && method != null
                ? method.Invoke(null, new[] { path, graphType, false }) as UnityEngine.Object
                : null;
            return loaded != null ? loaded : AssetDatabase.LoadMainAssetAtPath(path);
        }

        private static object GetGraphTypeForPath(Type factory, string path)
        {
            if (factory == null)
                return null;
            var method = factory.GetMethod("GetGraphObjectTypeForExtension",
                BindingFlags.Public | BindingFlags.Static);
            string ext = System.IO.Path.GetExtension(path);
            return method?.Invoke(null, new object[] { ext });
        }

        private static List<string> GetExtensions()
        {
            var values = InvokeFactory("GetExtensions", null) as IEnumerable;
            var result = new List<string>();
            if (values == null) return result;
            foreach (var value in values)
                if (value != null) result.Add(value.ToString());
            return result;
        }

        private static List<string> FindGraphAssetPaths(List<string> extensions)
        {
            var paths = new List<string>();
            foreach (var path in AssetDatabase.GetAllAssetPaths())
            {
                if (MatchesExtension(path, extensions) || LooksLikeGraphAsset(path))
                    paths.Add(path);
            }
            paths.Sort(StringComparer.OrdinalIgnoreCase);
            return paths;
        }

        private static bool LooksLikeGraphAsset(string path)
        {
            var asset = AssetDatabase.LoadMainAssetAtPath(path);
            return asset != null && asset.GetType().FullName.ToLowerInvariant().Contains("graph");
        }

        private static bool MatchesExtension(string path, List<string> extensions)
        {
            foreach (var ext in extensions)
                if (!string.IsNullOrEmpty(ext)
                    && path.EndsWith(ext, StringComparison.OrdinalIgnoreCase))
                    return true;
            return false;
        }

        private static GraphToolkitAssetInfo BuildAssetInfo(string path)
        {
            var asset = AssetDatabase.LoadMainAssetAtPath(path);
            return new GraphToolkitAssetInfo
            {
                assetPath = path,
                name = asset != null ? asset.name : System.IO.Path.GetFileNameWithoutExtension(path),
                extension = System.IO.Path.GetExtension(path),
                typeName = asset != null ? asset.GetType().FullName : ""
            };
        }

        private static object InvokeFactory(string methodName, object[] args)
        {
            var type = FindType(FactoryTypeName);
            return type?.GetMethod(methodName, BindingFlags.Public | BindingFlags.Static)
                ?.Invoke(null, args);
        }

        private static Type FindType(string fullName)
        {
            foreach (var assembly in AppDomain.CurrentDomain.GetAssemblies())
                if (assembly.GetType(fullName) != null) return assembly.GetType(fullName);
            try { return Assembly.Load("UnityEditor.GraphToolkitModule").GetType(fullName); }
            catch { return null; }
        }

        private static object GetProperty(object target, string name)
        {
            if (target == null) return null;
            var flags = BindingFlags.Public | BindingFlags.NonPublic | BindingFlags.Instance;
            try { return target.GetType().GetProperty(name, flags)?.GetValue(target); }
            catch { return null; }
        }

        private static List<object> ToList(object value, int max)
        {
            var result = new List<object>();
            if (!(value is IEnumerable enumerable) || value is string)
                return result;
            foreach (var item in enumerable)
            {
                if (item != null) result.Add(item);
                if (result.Count >= max) break;
            }
            return result;
        }

        private static void SetVector2(object value, out float x, out float y)
        {
            x = 0;
            y = 0;
            if (value is Vector2 vector)
            {
                x = vector.x;
                y = vector.y;
            }
        }

        private static void SetRect(object value, GraphToolkitAnnotationInfo info)
        {
            if (!(value is Rect rect)) return;
            info.x = rect.x;
            info.y = rect.y;
            info.width = rect.width;
            info.height = rect.height;
        }

        private static GraphToolkitResult NewResult(string operation)
        {
            return new GraphToolkitResult { success = true, operation = operation };
        }

        private static string Text(object value, string fallback = "")
        {
            return value != null ? value.ToString() : fallback;
        }

        private static bool Bool(object value)
        {
            return value is bool b && b;
        }

        private static BridgeResponse Success(BridgeCommand command, GraphToolkitResult result)
        {
            return BridgeResponse.Success(command.commandId, command.commandType,
                JsonUtility.ToJson(result));
        }

        private static BridgeResponse Error(BridgeCommand command, string operation, string message)
        {
            var result = new GraphToolkitResult
            {
                success = false,
                operation = operation,
                message = message
            };
            return new BridgeResponse
            {
                commandId = command.commandId,
                commandType = command.commandType,
                status = "error",
                timestamp = DateTime.UtcNow.ToString("o"),
                dataJson = JsonUtility.ToJson(result),
                errorMessage = message
            };
        }
    }

    [Serializable]
    public class GraphToolkitParams
    {
        public string operation;
        public string assetPath;
        public bool includePorts;
        public bool includeVariables;
        public bool includeAnnotations;
        public int maxElements;
    }

    [Serializable]
    public class GraphToolkitResult
    {
        public bool success;
        public string operation;
        public string message;
        public bool moduleAvailable;
        public string moduleVersion;
        public List<string> extensions = new List<string>();
        public List<GraphToolkitAssetInfo> assets = new List<GraphToolkitAssetInfo>();
        public GraphToolkitGraphInfo graph;
    }

    [Serializable]
    public class GraphToolkitAssetInfo
    {
        public string assetPath;
        public string name;
        public string extension;
        public string typeName;
    }

    [Serializable]
    public class GraphToolkitGraphInfo
    {
        public string assetPath;
        public string name;
        public string typeName;
        public string guid;
        public int nodeCount;
        public int wireCount;
        public int variableCount;
        public int stickyNoteCount;
        public int placematCount;
        public List<GraphToolkitNodeInfo> nodes = new List<GraphToolkitNodeInfo>();
        public List<GraphToolkitWireInfo> wires = new List<GraphToolkitWireInfo>();
        public List<GraphToolkitVariableInfo> variables = new List<GraphToolkitVariableInfo>();
        public List<GraphToolkitAnnotationInfo> stickyNotes =
            new List<GraphToolkitAnnotationInfo>();
        public List<GraphToolkitAnnotationInfo> placemats =
            new List<GraphToolkitAnnotationInfo>();
    }

    [Serializable]
    public class GraphToolkitNodeInfo
    {
        public string guid;
        public string title;
        public string subtitle;
        public string tooltip;
        public string typeName;
        public float x;
        public float y;
        public List<GraphToolkitPortInfo> ports = new List<GraphToolkitPortInfo>();
    }

    [Serializable]
    public class GraphToolkitPortInfo
    {
        public string guid;
        public string title;
        public string uniqueName;
        public string portId;
        public string direction;
        public string orientation;
        public string capacity;
        public string dataType;
    }

    [Serializable]
    public class GraphToolkitWireInfo
    {
        public string guid;
        public string fromNodeGuid;
        public string toNodeGuid;
        public string fromPortId;
        public string toPortId;
        public string bubbleText;
    }

    [Serializable]
    public class GraphToolkitVariableInfo
    {
        public string guid;
        public string title;
        public string uniqueId;
        public string dataType;
        public string scope;
        public string flags;
        public bool isInput;
        public bool isOutput;
    }

    [Serializable]
    public class GraphToolkitAnnotationInfo
    {
        public string guid;
        public string title;
        public string body;
        public string typeName;
        public float x;
        public float y;
        public float width;
        public float height;
    }
}
