using System;
using System.IO;

namespace BWS.Editor.ClaudeCodeBridge
{
    /// <summary>
    /// Resolves Unity asset paths only after canonical containment under Assets.
    /// </summary>
    internal static class ProjectAssetPath
    {
        private const string AssetPrefix = "Assets/";
        private const string InvalidFileNameCharacters = "<>:\"|?*";

        public static bool TryResolve(
            string assetsDirectory,
            string assetPath,
            out string fullPath,
            out string message)
        {
            fullPath = "";
            message = "";
            if (!TryGetRelativePath(assetPath, out var relativePath))
                return Fail(assetPath, out message);

            try
            {
                var assetsRoot = Path.GetFullPath(assetsDirectory)
                    .TrimEnd(Path.DirectorySeparatorChar, Path.AltDirectorySeparatorChar);
                var relativeSystemPath = relativePath.Replace(
                    '/', Path.DirectorySeparatorChar);
                var candidate = Path.GetFullPath(Path.Combine(assetsRoot, relativeSystemPath));
                var rootPrefix = assetsRoot + Path.DirectorySeparatorChar;
                var comparison = Path.DirectorySeparatorChar == '\\'
                    ? StringComparison.OrdinalIgnoreCase
                    : StringComparison.Ordinal;
                if (!candidate.StartsWith(rootPrefix, comparison))
                    return Fail(assetPath, out message);
                if (ContainsReparsePoint(assetsRoot, relativePath))
                    return Fail(assetPath, out message);

                fullPath = candidate;
                return true;
            }
            catch (Exception ex) when (
                ex is ArgumentException
                || ex is IOException
                || ex is NotSupportedException
                || ex is PathTooLongException
                || ex is UnauthorizedAccessException)
            {
                return Fail(assetPath, out message);
            }
        }

        private static bool ContainsReparsePoint(string assetsRoot, string relativePath)
        {
            var current = assetsRoot;
            foreach (var segment in relativePath.Split('/'))
            {
                current = Path.Combine(current, segment);
                if (!File.Exists(current) && !Directory.Exists(current))
                    break;
                var attributes = File.GetAttributes(current);
                if ((attributes & FileAttributes.ReparsePoint) != 0)
                    return true;
            }
            return false;
        }

        private static bool TryGetRelativePath(string assetPath, out string relativePath)
        {
            relativePath = "";
            if (string.IsNullOrWhiteSpace(assetPath)
                || Path.IsPathRooted(assetPath)
                || assetPath.IndexOf('\\') >= 0
                || !assetPath.StartsWith(AssetPrefix, StringComparison.Ordinal))
            {
                return false;
            }

            relativePath = assetPath.Substring(AssetPrefix.Length);
            if (string.IsNullOrEmpty(relativePath))
                return false;

            var segments = relativePath.Split('/');
            foreach (var segment in segments)
            {
                if (IsMalformedSegment(segment))
                    return false;
            }
            return true;
        }

        private static bool IsMalformedSegment(string segment)
        {
            if (string.IsNullOrEmpty(segment)
                || segment == "."
                || segment == ".."
                || segment.EndsWith(" ", StringComparison.Ordinal)
                || segment.EndsWith(".", StringComparison.Ordinal))
            {
                return true;
            }

            foreach (var character in segment)
            {
                if (character < 32 || InvalidFileNameCharacters.IndexOf(character) >= 0)
                    return true;
            }
            return IsReservedWindowsName(segment);
        }

        private static bool IsReservedWindowsName(string segment)
        {
            var baseName = Path.GetFileNameWithoutExtension(segment).ToUpperInvariant();
            if (baseName == "CON" || baseName == "PRN"
                || baseName == "AUX" || baseName == "NUL")
            {
                return true;
            }

            if (baseName.Length != 4)
                return false;
            var prefix = baseName.Substring(0, 3);
            var suffix = baseName[3];
            return (prefix == "COM" || prefix == "LPT") && suffix >= '1' && suffix <= '9';
        }

        private static bool Fail(string assetPath, out string message)
        {
            message = $"Invalid asset path: '{assetPath}'. "
                + "Must be a canonical path inside the project Assets directory.";
            return false;
        }
    }
}
