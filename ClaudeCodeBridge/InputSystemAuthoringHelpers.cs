using System;
using System.Collections;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Reflection;
using UnityEditor;
using UnityEngine;

namespace BWS.Editor.ClaudeCodeBridge
{
    internal static class InputSystemAuthoringHelpers
    {
        private const string AssetTypeName = "UnityEngine.InputSystem.InputActionAsset";
        private const string MapTypeName = "UnityEngine.InputSystem.InputActionMap";
        private const string ActionTypeName = "UnityEngine.InputSystem.InputAction";
        private const string SetupTypeName = "UnityEngine.InputSystem.InputActionSetupExtensions";

        public static BridgeResponse Handle(BridgeCommand command, InputSystemParams parameters)
        {
            var operation = parameters.operation?.ToLower();
            try
            {
                switch (operation)
                {
                    case "create-asset":
                        return HandleCreateAsset(command, parameters);
                    case "add-action-map":
                        return HandleAddActionMap(command, parameters);
                    case "add-action":
                        return HandleAddAction(command, parameters);
                    case "add-binding":
                        return HandleAddBinding(command, parameters);
                    case "add-control-scheme":
                        return HandleAddControlScheme(command, parameters);
                    case "list-control-schemes":
                        return HandleListControlSchemes(command, parameters);
                    default:
                        return Error(command, operation, $"Unknown operation: {parameters.operation}");
                }
            }
            catch (TargetInvocationException ex)
            {
                return Error(command, operation, ex.InnerException?.Message ?? ex.Message);
            }
            catch (Exception ex)
            {
                BridgeLogger.LogError($"Input system authoring error: {ex}");
                return Error(command, operation, ex.Message);
            }
        }

        private static BridgeResponse HandleCreateAsset(
            BridgeCommand command, InputSystemParams p)
        {
            var error = ValidateAssetPath(p) ?? ValidateNotPlaying();
            if (error != null) return Error(command, p.operation, error, p);
            if (File.Exists(ToFullPath(p.assetPath)) && !p.overwrite)
                return Error(command, p.operation, $"Asset already exists: {p.assetPath}", p);

            EnsureDirectoryExists(p.assetPath);
            var name = Path.GetFileNameWithoutExtension(p.assetPath);
            var json = NormalizeJson(CreateEmptyAssetJson(name));
            File.WriteAllText(ToFullPath(p.assetPath), json);
            ImportAndSave(p.assetPath);
            return Success(command, p, $"Created InputActionAsset: {p.assetPath}", json);
        }

        private static BridgeResponse HandleAddActionMap(
            BridgeCommand command, InputSystemParams p)
        {
            var error = ValidateAssetPath(p) ?? Require(p.actionMap, "actionMap") ?? ValidateNotPlaying();
            if (error != null) return Error(command, p.operation, error, p);
            var asset = LoadAsset(p.assetPath, command);
            if (asset == null) return Error(command, p.operation, $"InputActionAsset not found: {p.assetPath}", p);

            var existing = FindActionMap(asset, p.actionMap);
            if (existing != null && !p.overwrite)
                return Error(command, p.operation, $"Action map already exists: {p.actionMap}", p);
            if (existing != null) InvokeExtension("RemoveActionMap", AssetTypeName, 2, asset, p.actionMap);

            InvokeExtension("AddActionMap", AssetTypeName, 2, asset, p.actionMap);
            var json = PersistAsset(asset, p.assetPath);
            return Success(command, p, $"Added action map '{p.actionMap}'", json);
        }

