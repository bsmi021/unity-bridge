using System;
using System.Collections;
using System.Collections.Generic;
using System.IO;
using System.Reflection;
using UnityEditor;
using UnityEngine;

namespace BWS.Editor.ClaudeCodeBridge
{
    /// <summary>
    /// Read-only Multiplayer Play Mode inspection.
    /// </summary>
    public class MultiplayerPlayModeCommandHandler : ICommandHandler
    {
        private const string CurrentPlayerTypeName = "Unity.Multiplayer.PlayMode.CurrentPlayer";
        private const string EngineModuleName = "UnityEngine.MultiplayerModule";
        private const string EditorModuleName = "UnityEditor.MultiplayerModule";

        private static readonly string[] PackageNames =
        {
            "com.unity.multiplayer.playmode",
            "com.unity.multiplayer.center",
            "com.unity.multiplayer.tools"
        };

        public string CommandType => "multiplayer-playmode";

        public BridgeResponse Execute(BridgeCommand command)
        {
            string operation = "availability";
            try
            {
                var parameters = JsonUtility.FromJson<MultiplayerPlayModeParams>(
                    command.parametersJson ?? "{}") ?? new MultiplayerPlayModeParams();
                operation = string.IsNullOrEmpty(parameters.operation)
                    ? "availability"
                    : parameters.operation.ToLowerInvariant();

                switch (operation)
                {
                    case "availability":
                        return Success(command, BuildAvailability(operation));
                    case "current-player":
                        return Success(command, BuildCurrentPlayerResult(operation));
                    case "packages":
                        return Success(command, BuildPackagesResult(operation));
                    default:
                        return BridgeResponse.Error(command.commandId, command.commandType,
                            "Unknown operation. Supported: availability, current-player, packages");
                }
            }
            catch (Exception ex)
            {
                BridgeLogger.LogError($"Multiplayer Play Mode error: {ex}");
                var result = BaseResult(operation);
                result.success = false;
                result.message = ex.ToString();
                return Error(command, result);
            }
        }

        private static MultiplayerPlayModeResult BuildAvailability(string operation)
        {
            var result = BaseResult(operation);
            result.packages = BuildPackageList();
            result.packageCount = result.packages.Count;
            result.message = result.currentPlayerTypePresent
                ? "Multiplayer Play Mode CurrentPlayer API is available."
                : "Multiplayer Play Mode CurrentPlayer API is not available.";
            return result;
        }

        private static MultiplayerPlayModeResult BuildCurrentPlayerResult(string operation)
        {
            var result = BaseResult(operation);
            Type currentPlayerType = FindType(CurrentPlayerTypeName);
            result.currentPlayer = BuildCurrentPlayer(currentPlayerType);
            result.message = result.currentPlayer.available
                ? "Read Multiplayer Play Mode current player."
                : result.currentPlayer.message;
            return result;
        }

        private static MultiplayerPlayModeResult BuildPackagesResult(string operation)
        {
            var result = BaseResult(operation);
            result.packages = BuildPackageList();
            result.packageCount = result.packages.Count;
            result.message = $"Inspected {result.packageCount} Multiplayer package(s).";
            return result;
        }

        private static MultiplayerCurrentPlayerInfo BuildCurrentPlayer(Type type)
        {
            var info = new MultiplayerCurrentPlayerInfo
            {
                available = type != null,
                typeName = type?.FullName ?? CurrentPlayerTypeName,
                message = type == null
                    ? "Unity.Multiplayer.PlayMode.CurrentPlayer is not available."
                    : "CurrentPlayer data is available."
            };
            if (type == null) return info;

            object isMainEditor = GetStaticValue(type, "IsMainEditor");
            info.isMainEditorAvailable = isMainEditor is bool;
            info.isMainEditor = Bool(isMainEditor);
            info.role = info.isMainEditorAvailable
                ? (info.isMainEditor ? "main-editor" : "virtual-player")
                : "unknown";
            info.tags = ToStringList(GetStaticValue(type, "Tags"));
            info.readOnlyTags = ToStringList(GetStaticValue(type, "ReadOnlyTags"));
            return info;
        }

        private static MultiplayerPlayModeResult BaseResult(string operation)
        {
            Type currentPlayerType = FindType(CurrentPlayerTypeName);
            return new MultiplayerPlayModeResult
            {
                success = true,
                operation = operation,
                unityEngineMultiplayerModulePresent = IsAssemblyOrModulePresent(EngineModuleName),
                unityEditorMultiplayerModulePresent = IsAssemblyOrModulePresent(EditorModuleName),
                currentPlayerTypePresent = currentPlayerType != null,
                currentPlayerTypeName = currentPlayerType?.FullName ?? CurrentPlayerTypeName
            };
        }

        private static List<MultiplayerPackageInfo> BuildPackageList()
        {
            var packages = new List<MultiplayerPackageInfo>();
            foreach (string packageName in PackageNames)
                packages.Add(BuildPackageInfo(packageName));
            return packages;
        }

        private static MultiplayerPackageInfo BuildPackageInfo(string packageName)
        {
            var info = new MultiplayerPackageInfo
            {
                packageName = packageName,
                manifestDependency = IsManifestDependency(packageName),
                embeddedPackage = IsEmbeddedPackage(packageName),
                packageCacheAvailable = IsPackageCacheAvailable(packageName)
            };

            try
            {
                UnityEditor.PackageManager.PackageInfo packageInfo =
                    UnityEditor.PackageManager.PackageInfo.FindForPackageName(packageName);
                if (packageInfo != null)
                {
                    info.packageInfoAvailable = true;
                    info.displayName = packageInfo.displayName;
                    info.version = packageInfo.version;
                    info.source = packageInfo.source.ToString();
                    info.resolvedPath = packageInfo.resolvedPath;
                }
            }
            catch (Exception ex)
            {
                info.packageInfoError = ex.Message;
            }

            info.packageAvailable = info.manifestDependency || info.embeddedPackage
                || info.packageCacheAvailable || info.packageInfoAvailable;
            return info;
        }

