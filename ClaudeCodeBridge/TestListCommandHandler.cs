using System;
using System.Collections.Generic;
using System.Linq;
using System.Reflection;
using UnityEditor;
using UnityEditor.TestTools.TestRunner.Api;
using UnityEngine;

namespace BWS.Editor.ClaudeCodeBridge
{
    /// <summary>
    /// Command handler for discovering tests without executing them.
    ///
    /// PURPOSE:
    /// Provides Claude Code with the ability to discover available tests,
    /// categories, and test assemblies in the project without running them.
    ///
    /// SUPPORTED OPERATIONS:
    /// 1. "tests" - List individual test methods with metadata
    /// 2. "categories" - List unique test category names
    /// 3. "assemblies" - List test assemblies with test counts
    ///
    /// CRITICAL IMPLEMENTATION NOTES:
    /// - Uses TestRunnerApi.RetrieveTestTree (NOT the obsolete RetrieveTestList)
    /// - The callback is Action&lt;ITestAdaptor&gt;, NOT ICallbacks interface
    /// - Response is deferred until callback fires (returns "running" immediately)
    /// - Walks ITestAdaptor tree recursively to find leaf test nodes
    ///
    /// GUARDS:
    /// - EditorApplication.isCompiling: blocks all operations
    /// - EditorApplication.isPlaying: blocks test tree retrieval
    /// </summary>
    public class TestListCommandHandler : ICommandHandler
    {
        public string CommandType => "list-tests";

        public BridgeResponse Execute(BridgeCommand command)
        {
            try
            {
                if (EditorApplication.isCompiling)
                {
                    return BridgeResponse.Error(
                        command.commandId,
                        command.commandType,
                        "Cannot retrieve test tree while scripts are compiling."
                    );
                }

                if (EditorApplication.isPlaying)
                {
                    return BridgeResponse.Error(
                        command.commandId,
                        command.commandType,
                        "Cannot retrieve test tree during play mode."
                    );
                }

                var parameters = JsonUtility.FromJson<ListTestsParams>(
                    command.parametersJson ?? "{}"
                );
                if (parameters == null)
                    parameters = new ListTestsParams();

                // Default mode to "tests" if empty
                if (string.IsNullOrEmpty(parameters.mode))
                    parameters.mode = "tests";

                BridgeLogger.LogDebug($"List tests mode: {parameters.mode}");

                var testRunnerApi = ScriptableObject.CreateInstance<TestRunnerApi>();
                var testMode = ParseTestMode(parameters.testPlatform);
                var capturedParams = parameters;
                var capturedCommand = command;

                // RetrieveTestTree uses Action<ITestAdaptor> callback directly.
                // NOT the ICallbacks interface used by Execute().
                RetrieveTestTree(
                    testRunnerApi,
                    testMode,
                    (ITestAdaptor testTree) =>
                    {
                        try
                        {
                            var result = ProcessTestTree(
                                testTree, capturedParams, capturedCommand
                            );
                            var resultJson = JsonUtility.ToJson(result);
                            ClaudeUnityBridge.WriteResponseStatic(
                                BridgeResponse.Success(
                                    capturedCommand.commandId,
                                    capturedCommand.commandType,
                                    resultJson
                                )
                            );
                        }
                        catch (Exception ex)
                        {
                            BridgeLogger.LogError($"Error processing test tree: {ex}");
                            ClaudeUnityBridge.WriteResponseStatic(
                                BridgeResponse.Error(
                                    capturedCommand.commandId,
                                    capturedCommand.commandType,
                                    $"Error processing test tree: {ex.Message}"
                                )
                            );
                        }
                    }
                );

                // Return "running" immediately; real response comes from callback
                return BridgeResponse.Running(
                    command.commandId,
                    command.commandType,
                    "{\"success\":true,\"message\":\"Retrieving test tree...\"}"
                );
            }
            catch (Exception ex)
            {
                BridgeLogger.LogError($"Error: {ex}");
                return BridgeResponse.Error(command.commandId, command.commandType, ex.ToString());
            }
        }

        private static void RetrieveTestTree(
            TestRunnerApi testRunnerApi,
            TestMode testMode,
            Action<ITestAdaptor> callback)
        {
            var apiType = testRunnerApi.GetType();
            var treeMethod = FindRetrieveMethod(apiType, "RetrieveTestTree", typeof(ExecutionSettings));
            if (treeMethod is not null)
            {
                var filter = new Filter { testMode = testMode };
                treeMethod.Invoke(testRunnerApi, new object[] { new ExecutionSettings(filter), callback });
                return;
            }

            var listMethod = FindRetrieveMethod(apiType, "RetrieveTestList", typeof(TestMode));
            if (listMethod is not null)
            {
                listMethod.Invoke(testRunnerApi, new object[] { testMode, callback });
                return;
            }

            throw new MissingMethodException(
                "Unity Test Framework does not expose RetrieveTestTree or compatible fallback.");
        }

        private static MethodInfo FindRetrieveMethod(Type apiType, string name, Type firstParameterType)
        {
            foreach (var method in apiType.GetMethods(BindingFlags.Public | BindingFlags.Instance))
            {
                if (method.Name != name)
                    continue;
                var parameters = method.GetParameters();
                if (parameters.Length == 2
                    && parameters[0].ParameterType == firstParameterType)
                    return method;
            }
            return null;
        }

