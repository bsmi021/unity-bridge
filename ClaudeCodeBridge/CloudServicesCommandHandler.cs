using System;
using System.Collections.Generic;
using System.Reflection;
using UnityEditor;
using UnityEngine;

namespace BWS.Editor.ClaudeCodeBridge
{
    /// <summary>
    /// Reads Unity Gaming Services configuration (project ID, organization ID,
    /// active environment) so CI/CD agents can bootstrap UGS-linked workflows
    /// without hard-coding IDs.
    ///
    /// Uses the public static <c>UnityEditor.CloudProjectSettings</c> surface.
    /// Environment ID requires the <c>com.unity.services.core</c> package and
    /// is resolved via reflection against its Editor assembly when present.
    ///
    /// SUPPORTED OPERATIONS:
    /// 1. "get-project-id"     - Read project GUID, name, organization ID.
    /// 2. "get-environments"   - List known environments (requires Services package).
    /// 3. "get-active-environment" - Return the active environment ID/name.
    /// </summary>
    public class CloudServicesCommandHandler : ICommandHandler
    {
        public string CommandType => "cloud-services";

        public BridgeResponse Execute(BridgeCommand command)
        {
            try
            {
                var parameters = JsonUtility.FromJson<CloudServicesParams>(
                    command.parametersJson ?? "{}") ?? new CloudServicesParams();
                var operation = parameters.operation?.ToLower();

                switch (operation)
                {
                    case "get-project-id":
                        return HandleGetProjectId(command);
                    case "get-environments":
                        return HandleGetEnvironments(command);
                    case "get-active-environment":
                        return HandleGetActiveEnvironment(command);
                    default:
                        return BridgeResponse.Error(
                            command.commandId, command.commandType,
                            $"Unknown operation: {parameters.operation}. " +
                            "Supported: get-project-id, get-environments, get-active-environment");
                }
            }
            catch (Exception ex)
            {
                BridgeLogger.LogError($"Cloud services error: {ex}");
                return BridgeResponse.Error(command.commandId, command.commandType, ex.ToString());
            }
        }

        private BridgeResponse HandleGetProjectId(BridgeCommand command)
        {
            var result = new CloudProjectInfo
            {
                projectId = CloudProjectSettings.projectId,
                projectName = CloudProjectSettings.projectName,
                organizationId = CloudProjectSettings.organizationId,
                organizationName = SafeReadString(typeof(CloudProjectSettings), "organizationName"),
                userId = SafeReadString(typeof(CloudProjectSettings), "userId"),
                userName = SafeReadString(typeof(CloudProjectSettings), "userName"),
                success = true
            };
            return BridgeResponse.Success(
                command.commandId, command.commandType,
                JsonUtility.ToJson(result));
        }

        private BridgeResponse HandleGetEnvironments(BridgeCommand command)
        {
            var result = new CloudEnvironmentsResult { success = true };

            var servicesCore = FindServicesCoreEditorType();
            if (servicesCore == null)
            {
                result.packageInstalled = false;
                result.message = "com.unity.services.core not installed; no environments available.";
                return BridgeResponse.Success(
                    command.commandId, command.commandType,
                    JsonUtility.ToJson(result));
            }

            result.packageInstalled = true;
            result.activeEnvironmentId = SafeReadString(servicesCore, "environmentId");
            result.activeEnvironmentName = SafeReadString(servicesCore, "environmentName");
            result.environments = new List<string>();
            if (!string.IsNullOrEmpty(result.activeEnvironmentName))
                result.environments.Add(result.activeEnvironmentName);
            result.message = "Environment listing via the Services API requires the dashboard REST call; " +
                "only the currently-linked environment is returned from the Editor.";
            return BridgeResponse.Success(
                command.commandId, command.commandType,
                JsonUtility.ToJson(result));
        }

        private BridgeResponse HandleGetActiveEnvironment(BridgeCommand command)
        {
            var servicesCore = FindServicesCoreEditorType();
            var result = new CloudEnvironmentsResult
            {
                success = true,
                packageInstalled = servicesCore != null,
                activeEnvironmentId = servicesCore != null ? SafeReadString(servicesCore, "environmentId") : null,
                activeEnvironmentName = servicesCore != null ? SafeReadString(servicesCore, "environmentName") : null,
            };
            if (!result.packageInstalled)
                result.message = "com.unity.services.core not installed.";
            return BridgeResponse.Success(
                command.commandId, command.commandType,
                JsonUtility.ToJson(result));
        }

        private static Type FindServicesCoreEditorType()
        {
            // Search loaded assemblies for the Services Core editor settings type.
            foreach (var asm in AppDomain.CurrentDomain.GetAssemblies())
            {
                var t = asm.GetType("Unity.Services.Core.Editor.CloudServicesProjectSettings");
                if (t != null) return t;
            }
            return null;
        }

        private static string SafeReadString(Type type, string memberName)
        {
            try
            {
                var prop = type.GetProperty(memberName, BindingFlags.Public | BindingFlags.Static);
                if (prop != null) return prop.GetValue(null)?.ToString();
                var field = type.GetField(memberName, BindingFlags.Public | BindingFlags.Static);
                if (field != null) return field.GetValue(null)?.ToString();
            }
            catch { }
            return null;
        }
    }

    [Serializable]
    public class CloudServicesParams
    {
        public string operation;
    }

    [Serializable]
    public class CloudProjectInfo
    {
        public bool success;
        public string projectId;
        public string projectName;
        public string organizationId;
        public string organizationName;
        public string userId;
        public string userName;
    }

    [Serializable]
    public class CloudEnvironmentsResult
    {
        public bool success;
        public bool packageInstalled;
        public string activeEnvironmentId;
        public string activeEnvironmentName;
        public List<string> environments;
        public string message;
    }
}