        private static bool IsAssemblyOrModulePresent(string assemblyName)
        {
            foreach (Assembly assembly in AppDomain.CurrentDomain.GetAssemblies())
            {
                if (assembly.GetName().Name == assemblyName) return true;
            }

            string contents = EditorApplication.applicationContentsPath;
            if (string.IsNullOrEmpty(contents)) return false;

            string dll = assemblyName + ".dll";
            return File.Exists(Path.Combine(contents, "Managed", dll))
                || File.Exists(Path.Combine(contents, "Managed", "UnityEngine", dll))
                || File.Exists(Path.Combine(contents, "Managed", "UnityEditor", dll));
        }

        private static Type FindType(string fullName)
        {
            Type direct = Type.GetType(fullName + ", Unity.Multiplayer.PlayMode");
            if (direct != null) return direct;

            foreach (Assembly assembly in AppDomain.CurrentDomain.GetAssemblies())
            {
                Type type = assembly.GetType(fullName);
                if (type != null) return type;
            }
            return null;
        }

        private static object GetStaticValue(Type type, string name)
        {
            const BindingFlags flags = BindingFlags.Public | BindingFlags.Static;
            try
            {
                PropertyInfo property = type.GetProperty(name, flags);
                if (property != null) return property.GetValue(null);
                FieldInfo field = type.GetField(name, flags);
                return field?.GetValue(null);
            }
            catch (Exception ex)
            {
                BridgeLogger.LogWarning($"CurrentPlayer.{name} read failed: {ex.Message}");
                return null;
            }
        }

        private static List<string> ToStringList(object value)
        {
            var list = new List<string>();
            if (value == null) return list;
            if (value is string text)
            {
                if (!string.IsNullOrEmpty(text)) list.Add(text);
                return list;
            }
            if (value is IEnumerable enumerable)
            {
                foreach (object item in enumerable)
                    if (item != null) list.Add(item.ToString());
                return list;
            }
            list.Add(value.ToString());
            return list;
        }

        private static bool IsManifestDependency(string packageName)
        {
            string root = GetProjectRoot();
            if (string.IsNullOrEmpty(root)) return false;

            string manifest = Path.Combine(root, "Packages", "manifest.json");
            if (!File.Exists(manifest)) return false;

            try
            {
                return File.ReadAllText(manifest).Contains("\"" + packageName + "\"");
            }
            catch
            {
                return false;
            }
        }

        private static bool IsEmbeddedPackage(string packageName)
        {
            string root = GetProjectRoot();
            if (string.IsNullOrEmpty(root)) return false;
            return Directory.Exists(Path.Combine(root, "Packages", packageName));
        }

        private static bool IsPackageCacheAvailable(string packageName)
        {
            string root = GetProjectRoot();
            if (string.IsNullOrEmpty(root)) return false;

            string cache = Path.Combine(root, "Library", "PackageCache");
            if (!Directory.Exists(cache)) return false;

            try
            {
                return Directory.GetDirectories(cache, packageName + "*").Length > 0;
            }
            catch
            {
                return false;
            }
        }

        private static string GetProjectRoot()
        {
            DirectoryInfo parent = Directory.GetParent(Application.dataPath);
            return parent?.FullName;
        }

        private static bool Bool(object value)
        {
            return value is bool b && b;
        }

        private static BridgeResponse Success(
            BridgeCommand command, MultiplayerPlayModeResult result)
        {
            return BridgeResponse.Success(command.commandId, command.commandType,
                JsonUtility.ToJson(result));
        }

        private static BridgeResponse Error(
            BridgeCommand command, MultiplayerPlayModeResult result)
        {
            return new BridgeResponse
            {
                commandId = command.commandId,
                commandType = command.commandType,
                status = "error",
                timestamp = DateTime.UtcNow.ToString("o"),
                dataJson = JsonUtility.ToJson(result),
                errorMessage = result.message
            };
        }
    }

    [Serializable]
    public class MultiplayerPlayModeParams
    {
        public string operation;
    }

    [Serializable]
    public class MultiplayerPlayModeResult
    {
        public bool success;
        public string operation;
        public bool unityEngineMultiplayerModulePresent;
        public bool unityEditorMultiplayerModulePresent;
        public bool currentPlayerTypePresent;
        public string currentPlayerTypeName;
        public int packageCount;
        public MultiplayerCurrentPlayerInfo currentPlayer;
        public List<MultiplayerPackageInfo> packages = new List<MultiplayerPackageInfo>();
        public string message;
    }

    [Serializable]
    public class MultiplayerCurrentPlayerInfo
    {
        public bool available;
        public string typeName;
        public bool isMainEditorAvailable;
        public bool isMainEditor;
        public string role;
        public List<string> tags = new List<string>();
        public List<string> readOnlyTags = new List<string>();
        public string message;
    }

    [Serializable]
    public class MultiplayerPackageInfo
    {
        public string packageName;
        public bool packageAvailable;
        public bool manifestDependency;
        public bool embeddedPackage;
        public bool packageCacheAvailable;
        public bool packageInfoAvailable;
        public string displayName;
        public string version;
        public string source;
        public string resolvedPath;
        public string packageInfoError;
    }
}
