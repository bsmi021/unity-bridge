using System;
using System.Collections.Generic;
using System.IO;
using System.Security.Cryptography;
using UnityEditor;
using UnityEngine;

namespace BWS.Editor.ClaudeCodeBridge
{
    public class ScriptEditCommandHandler : ICommandHandler
    {
        public string CommandType => "script-edit";

        public BridgeResponse Execute(BridgeCommand command)
        {
            try
            {
                if (EditorApplication.isCompiling)
                {
                    return BridgeResponse.Error(command.commandId, CommandType,
                        "Unity is compiling. Wait for compilation to finish before editing scripts.");
                }

                var parameters = JsonUtility.FromJson<ScriptEditParams>(
                    command.parametersJson ?? "{}");
                if (parameters == null)
                    parameters = new ScriptEditParams();

                var result = ExecuteEdit(parameters);
                return BridgeResponse.Success(
                    command.commandId, command.commandType, JsonUtility.ToJson(result));
            }
            catch (Exception ex)
            {
                BridgeLogger.LogError($"Script edit error: {ex}");
                return BridgeResponse.Error(command.commandId, command.commandType, ex.ToString());
            }
        }

        private ScriptEditResult ExecuteEdit(ScriptEditParams parameters)
        {
            if (!TryResolveScriptPath(parameters.assetPath, out var fullPath, out var message))
                return Fail(parameters, message);

            var content = File.ReadAllText(fullPath);
            var beforeHash = ComputeSha256(fullPath);
            if (!string.IsNullOrEmpty(parameters.ifMatch) && parameters.ifMatch != beforeHash)
                return Fail(parameters, "Hash precondition failed", beforeHash);

            if (!TryBuildUpdatedContent(parameters, content, out var updated, out message))
                return Fail(parameters, message, beforeHash);

            File.WriteAllText(fullPath, updated);
            AssetDatabase.ImportAsset(parameters.assetPath);
            AssetDatabase.Refresh();

            return new ScriptEditResult
            {
                operation = parameters.operation,
                assetPath = parameters.assetPath,
                success = true,
                message = $"Edited {parameters.assetPath}",
                sha256Before = beforeHash,
                sha256After = ComputeSha256(fullPath),
                imported = true,
                compileRequested = true,
                compileFeedback = "Asset imported; run unity-bridge test compile for compiler results."
            };
        }

        private static bool TryResolveScriptPath(
            string assetPath, out string fullPath, out string message)
        {
            fullPath = "";
            message = "";
            if (string.IsNullOrEmpty(assetPath))
            {
                message = "assetPath is required.";
                return false;
            }
            if (!assetPath.StartsWith("Assets/"))
            {
                message = $"Invalid asset path: '{assetPath}'. Must start with 'Assets/'.";
                return false;
            }
            if (!assetPath.EndsWith(".cs", StringComparison.OrdinalIgnoreCase))
            {
                message = "Script edit only supports .cs assets.";
                return false;
            }

            var projectRoot = Directory.GetParent(Application.dataPath).FullName;
            fullPath = Path.GetFullPath(Path.Combine(
                projectRoot,
                assetPath.Replace('/', Path.DirectorySeparatorChar)));
            if (!fullPath.StartsWith(projectRoot, StringComparison.OrdinalIgnoreCase)
                || !File.Exists(fullPath))
            {
                message = $"Script asset does not exist: {assetPath}";
                return false;
            }
            return true;
        }

        private static bool TryBuildUpdatedContent(
            ScriptEditParams parameters,
            string content,
            out string updated,
            out string message)
        {
            updated = content;
            message = "";
            switch (parameters.operation?.ToLower())
            {
                case "range":
                    return TryApplyRangeEdit(parameters, content, out updated, out message);
                case "anchor":
                    return TryApplyAnchorEdit(parameters, content, out updated, out message);
                default:
                    message = $"Unknown script edit operation: {parameters.operation}";
                    return false;
            }
        }

        private static bool TryApplyRangeEdit(
            ScriptEditParams parameters,
            string content,
            out string updated,
            out string message)
        {
            updated = content;
            message = "";
            var lines = SplitLines(content);
            if (parameters.startLine < 1
                || parameters.endLine < parameters.startLine
                || parameters.endLine > lines.Count)
            {
                message = "Invalid line range.";
                return false;
            }

            var replacementLines = SplitReplacement(parameters.replacement ?? "");
            lines.RemoveRange(parameters.startLine - 1, parameters.endLine - parameters.startLine + 1);
            lines.InsertRange(parameters.startLine - 1, replacementLines);
            updated = string.Join(DetectNewline(content), lines);
            return true;
        }

        private static bool TryApplyAnchorEdit(
            ScriptEditParams parameters,
            string content,
            out string updated,
            out string message)
        {
            updated = content;
            message = "";
            if (string.IsNullOrEmpty(parameters.anchor))
            {
                message = "anchor is required.";
                return false;
            }
            var index = FindOccurrence(content, parameters.anchor, Math.Max(parameters.occurrence, 1));
            if (index < 0)
            {
                message = "Anchor not found.";
                return false;
            }
            updated = content.Remove(index, parameters.anchor.Length)
                .Insert(index, parameters.replacement ?? "");
            return true;
        }

        private static List<string> SplitLines(string content)
        {
            return new List<string>(
                content.Replace("\r\n", "\n").Replace("\r", "\n").Split('\n'));
        }

        private static List<string> SplitReplacement(string replacement)
        {
            if (replacement.Length == 0)
                return new List<string>();
            return SplitLines(replacement);
        }

        private static string DetectNewline(string content)
        {
            return content.Contains("\r\n") ? "\r\n" : "\n";
        }

        private static int FindOccurrence(string content, string anchor, int occurrence)
        {
            var index = -1;
            var start = 0;
            for (var i = 0; i < occurrence; i++)
            {
                index = content.IndexOf(anchor, start, StringComparison.Ordinal);
                if (index < 0)
                    return -1;
                start = index + anchor.Length;
            }
            return index;
        }

        private static ScriptEditResult Fail(
            ScriptEditParams parameters, string message, string beforeHash = "")
        {
            return new ScriptEditResult
            {
                operation = parameters?.operation,
                assetPath = parameters?.assetPath,
                success = false,
                message = message,
                sha256Before = beforeHash,
                imported = false,
                compileRequested = false,
                compileFeedback = ""
            };
        }

        private static string ComputeSha256(string fullPath)
        {
            using (var sha = SHA256.Create())
            using (var stream = File.OpenRead(fullPath))
            {
                var hash = sha.ComputeHash(stream);
                return BitConverter.ToString(hash).Replace("-", "").ToLowerInvariant();
            }
        }
    }
}
