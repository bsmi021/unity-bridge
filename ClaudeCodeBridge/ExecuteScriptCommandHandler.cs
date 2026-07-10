using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.IO;
using System.Linq;
using System.Reflection;
using UnityEditor;
using UnityEngine;

namespace BWS.Editor.ClaudeCodeBridge
{
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
                if (!ValidateRequest(parameters, out var message))
                    return BridgeResponse.Error(command.commandId, command.commandType, message);
                if (ExecuteScriptJobCoordinator.HasActiveJob)
                {
                    return BridgeResponse.Error(
                        command.commandId,
                        command.commandType,
                        "A cooperative execute job currently owns the generic execution host.");
                }

                BridgeLogger.LogInfo(
                    $"Executing governed C# script with {parameters.manifest.intent} intent.");
                return ExecuteValidated(command, parameters, stopwatch);
            }
            catch (Exception ex)
            {
                stopwatch.Stop();
                BridgeLogger.LogError(
                    $"Execute-script failed after {stopwatch.ElapsedMilliseconds}ms: {ex}");
                return BridgeResponse.Error(command.commandId, command.commandType, ex.Message);
            }
        }

        internal static bool ValidateRequest(
            ExecuteScriptParams parameters, out string message)
        {
            if (string.IsNullOrWhiteSpace(parameters.expression))
            {
                message = "expression parameter is required";
                return false;
            }
            if (!ExecuteScriptManifestValidator.Validate(parameters.manifest, out message))
                return false;
            return ExecuteScriptReflectionPolicy.Validate(
                parameters.expression,
                parameters.manifest.allowInternalReflection,
                out message);
        }

        private static BridgeResponse ExecuteValidated(
            BridgeCommand command,
            ExecuteScriptParams parameters,
            Stopwatch stopwatch)
        {
            using (var logs = new ExecuteScriptLogCapture())
            {
                if (!ExecuteScriptMutationScope.TryBegin(
                    parameters.manifest, out var mutation, out var governanceError))
                {
                    return BridgeResponse.Error(
                        command.commandId, command.commandType, governanceError);
                }
                using (mutation)
                    return ExecuteInMutationScope(
                        command, parameters, stopwatch, logs.Entries, mutation);
            }
        }

        private static BridgeResponse ExecuteInMutationScope(
            BridgeCommand command,
            ExecuteScriptParams parameters,
            Stopwatch stopwatch,
            List<ExecuteScriptLogEntry> unityLogs,
            ExecuteScriptMutationScope mutation)
        {
            var outcome = ExecuteCode(parameters);
            var value = SerializeOutcome(outcome, parameters.manifest.returnSchema);

            ApplyMutationCompletion(outcome, mutation);
            stopwatch.Stop();
            var result = BuildResult(
                outcome, value, unityLogs, mutation.Report, stopwatch.ElapsedMilliseconds);
            return BuildResponse(command, result);
        }

        private static void ApplyMutationCompletion(
            ExecuteScriptOutcome outcome, ExecuteScriptMutationScope mutation)
        {
            var wasSuccessful = outcome.Success;
            var accepted = mutation.Complete(outcome.Success, out var governanceError);
            if (accepted)
                return;
            outcome.Success = false;
            if (string.IsNullOrEmpty(governanceError))
                return;
            outcome.Message = wasSuccessful || string.IsNullOrEmpty(outcome.Message)
                ? governanceError
                : $"{outcome.Message} {governanceError}";
        }

        internal static ExecuteScriptValue SerializeOutcome(
            ExecuteScriptOutcome outcome, string returnSchema)
        {
            if (!outcome.Success)
                return null;
            if (ExecuteScriptResultSerializer.TrySerialize(
                outcome.Value,
                outcome.ResultSet,
                returnSchema,
                out var value,
                out var serializationError))
            {
                return value;
            }
            outcome.Success = false;
            outcome.Message = serializationError;
            return null;
        }

        internal static ExecuteScriptResult BuildResult(
            ExecuteScriptOutcome outcome,
            ExecuteScriptValue value,
            List<ExecuteScriptLogEntry> unityLogs,
            ExecuteScriptMutationReport mutation,
            long executionTimeMs)
        {
            return new ExecuteScriptResult
            {
                success = outcome.Success,
                result = ExecuteScriptResultSerializer.ToLegacyScalar(value),
                resultType = outcome.Value?.GetType().FullName ?? "",
                resultSet = outcome.ResultSet,
                value = value,
                executionTimeMs = executionTimeMs,
                message = outcome.Message,
                compilerDiagnostics = outcome.Diagnostics,
                unityLogs = new List<ExecuteScriptLogEntry>(unityLogs),
                referencedAssemblies = outcome.ResolvedAssemblies
                    .Select(identity => identity.fullName).ToList(),
                resolvedAssemblies = outcome.ResolvedAssemblies,
                assemblyResolutionIssues = outcome.AssemblyResolutionIssues,
                mutation = mutation,
            };
        }

        internal static BridgeResponse BuildResponse(
            BridgeCommand command, ExecuteScriptResult result)
        {
            var dataJson = JsonUtility.ToJson(result);
            if (result.success)
                return BridgeResponse.Success(command.commandId, command.commandType, dataJson);

            var response = BridgeResponse.Error(
                command.commandId,
                command.commandType,
                string.IsNullOrEmpty(result.message) ? "Script execution failed." : result.message);
            response.dataJson = dataJson;
            return response;
        }

        internal static ExecuteScriptOutcome ExecuteCode(ExecuteScriptParams parameters)
        {
            var outcome = ExecuteWithFreshEvaluator(parameters, parameters.returnValue);
            if (outcome.Success || !parameters.returnValue
                || !LooksLikeStatements(parameters.expression))
            {
                return outcome;
            }
            return ExecuteWithFreshEvaluator(parameters, false);
        }

        private static ExecuteScriptOutcome ExecuteWithFreshEvaluator(
            ExecuteScriptParams parameters, bool returnValue)
        {
            using (var writer = new StringWriter())
            {
                if (!TryCreateEvaluator(
                    writer,
                    parameters.manifest,
                    out var evaluator,
                    out var resolvedAssemblies,
                    out var resolutionIssues,
                    out var message))
                {
                    return Failure(
                        message,
                        ExecuteScriptDiagnostics.Parse(writer.ToString()),
                        resolvedAssemblies,
                        resolutionIssues);
                }

                try
                {
                    return returnValue
                        ? Evaluate(evaluator, parameters.expression, writer, resolvedAssemblies)
                        : Run(evaluator, parameters.expression, writer, resolvedAssemblies);
                }
                catch (Exception ex)
                {
                    return Failure(
                        $"Script execution threw {ex.GetType().Name}: {ex.Message}",
                        ExecuteScriptDiagnostics.Parse(writer.ToString()),
                        resolvedAssemblies);
                }
            }
        }

        private static bool TryCreateEvaluator(
            StringWriter writer,
            ExecuteScriptManifest manifest,
            out object evaluator,
            out List<ExecuteScriptAssemblyIdentity> resolvedAssemblies,
            out List<ExecuteScriptAssemblyResolutionIssue> resolutionIssues,
            out string message)
        {
            evaluator = null;
            resolvedAssemblies = new List<ExecuteScriptAssemblyIdentity>();
            resolutionIssues = new List<ExecuteScriptAssemblyResolutionIssue>();
            var settingsType = GetMonoCSharpType("Mono.CSharp.CompilerSettings");
            var printerType = GetMonoCSharpType("Mono.CSharp.ConsoleReportPrinter");
            var contextType = GetMonoCSharpType("Mono.CSharp.CompilerContext");
            var evaluatorType = GetMonoCSharpType("Mono.CSharp.Evaluator");
            var settings = Activator.CreateInstance(settingsType);
            var printer = Activator.CreateInstance(printerType, writer);
            var context = Activator.CreateInstance(contextType, settings, printer);
            evaluator = Activator.CreateInstance(evaluatorType, context);

            var assemblies = ExecuteScriptAssemblyResolver.Resolve(
                AppDomain.CurrentDomain.GetAssemblies(),
                BaselineAssemblyNames(),
                manifest.expectedAssemblies,
                manifest.expectedAssemblyIdentities,
                out resolvedAssemblies,
                out var resolutionIssue);
            if (resolutionIssue != null)
            {
                resolutionIssues.Add(resolutionIssue);
                message = resolutionIssue.message;
                return false;
            }
            var bridgeAssembly = typeof(ExecuteScriptCommandHandler).Assembly;
            if (!assemblies.Contains(bridgeAssembly))
            {
                assemblies.Add(bridgeAssembly);
                resolvedAssemblies.Add(
                    ExecuteScriptAssemblyCandidate.FromAssembly(bridgeAssembly).Identity);
            }
            if (!ReferenceAssemblies(evaluator, assemblies, out message))
                return false;
            if (!ImportNamespaces(evaluator, out message))
                return false;
            writer.GetStringBuilder().Clear();
            return true;
        }

        private static IEnumerable<string> BaselineAssemblyNames()
        {
            return new[]
            {
                typeof(UnityEngine.Object).Assembly.GetName().Name,
                typeof(UnityEditor.Editor).Assembly.GetName().Name,
            }.Where(name => !string.IsNullOrEmpty(name));
        }

        private static bool ReferenceAssemblies(
            object evaluator, IEnumerable<Assembly> assemblies, out string message)
        {
            var method = evaluator.GetType().GetMethod(
                "ReferenceAssembly", new[] { typeof(Assembly) });
            if (method == null)
            {
                message = "Mono.CSharp evaluator does not expose ReferenceAssembly.";
                return false;
            }
            foreach (var assembly in assemblies)
            {
                try
                {
                    method.Invoke(evaluator, new object[] { assembly });
                }
                catch (Exception ex)
                {
                    message = $"Could not reference assembly {assembly.GetName().Name}: "
                        + Unwrap(ex).Message;
                    return false;
                }
            }
            message = "";
            return true;
        }

        private static bool ImportNamespaces(object evaluator, out string message)
        {
            var run = evaluator.GetType().GetMethod("Run", new[] { typeof(string) });
            if (run == null)
            {
                message = "Mono.CSharp evaluator does not expose Run.";
                return false;
            }
            foreach (var ns in new[]
            {
                "System",
                "System.Linq",
                "UnityEngine",
                "UnityEditor",
                "BWS.Editor.ClaudeCodeBridge",
            })
            {
                try
                {
                    if (run.Invoke(evaluator, new object[] { $"using {ns};" }) is not true)
                    {
                        message = $"Could not import namespace {ns}.";
                        return false;
                    }
                }
                catch (Exception ex)
                {
                    message = $"Could not import namespace {ns}: {Unwrap(ex).Message}";
                    return false;
                }
            }
            message = "";
            return true;
        }

        private static ExecuteScriptOutcome Evaluate(
            object evaluator,
            string code,
            StringWriter writer,
            List<ExecuteScriptAssemblyIdentity> resolvedAssemblies)
        {
            var method = evaluator.GetType().GetMethod("Evaluate", new[]
            {
                typeof(string),
                typeof(object).MakeByRefType(),
                typeof(bool).MakeByRefType(),
            });
            if (method == null)
                return Failure("Mono.CSharp evaluator does not expose Evaluate.");

            var args = new object[] { code, null, false };
            var error = InvokeEvaluator(method, evaluator, args) as string;
            var diagnostics = ExecuteScriptDiagnostics.Parse(writer.ToString());
            if (!string.IsNullOrEmpty(error) || ExecuteScriptDiagnostics.HasErrors(diagnostics))
            {
                return Failure(
                    string.IsNullOrEmpty(error) ? "Script compilation failed." : error,
                    diagnostics,
                    resolvedAssemblies);
            }
            return Successful(
                args[1], args[2] is bool resultSet && resultSet,
                "Script evaluated.", diagnostics, resolvedAssemblies);
        }

        private static ExecuteScriptOutcome Run(
            object evaluator,
            string code,
            StringWriter writer,
            List<ExecuteScriptAssemblyIdentity> resolvedAssemblies)
        {
            var method = evaluator.GetType().GetMethod("Run", new[] { typeof(string) });
            if (method == null)
                return Failure("Mono.CSharp evaluator does not expose Run.");
            var success = InvokeEvaluator(method, evaluator, new object[] { code }) is true;
            var diagnostics = ExecuteScriptDiagnostics.Parse(writer.ToString());
            return success && !ExecuteScriptDiagnostics.HasErrors(diagnostics)
                ? Successful(null, false, "Script executed.", diagnostics, resolvedAssemblies)
                : Failure("Script execution failed.", diagnostics, resolvedAssemblies);
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

        private static Type GetMonoCSharpType(string typeName)
        {
            var type = AppDomain.CurrentDomain.GetAssemblies()
                .Select(assembly => assembly.GetType(typeName))
                .FirstOrDefault(found => found != null);
            if (type != null)
                return type;
            return Assembly.Load("Mono.CSharp").GetType(typeName, true);
        }

        private static ExecuteScriptOutcome Successful(
            object value,
            bool resultSet,
            string message,
            List<ExecuteScriptDiagnostic> diagnostics,
            List<ExecuteScriptAssemblyIdentity> resolvedAssemblies)
        {
            return new ExecuteScriptOutcome
            {
                Success = true,
                Value = value,
                ResultSet = resultSet,
                Message = message,
                Diagnostics = diagnostics ?? new List<ExecuteScriptDiagnostic>(),
                ResolvedAssemblies = resolvedAssemblies
                    ?? new List<ExecuteScriptAssemblyIdentity>(),
            };
        }

        private static ExecuteScriptOutcome Failure(
            string message,
            List<ExecuteScriptDiagnostic> diagnostics = null,
            List<ExecuteScriptAssemblyIdentity> resolvedAssemblies = null,
            List<ExecuteScriptAssemblyResolutionIssue> resolutionIssues = null)
        {
            return new ExecuteScriptOutcome
            {
                Success = false,
                Message = message,
                Diagnostics = diagnostics ?? new List<ExecuteScriptDiagnostic>(),
                ResolvedAssemblies = resolvedAssemblies
                    ?? new List<ExecuteScriptAssemblyIdentity>(),
                AssemblyResolutionIssues = resolutionIssues
                    ?? new List<ExecuteScriptAssemblyResolutionIssue>(),
            };
        }

        private static Exception Unwrap(Exception exception)
        {
            return exception is TargetInvocationException invocation && invocation.InnerException != null
                ? invocation.InnerException
                : exception;
        }

        private static bool LooksLikeStatements(string code)
        {
            return code.Contains(";") || code.Contains("\n") || code.Contains("\r");
        }
    }
}
