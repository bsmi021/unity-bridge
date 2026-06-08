using System;
using System.Collections;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Reflection;
using UnityEngine;

namespace BWS.Editor.ClaudeCodeBridge
{
    /// <summary>
    /// Optional Project Auditor integration via reflection so projects without
    /// com.unity.project-auditor still compile.
    /// </summary>
    public class ProjectAuditorCommandHandler : ICommandHandler
    {
        private const string PackageName = "com.unity.project-auditor";
        private const int DefaultMaxIssues = 50;

        public string CommandType => "project-auditor";

        public BridgeResponse Execute(BridgeCommand command)
        {
            string operation = "unknown";
            try
            {
                var p = JsonUtility.FromJson<ProjectAuditorParams>(
                    command.parametersJson ?? "{}") ?? new ProjectAuditorParams();
                operation = p.operation?.ToLowerInvariant() ?? "availability";

                switch (operation)
                {
                    case "availability":
                        return Reply(command, AvailabilityResult(operation));
                    case "run":
                        return Reply(command, RunAudit(operation, p));
                    case "load":
                        return Reply(command, LoadReport(operation, p));
                    default:
                        return Reply(command, Fail(operation, $"Unknown operation: {p.operation}. "
                            + "Supported: availability, run, load"));
                }
            }
            catch (Exception ex)
            {
                BridgeLogger.LogError($"Project Auditor error: {ex}");
                var result = Fail(operation, ex.ToString());
                return Reply(command, result);
            }
        }

        private static BridgeResponse Reply(BridgeCommand command, ProjectAuditorResult result)
        {
            string json = JsonUtility.ToJson(result);
            if (result.success) return BridgeResponse.Success(command.commandId, command.commandType, json);
            return new BridgeResponse
            {
                commandId = command.commandId,
                commandType = command.commandType,
                status = "error",
                timestamp = DateTime.UtcNow.ToString("o"),
                dataJson = json,
                errorMessage = result.message,
            };
        }

        private static ProjectAuditorResult AvailabilityResult(string operation)
        {
            var api = FindApi();
            bool apiAvailable = api.IsUsable;
            return new ProjectAuditorResult
            {
                success = true,
                operation = operation,
                packageAvailable = IsPackageAvailable() || apiAvailable,
                apiAvailable = apiAvailable,
                message = apiAvailable ? "Project Auditor API is available."
                    : "Project Auditor package/API is not available.",
            };
        }

        private static ProjectAuditorResult RunAudit(string operation, ProjectAuditorParams p)
        {
            var api = FindApi();
            if (!api.IsUsable) return Unavailable(operation);

            object analysisParams = CreateAnalysisParams(api, p);
            object report = InvokeAudit(api, analysisParams);
            if (report == null) return Fail(operation, "ProjectAuditor.Audit returned no report.");

            string reportPath = SaveReport(report, p.outputPath);
            var result = SummarizeReport(operation, api, report, p.maxIssues);
            result.reportPath = reportPath;
            result.message = "Project Auditor audit completed.";
            return result;
        }

        private static ProjectAuditorResult LoadReport(string operation, ProjectAuditorParams p)
        {
            var api = FindApi();
            if (!api.IsUsable) return Unavailable(operation);
            if (string.IsNullOrEmpty(p.outputPath))
                return Fail(operation, "outputPath is required for load operation.");
            if (!File.Exists(p.outputPath))
                return Fail(operation, $"Project Auditor report not found: {p.outputPath}");

            object report = InvokeLoad(api, p.outputPath);
            if (report == null) return Fail(operation, $"Project Auditor report not found: {p.outputPath}");

            var result = SummarizeReport(operation, api, report, p.maxIssues);
            result.reportPath = p.outputPath;
            result.message = "Project Auditor report loaded.";
            return result;
        }

        private static ProjectAuditorResult SummarizeReport(
            string operation, ProjectAuditorApi api, object report, int maxIssues)
        {
            int max = maxIssues > 0 ? maxIssues : DefaultMaxIssues;
            var issues = new List<ProjectAuditorIssue>();
            foreach (object issue in GetIssues(report))
            {
                if (issue == null) continue;
                if (issues.Count >= max) break;
                issues.Add(ReadIssue(issue));
            }

            return new ProjectAuditorResult
            {
                success = true,
                operation = operation,
                packageAvailable = IsPackageAvailable() || api.IsUsable,
                apiAvailable = api.IsUsable,
                totalIssues = GetInt(report, "NumTotalIssues"),
                issueCount = issues.Count,
                issues = issues,
            };
        }

        private static object CreateAnalysisParams(ProjectAuditorApi api, ProjectAuditorParams p)
        {
            object analysisParams = CreateAnalysisParamsInstance(api.analysisParamsType);
            TrySetListMember(analysisParams, "AssemblyNames", p.assemblyNames);
            TrySetListMember(analysisParams, "Categories", p.categories);
            TrySetSingleMember(analysisParams, "Platform", p.platform);
            return analysisParams;
        }