        private static BridgeResponse HandleAddAction(
            BridgeCommand command, InputSystemParams p)
        {
            var error = ValidateActionTarget(p) ?? ValidateNotPlaying();
            if (error != null) return Error(command, p.operation, error, p);
            var asset = LoadAsset(p.assetPath, command);
            var map = asset != null ? FindActionMap(asset, p.actionMap) : null;
            if (map == null) return Error(command, p.operation, $"Action map not found: {p.actionMap}", p);

            var existing = FindAction(map, p.actionName);
            if (existing != null && !p.overwrite)
                return Error(command, p.operation, $"Action already exists: {p.actionName}", p);
            if (existing != null) InvokeExtension("RemoveAction", ActionTypeName, 1, existing);

            var type = ParseActionType(p.actionType);
            InvokeExtension("AddAction", MapTypeName, 8, map, p.actionName, type,
                NullIfEmpty(p.bindingPath), NullIfEmpty(p.interactions), NullIfEmpty(p.processors),
                NullIfEmpty(p.groups), NullIfEmpty(p.expectedControlType));
            var json = PersistAsset(asset, p.assetPath);
            return Success(command, p, $"Added action '{p.actionName}'", json);
        }

        private static BridgeResponse HandleAddBinding(
            BridgeCommand command, InputSystemParams p)
        {
            var error = ValidateActionTarget(p) ?? Require(p.bindingPath, "bindingPath") ?? ValidateNotPlaying();
            if (error != null) return Error(command, p.operation, error, p);
            var asset = LoadAsset(p.assetPath, command);
            var map = asset != null ? FindActionMap(asset, p.actionMap) : null;
            var action = map != null ? FindAction(map, p.actionName) : null;
            if (action == null) return Error(command, p.operation, $"Action not found: {p.actionName}", p);

            InvokeExtension("AddBinding", ActionTypeName, 5, action, p.bindingPath,
                NullIfEmpty(p.interactions), NullIfEmpty(p.processors), NullIfEmpty(p.groups));
            var json = PersistAsset(asset, p.assetPath);
            return Success(command, p, $"Added binding '{p.bindingPath}'", json);
        }

        private static BridgeResponse HandleAddControlScheme(
            BridgeCommand command, InputSystemParams p)
        {
            var error = ValidateControlScheme(p) ?? ValidateNotPlaying();
            if (error != null) return Error(command, p.operation, error, p);
            var asset = LoadAsset(p.assetPath, command);
            if (asset == null) return Error(command, p.operation, $"InputActionAsset not found: {p.assetPath}", p);
            var names = GetControlSchemeNames(asset);
            if (names.Contains(p.controlScheme, StringComparer.OrdinalIgnoreCase) && !p.overwrite)
                return Error(command, p.operation, $"Control scheme already exists: {p.controlScheme}", p);
            if (names.Contains(p.controlScheme, StringComparer.OrdinalIgnoreCase))
                InvokeExtension("RemoveControlScheme", AssetTypeName, 2, asset, p.controlScheme);

            var syntax = InvokeExtension("AddControlScheme", AssetTypeName, 2, asset, p.controlScheme);
            if (!string.IsNullOrEmpty(p.bindingGroup))
                syntax = InvokeSyntax(syntax, "WithBindingGroup", p.bindingGroup);
            foreach (var path in p.devicePaths)
                syntax = InvokeSyntax(syntax, "WithRequiredDevice", path);
            var json = PersistAsset(asset, p.assetPath);
            return Success(command, p, $"Added control scheme '{p.controlScheme}'", json);
        }

        private static BridgeResponse HandleListControlSchemes(
            BridgeCommand command, InputSystemParams p)
        {
            var error = ValidateAssetPath(p);
            if (error != null) return Error(command, p.operation, error, p);
            var asset = LoadAsset(p.assetPath, command);
            if (asset == null) return Error(command, p.operation, $"InputActionAsset not found: {p.assetPath}", p);
            var result = Result(p, $"Found control schemes in {p.assetPath}", null);
            result.controlSchemes = GetControlSchemeNames(asset);
            return BridgeResponse.Success(command.commandId, command.commandType, JsonUtility.ToJson(result));
        }

        private static string ValidateActionTarget(InputSystemParams p)
        {
            return ValidateAssetPath(p) ?? Require(p.actionMap, "actionMap") ??
                Require(p.actionName, "actionName");
        }

