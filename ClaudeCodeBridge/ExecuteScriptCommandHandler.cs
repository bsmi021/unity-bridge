using System;
using System.Diagnostics;
using System.IO;
using System.Linq;
using System.Reflection;
using UnityEngine;

namespace BWS.Editor.ClaudeCodeBridge
{
    [Serializable]
    public class ExecuteScriptParams
    {
        public string expression;
        public bool returnValue = true;
    }

    [Serializable]
    public class ExecuteScriptResult
    {
        public string result;
        public string resultType;
        public bool resultSet;
        public long executionTimeMs;
        public string message;
    }

    public class ExecuteScriptCommandHandler : ICommandHandler
    {
        public string CommandType => "execute-script";

        public BridgeResponse Execute(BridgeCommand command)
        {
            var stopwatch = Stopwatch.StartNew();
            try
            {
                var parameters = JsonUtility.FromJson<ExecuteScriptParams>(
                    command.parametersJson ?? "{}") ?? new ExecuteScriptParams();
                if (string.IsNullOrWhiteSpace(parameters.expression))
                    return BridgeResponse.Error(command.commandId, command.commandType,
                        "expression parameter is required");

                BridgeLogger.LogInfo("Executing C# script through bridge.");
                var outcome = ExecuteCode(parameters.expression, parameters.returnValue);
                stopwatch.Stop();
                if (!outcome.Success)
                    return BridgeResponse.Error(command.commandId, command.commandType, outcome.Message);

                outcome.Result.executionTimeMs = stopwatch.ElapsedMilliseconds;
                return BridgeResponse.Success(command.commandId, command.commandType,
                    JsonUtility.ToJson(outcome.Result));
            }
            catch (Exception ex)
            {
                stopwatch.Stop();
                BridgeLogger.LogError($"Execute-script failed after {stopwatch.ElapsedMilliseconds}ms: {ex}");
                return BridgeResponse.Error(command.commandId, command.commandType, ex.Message);
            }
        }

        private static ScriptOutcome ExecuteCode(string code, bool returnValue)
        {
            var outcome = ExecuteWithFreshEvaluator(code, returnValue);
            if (outcome.Success || !returnValue || !LooksLikeStatements(code))
                return outcome;
            return ExecuteWithFreshEvaluator(code, false);
        }

        private static ScriptOutcome ExecuteWithFreshEvaluator(string code, bool returnValue)
        {
            using (var writer = new StringWriter())
            {
                var evaluator = CreateEvaluator(writer);
                return returnValue ? Evaluate(evaluator, code, writer) : Run(evaluator, code, writer);
            }
        }

        private static object CreateEvaluator(StringWriter writer)
        {
            var settingsType = GetMonoCSharpType("Mono.CSharp.CompilerSettings");
            var printerType = GetMonoCSharpType("Mono.CSharp.ConsoleReportPrinter");
            var contextType = GetMonoCSharpType("Mono.CSharp.CompilerContext");
            var evaluatorType = GetMonoCSharpType("Mono.CSharp.Evaluator");
            var settings = Activator.CreateInstance(settingsType);
            var printer = Activator.CreateInstance(printerType, writer);
            var context = Activator.CreateInstance(contextType, settings, printer);
            var evaluator = Activator.CreateInstance(evaluatorType, context);
            ReferenceLoadedAssemblies(evaluator);
            ImportUnityNamespaces(evaluator);
            return evaluator;
        }

        private static ScriptOutcome Evaluate(object evaluator, string code, StringWriter writer)
        {
            var method = evaluator.GetType().GetMethod("Evaluate", new[]
            {
                typeof(string),
                typeof(object).MakeByRefType(),
                typeof(bool).MakeByRefType()
            });
            var args = new object[] { code, null, false };
            var error = InvokeEvaluator(method, evaluator, args) as string;
            if (!string.IsNullOrEmpty(error))
                return ScriptOutcome.Failure(error);
            var result = args[1];
            var resultSet = args[2] is bool set && set;
            return ScriptOutcome.Successful(result, resultSet, ReportText(writer));
        }

        private static ScriptOutcome Run(object evaluator, string code, StringWriter writer)
        {
            var method = evaluator.GetType().GetMethod("Run", new[] { typeof(string) });
            var success = InvokeEvaluator(method, evaluator, new object[] { code }) is true;
            if (!success)
                return ScriptOutcome.Failure(ReportText(writer, "Script execution failed."));
            return ScriptOutcome.Successful(null, false, ReportText(writer, "Script executed."));
        }

        private static object InvokeEvaluator(MethodInfo method, object evaluator, object[] args)
        {
            try
            {
                return method.Invoke(evaluator, args);
            }
            catch (TargetInvocationException ex)
            {
                throw ex.InnerException ?? ex;
            }
        }

        private static void ReferenceLoadedAssemblies(object evaluator)
        {
            var method = evaluator.GetType().GetMethod("ReferenceAssembly", new[] { typeof(Assembly) });
            foreach (var assembly in AppDomain.CurrentDomain.GetAssemblies().Where(CanReference))
            {
                try { method.Invoke(evaluator, new object[] { assembly }); }
                catch { /* Best effort: dynamic/editor-only assemblies may reject references. */ }
            }
        }

        private static void ImportUnityNamespaces(object evaluator)
        {
            var run = evaluator.GetType().GetMethod("Run", new[] { typeof(string) });
            foreach (var ns in new[] { "System", "System.Linq", "UnityEngine", "UnityEditor" })
            {
                try { run.Invoke(evaluator, new object[] { $"using {ns};" }); }
                catch { /* Missing namespaces are surfaced when user code requires them. */ }
            }
        }

        private static Type GetMonoCSharpType(string typeName)
        {
            var type = AppDomain.CurrentDomain.GetAssemblies()
                .Select(assembly => assembly.GetType(typeName))
                .FirstOrDefault(found => found != null);
            if (type != null) return type;
            var monoCSharp = Assembly.Load("Mono.CSharp");
            return monoCSharp.GetType(typeName, true);
        }

        private static bool CanReference(Assembly assembly)
        {
            try
            {
                return !assembly.IsDynamic && !string.IsNullOrEmpty(assembly.Location);
            }
            catch
            {
                return false;
            }
        }

        private static bool LooksLikeStatements(string code)
        {
            return code.Contains(";") || code.Contains("\n") || code.Contains("\r");
        }

        private static string ReportText(StringWriter writer, string fallback = "")
        {
            var text = writer.ToString().Trim();
            return string.IsNullOrEmpty(text) ? fallback : text;
        }

        private class ScriptOutcome
        {
            public bool Success { get; private set; }
            public string Message { get; private set; }
            public ExecuteScriptResult Result { get; private set; }

            public static ScriptOutcome Failure(string message)
            {
                return new ScriptOutcome { Success = false, Message = message };
            }

            public static ScriptOutcome Successful(object value, bool resultSet, string message)
            {
                return new ScriptOutcome
                {
                    Success = true,
                    Result = new ExecuteScriptResult
                    {
                        result = value?.ToString() ?? "",
                        resultType = value?.GetType().FullName ?? "",
                        resultSet = resultSet,
                        message = message,
                    }
                };
            }
        }
    }
}