        private static object CreateAnalysisParamsInstance(Type analysisParamsType)
        {
            var ctor = analysisParamsType.GetConstructor(new[] { typeof(bool) });
            if (ctor != null) return ctor.Invoke(new object[] { true });
            return Activator.CreateInstance(analysisParamsType);
        }

        private static object InvokeAudit(ProjectAuditorApi api, object analysisParams)
        {
            var methods = api.projectAuditorType.GetMethods(BindingFlags.Public | BindingFlags.Static
                | BindingFlags.Instance);
            var audit = methods.FirstOrDefault(m => IsAuditMethod(m, api.analysisParamsType));
            if (audit == null) return null;

            object target = audit.IsStatic ? null : Activator.CreateInstance(api.projectAuditorType);
            object[] args = BuildArguments(audit, analysisParams);
            return audit.Invoke(target, args);
        }

        private static bool IsAuditMethod(MethodInfo method, Type analysisParamsType)
        {
            var ps = method.GetParameters();
            return method.Name == "Audit" && ps.Length > 0
                && ps[0].ParameterType.IsAssignableFrom(analysisParamsType);
        }

        private static object[] BuildArguments(MethodInfo method, object firstArg)
        {
            var ps = method.GetParameters();
            var args = new object[ps.Length];
            args[0] = firstArg;
            for (int i = 1; i < ps.Length; i++)
                args[i] = ps[i].HasDefaultValue ? ps[i].DefaultValue : DefaultValue(ps[i].ParameterType);
            return args;
        }

        private static object InvokeLoad(ProjectAuditorApi api, string path)
        {
            var load = api.reportType.GetMethods(BindingFlags.Public | BindingFlags.Static)
                .FirstOrDefault(m => m.Name == "Load" && HasSingleStringParameter(m));
            return load?.Invoke(null, new object[] { path });
        }

        private static string SaveReport(object report, string outputPath)
        {
            if (string.IsNullOrEmpty(outputPath)) return null;
            string directory = Path.GetDirectoryName(outputPath);
            if (!string.IsNullOrEmpty(directory)) Directory.CreateDirectory(directory);
            var save = report.GetType().GetMethods(BindingFlags.Public | BindingFlags.Instance)
                .FirstOrDefault(m => m.Name == "Save" && HasSingleStringParameter(m));
            save?.Invoke(report, new object[] { outputPath });
            return outputPath;
        }

        private static IEnumerable<object> GetIssues(object report)
        {
            var getAllIssues = report.GetType().GetMethod(
                "GetAllIssues", BindingFlags.Public | BindingFlags.Instance);
            object items = getAllIssues?.Invoke(report, null);
            if (items is IEnumerable enumerable)
            {
                foreach (object item in enumerable) yield return item;
            }
        }

        private static ProjectAuditorIssue ReadIssue(object issue)
        {
            return new ProjectAuditorIssue
            {
                id = GetString(issue, "Id"),
                category = GetString(issue, "Category"),
                severity = GetString(issue, "Severity"),
                description = GetString(issue, "Description"),
                relativePath = GetString(issue, "RelativePath"),
                filename = GetString(issue, "Filename"),
                line = GetInt(issue, "Line"),
                isIssue = InvokeBool(issue, "IsIssue"),
                isMajorOrCritical = InvokeBool(issue, "IsMajorOrCritical"),
            };
        }

        private static void TrySetListMember(object target, string name, List<string> values)
        {
            if (target == null || values == null || values.Count == 0) return;
            var member = FindMember(target.GetType(), name);
            if (member == null) return;
            object converted = ConvertList(MemberType(member), values);
            if (converted != null) SetMember(target, member, converted);
        }

        private static void TrySetSingleMember(object target, string name, string value)
        {
            if (target == null || string.IsNullOrEmpty(value)) return;
            var member = FindMember(target.GetType(), name);
            if (member == null) return;
            object converted = ConvertSingle(value, MemberType(member));
            if (converted != null) SetMember(target, member, converted);
        }

        private static object ConvertList(Type targetType, List<string> values)
        {
            Type elementType = ElementType(targetType) ?? typeof(string);
            var converted = values.Select(v => ConvertSingle(v, elementType))
                .Where(v => v != null)
                .ToList();
            if (converted.Count == 0) return null;
            if (targetType.IsArray) return ToArray(elementType, converted);
            if (targetType.IsAssignableFrom(typeof(List<string>)) && elementType == typeof(string))
                return values;
            return ToGenericList(elementType, converted);
        }

        private static object ConvertSingle(string value, Type targetType)
        {
            try
            {
                if (targetType == typeof(string)) return value;
                if (targetType.IsEnum) return Enum.Parse(targetType, value, true);
                var parse = targetType.GetMethod("Parse", BindingFlags.Public | BindingFlags.Static,
                    null, new[] { typeof(string) }, null);
                if (parse != null) return parse.Invoke(null, new object[] { value });
                return Convert.ChangeType(value, targetType);
            }
            catch
            {
                return null;
            }
        }