        private static string ValidateControlScheme(InputSystemParams p)
        {
            if (p.devicePaths == null) p.devicePaths = new List<string>();
            p.devicePaths = p.devicePaths.Where(path => !string.IsNullOrEmpty(path)).ToList();
            return ValidateAssetPath(p) ?? Require(p.controlScheme, "controlScheme");
        }

        private static string ValidateAssetPath(InputSystemParams p)
        {
            return Require(p.assetPath, "assetPath");
        }

        private static string ValidateNotPlaying()
        {
            return EditorApplication.isPlaying ? "Cannot modify InputActionAssets during play mode." : null;
        }

        private static string Require(string value, string name)
        {
            return string.IsNullOrEmpty(value) ? $"{name} is required" : null;
        }

        private static UnityEngine.Object LoadAsset(string path, BridgeCommand command)
        {
            var type = GetTypeByName(AssetTypeName);
            if (type == null)
            {
                BridgeLogger.LogWarning($"Input System type unavailable for {command.commandId}");
                return null;
            }
            return AssetDatabase.LoadAssetAtPath(path, type);
        }

        private static object FindActionMap(UnityEngine.Object asset, string name)
        {
            return InvokeInstance(asset, "FindActionMap", name, false);
        }

        private static object FindAction(object map, string name)
        {
            return InvokeInstance(map, "FindAction", name, false);
        }

        private static object InvokeInstance(object target, string name, params object[] args)
        {
            var method = target.GetType().GetMethods().FirstOrDefault(m =>
                m.Name == name && m.GetParameters().Length == args.Length);
            return method?.Invoke(target, args);
        }

        private static object InvokeExtension(
            string name, string firstType, int parameterCount, params object[] args)
        {
            var method = GetSetupType().GetMethods(BindingFlags.Public | BindingFlags.Static)
                .FirstOrDefault(m => IsExtensionMatch(m, name, firstType, parameterCount, args));
            if (method == null) throw new MissingMethodException(SetupTypeName, name);
            return method.Invoke(null, args);
        }

        private static bool IsExtensionMatch(
            MethodInfo method, string name, string firstType, int parameterCount, object[] args)
        {
            var parameters = method.GetParameters();
            if (method.Name != name || parameters.Length != parameterCount ||
                parameters[0].ParameterType.FullName != firstType)
            {
                return false;
            }
            for (var i = 1; i < parameters.Length; i++)
            {
                if (args[i] != null && !parameters[i].ParameterType.IsInstanceOfType(args[i]))
                    return false;
            }
            return true;
        }

        private static object InvokeSyntax(object syntax, string methodName, string value)
        {
            var method = syntax.GetType().GetMethod(methodName, new[] { typeof(string) });
            if (method == null) throw new MissingMethodException(syntax.GetType().FullName, methodName);
            return method.Invoke(syntax, new object[] { value });
        }

        private static object ParseActionType(string actionType)
        {
            var type = GetTypeByName("UnityEngine.InputSystem.InputActionType");
            if (type == null) throw new TypeLoadException("InputActionType not found");
            if (string.IsNullOrEmpty(actionType)) return Activator.CreateInstance(type);
            var normalized = actionType.Replace("-", "").Replace("_", "");
            foreach (var name in Enum.GetNames(type))
            {
                if (string.Equals(name, normalized, StringComparison.OrdinalIgnoreCase))
                    return Enum.Parse(type, name);
            }
            throw new ArgumentException($"Unknown actionType: {actionType}");
        }

        private static List<string> GetControlSchemeNames(UnityEngine.Object asset)
        {
            var property = asset.GetType().GetProperty("controlSchemes");
            var schemes = property?.GetValue(asset, null) as IEnumerable;
            var names = new List<string>();
            if (schemes == null) return names;
            foreach (var scheme in schemes)
            {
                var name = scheme.GetType().GetProperty("name")?.GetValue(scheme, null) as string;
                if (!string.IsNullOrEmpty(name)) names.Add(name);
            }
            return names;
        }

        private static string PersistAsset(UnityEngine.Object asset, string path)
        {
            var json = InvokeToJson(asset);
            File.WriteAllText(ToFullPath(path), json);
            ImportAndSave(path);
            return json;
        }