        /// <summary>
        /// Process the retrieved test tree based on the requested mode.
        /// </summary>
        private ListTestsResult ProcessTestTree(
            ITestAdaptor testTree,
            ListTestsParams parameters,
            BridgeCommand command
        )
        {
            var leafTests = new List<ITestAdaptor>();
            CollectLeafTests(testTree, leafTests);

            // Apply filter if provided
            if (!string.IsNullOrEmpty(parameters.filter))
            {
                var filterLower = parameters.filter.ToLower();
                leafTests = leafTests
                    .Where(t => t.FullName.ToLower().Contains(filterLower))
                    .ToList();
            }

            switch (parameters.mode?.ToLower())
            {
                case "categories":
                    return BuildCategoriesResult(leafTests);
                case "assemblies":
                    return BuildAssembliesResult(leafTests);
                case "tests":
                default:
                    return BuildTestsResult(leafTests);
            }
        }

        /// <summary>
        /// Build result listing individual tests with metadata.
        /// </summary>
        private ListTestsResult BuildTestsResult(List<ITestAdaptor> leafTests)
        {
            var result = new ListTestsResult { success = true };

            foreach (var test in leafTests)
            {
                var info = new TestInfoEntry
                {
                    fullName = test.FullName,
                    className = ExtractClassName(test.FullName),
                    methodName = test.Name,
                };

                // Extract categories from test properties
                foreach (var cat in test.Categories)
                {
                    info.categories.Add(cat);
                }

                // Extract assembly name from parent chain
                info.assembly = FindAssemblyName(test);

                result.tests.Add(info);
            }

            result.count = result.tests.Count;
            BridgeLogger.LogInfo($"Listed {result.count} tests");
            return result;
        }

        /// <summary>
        /// Build result listing unique category names.
        /// </summary>
        private ListTestsResult BuildCategoriesResult(List<ITestAdaptor> leafTests)
        {
            var result = new ListTestsResult { success = true };
            var categories = new HashSet<string>();

            foreach (var test in leafTests)
            {
                foreach (var cat in test.Categories)
                {
                    categories.Add(cat);
                }
            }

            result.categories = categories.OrderBy(c => c).ToList();
            result.count = result.categories.Count;
            BridgeLogger.LogInfo($"Found {result.count} categories");
            return result;
        }

        /// <summary>
        /// Build result listing test assemblies with counts.
        /// </summary>
        private ListTestsResult BuildAssembliesResult(List<ITestAdaptor> leafTests)
        {
            var result = new ListTestsResult { success = true };
            var assemblyCounts = new Dictionary<string, int>();

            foreach (var test in leafTests)
            {
                var assemblyName = FindAssemblyName(test);
                if (string.IsNullOrEmpty(assemblyName))
                    assemblyName = "Unknown";

                if (assemblyCounts.ContainsKey(assemblyName))
                    assemblyCounts[assemblyName]++;
                else
                    assemblyCounts[assemblyName] = 1;
            }

            foreach (var kvp in assemblyCounts.OrderBy(k => k.Key))
            {
                result.assemblies.Add(new TestAssemblyInfoEntry
                {
                    name = kvp.Key,
                    testCount = kvp.Value
                });
            }

            result.count = result.assemblies.Count;
            BridgeLogger.LogInfo($"Found {result.count} test assemblies");
            return result;
        }

        /// <summary>
        /// Recursively walk the test tree and collect leaf nodes (actual test methods).
        /// Leaf nodes are those where IsSuite is false.
        /// </summary>
        private void CollectLeafTests(ITestAdaptor node, List<ITestAdaptor> results)
        {
            if (node == null) return;

            if (!node.IsSuite)
            {
                results.Add(node);
                return;
            }

            if (node.Children != null)
            {
                foreach (var child in node.Children)
                {
                    CollectLeafTests(child, results);
                }
            }
        }

        /// <summary>
        /// Extract the class name from a fully qualified test name.
        /// E.g. "Tests.Combat.CombatControllerTests.AttackDealsDamage" -> "CombatControllerTests"
        /// </summary>
        private string ExtractClassName(string fullName)
        {
            if (string.IsNullOrEmpty(fullName)) return "";

            var parts = fullName.Split('.');
            if (parts.Length >= 2)
                return parts[parts.Length - 2];
            return fullName;
        }

        /// <summary>
        /// Walk up the parent chain to find the assembly name for a test.
        /// The root-level children of the test tree typically represent assemblies.
        /// </summary>
        private string FindAssemblyName(ITestAdaptor test)
        {
            var current = test;
            ITestAdaptor previous = null;

            while (current.Parent != null)
            {
                previous = current;
                current = current.Parent;
            }

            // The direct child of root is typically the assembly
            if (previous != null && previous != test)
                return previous.Name;

            return test.Name;
        }

        /// <summary>
        /// Parse a platform string to TestMode enum.
        /// Defaults to EditMode if not specified or unrecognised.
        /// </summary>
        private TestMode ParseTestMode(string platform)
        {
            if (string.IsNullOrEmpty(platform))
                return TestMode.EditMode;

            switch (platform.ToLower())
            {
                case "playmode":
                    return TestMode.PlayMode;
                case "editmode":
                default:
                    return TestMode.EditMode;
            }
        }
    }
}