        private static Array ToArray(Type elementType, List<object> values)
        {
            Array array = Array.CreateInstance(elementType, values.Count);
            for (int i = 0; i < values.Count; i++) array.SetValue(values[i], i);
            return array;
        }

        private static object ToGenericList(Type elementType, List<object> values)
        {
            Type listType = typeof(List<>).MakeGenericType(elementType);
            var list = (IList)Activator.CreateInstance(listType);
            foreach (object value in values) list.Add(value);
            return list;
        }

        private static Type ElementType(Type targetType)
        {
            if (targetType.IsArray) return targetType.GetElementType();
            if (targetType.IsGenericType) return targetType.GetGenericArguments()[0];
            return null;
        }

        private static ProjectAuditorApi FindApi()
        {
            return new ProjectAuditorApi
            {
                projectAuditorType = FindType("Unity.ProjectAuditor.Editor.ProjectAuditor"),
                analysisParamsType = FindType("Unity.ProjectAuditor.Editor.AnalysisParams"),
                reportType = FindType("Unity.ProjectAuditor.Editor.Report"),
            };
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

        private static ProjectAuditorResult Unavailable(string operation)
        {
            return new ProjectAuditorResult
            {
                success = false,
                operation = operation,
                packageAvailable = IsPackageAvailable(),
                apiAvailable = false,
                message = "Project Auditor package/API is not available. "
                    + "Install com.unity.project-auditor to use this operation.",
            };
        }

        private static ProjectAuditorResult Fail(string operation, string message)
        {
            var api = FindApi();
            return new ProjectAuditorResult
            {
                success = false,
                operation = operation,
                packageAvailable = IsPackageAvailable() || api.IsUsable,
                apiAvailable = api.IsUsable,
                message = message,
            };
        }

        private static MemberInfo FindMember(Type type, string name)
        {
            const BindingFlags flags = BindingFlags.Public | BindingFlags.Instance;
            return (MemberInfo)type.GetProperty(name, flags) ?? type.GetField(name, flags);
        }

        private static Type MemberType(MemberInfo member)
        {
            if (member is PropertyInfo p) return p.PropertyType;
            return ((FieldInfo)member).FieldType;
        }

        private static void SetMember(object target, MemberInfo member, object value)
        {
            if (member is PropertyInfo p && p.CanWrite) p.SetValue(target, value);
            else if (member is FieldInfo f) f.SetValue(target, value);
        }

        private static string GetString(object obj, string name)
        {
            object value = GetValue(obj, name);
            return value?.ToString();
        }

        private static int GetInt(object obj, string name)
        {
            object value = GetValue(obj, name);
            if (value is int i) return i;
            return value != null && int.TryParse(value.ToString(), out int parsed) ? parsed : 0;
        }

        private static object GetValue(object obj, string name)
        {
            if (obj == null) return null;
            var member = FindMember(obj.GetType(), name);
            if (member is PropertyInfo p) return p.GetValue(obj);
            if (member is FieldInfo f) return f.GetValue(obj);
            return null;
        }

        private static bool InvokeBool(object obj, string methodName)
        {
            var method = obj?.GetType().GetMethod(methodName, BindingFlags.Public | BindingFlags.Instance);
            object value = method?.Invoke(obj, null);
            return value is bool b && b;
        }

        private static bool HasSingleStringParameter(MethodInfo method)
        {
            var ps = method.GetParameters();
            return ps.Length == 1 && ps[0].ParameterType == typeof(string);
        }

        private static object DefaultValue(Type type)
        {
            return type.IsValueType ? Activator.CreateInstance(type) : null;
        }

        private class ProjectAuditorApi
        {
            public Type projectAuditorType;
            public Type analysisParamsType;
            public Type reportType;
            public bool IsUsable => projectAuditorType != null
                && analysisParamsType != null && reportType != null;
        }
    }

    [Serializable]
    public class ProjectAuditorParams
    {
        public string operation;
        public string outputPath;
        public int maxIssues;
        public List<string> categories = new List<string>();
        public List<string> assemblyNames = new List<string>();
        public string platform;
    }

    [Serializable]
    public class ProjectAuditorResult
    {
        public bool success;
        public string operation;
        public bool packageAvailable;
        public bool apiAvailable;
        public string reportPath;
        public int totalIssues;
        public int issueCount;
        public List<ProjectAuditorIssue> issues = new List<ProjectAuditorIssue>();
        public string message;
    }

    [Serializable]
    public class ProjectAuditorIssue
    {
        public string id;
        public string category;
        public string severity;
        public string description;
        public string relativePath;
        public string filename;
        public int line;
        public bool isIssue;
        public bool isMajorOrCritical;
    }
}