        private static void ImportAndSave(string path)
        {
            AssetDatabase.ImportAsset(path);
            AssetDatabase.SaveAssets();
        }

        private static string NormalizeJson(string json)
        {
            var method = GetTypeByName(AssetTypeName).GetMethod(
                "FromJson", BindingFlags.Public | BindingFlags.Static);
            var asset = method.Invoke(null, new object[] { json }) as UnityEngine.Object;
            var normalized = InvokeToJson(asset);
            UnityEngine.Object.DestroyImmediate(asset);
            return normalized;
        }

        private static string InvokeToJson(UnityEngine.Object asset)
        {
            var method = asset.GetType().GetMethod(
                "ToJson", BindingFlags.Public | BindingFlags.Instance);
            return method?.Invoke(asset, null) as string ?? EditorJsonUtility.ToJson(asset, true);
        }

        private static Type GetSetupType()
        {
            var type = GetTypeByName(SetupTypeName);
            if (type == null) throw new TypeLoadException($"{SetupTypeName} not found");
            return type;
        }

        private static Type GetTypeByName(string typeName)
        {
            foreach (var asm in AppDomain.CurrentDomain.GetAssemblies())
            {
                var type = asm.GetType(typeName);
                if (type != null) return type;
            }
            return null;
        }

        private static string CreateEmptyAssetJson(string name)
        {
            return "{\n" +
                $"    \"name\": \"{EscapeJson(name)}\",\n" +
                "    \"maps\": [],\n" +
                "    \"controlSchemes\": []\n" +
                "}";
        }

        private static string EscapeJson(string value)
        {
            return value.Replace("\\", "\\\\").Replace("\"", "\\\"");
        }

        private static void EnsureDirectoryExists(string assetPath)
        {
            var directory = Path.GetDirectoryName(ToFullPath(assetPath));
            if (!string.IsNullOrEmpty(directory) && !Directory.Exists(directory))
                Directory.CreateDirectory(directory);
        }

        private static string ToFullPath(string assetPath)
        {
            if (Path.IsPathRooted(assetPath)) return assetPath;
            var projectRoot = Directory.GetParent(Application.dataPath).FullName;
            return Path.Combine(projectRoot, assetPath.Replace('/', Path.DirectorySeparatorChar));
        }

        private static string NullIfEmpty(string value)
        {
            return string.IsNullOrEmpty(value) ? null : value;
        }

        private static BridgeResponse Success(
            BridgeCommand command, InputSystemParams p, string message, string json)
        {
            var result = Result(p, message, json);
            BridgeLogger.LogInfo($"Input system {p.operation}: {message}");
            return BridgeResponse.Success(command.commandId, command.commandType, JsonUtility.ToJson(result));
        }

        private static InputSystemResult Result(InputSystemParams p, string message, string json)
        {
            return new InputSystemResult
            {
                success = true,
                operation = p.operation,
                assetPath = p.assetPath ?? "",
                actionMap = p.actionMap ?? "",
                actionName = p.actionName ?? "",
                bindingPath = p.bindingPath ?? "",
                controlScheme = p.controlScheme ?? "",
                json = json ?? "",
                message = message,
            };
        }

        private static BridgeResponse Error(
            BridgeCommand command, string operation, string message, InputSystemParams p = null)
        {
            var result = new InputSystemResult
            {
                success = false,
                operation = operation ?? "",
                assetPath = p?.assetPath ?? "",
                actionMap = p?.actionMap ?? "",
                actionName = p?.actionName ?? "",
                bindingPath = p?.bindingPath ?? "",
                controlScheme = p?.controlScheme ?? "",
                message = message,
            };
            return new BridgeResponse
            {
                commandId = command.commandId,
                commandType = command.commandType,
                status = "error",
                timestamp = DateTime.UtcNow.ToString("o"),
                dataJson = JsonUtility.ToJson(result),
                errorMessage = message,
            };
        }
    }
}
