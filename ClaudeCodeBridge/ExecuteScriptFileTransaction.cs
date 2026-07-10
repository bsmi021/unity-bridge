using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Security.Cryptography;

namespace BWS.Editor.ClaudeCodeBridge
{
    internal sealed class ExecuteScriptFileTransaction : IDisposable
    {
        private readonly string _assetsDirectory;
        private readonly HashSet<string> _declaredPaths;
        private readonly List<AssetFileMutationScope> _backups;
        private readonly Dictionary<string, FileSnapshot> _before;
        private bool _completed;

        private ExecuteScriptFileTransaction(
            string assetsDirectory,
            HashSet<string> declaredPaths,
            List<AssetFileMutationScope> backups,
            Dictionary<string, FileSnapshot> before)
        {
            _assetsDirectory = assetsDirectory;
            _declaredPaths = declaredPaths;
            _backups = backups;
            _before = before;
        }

        public static bool TryBegin(
            string assetsDirectory,
            IEnumerable<string> assetPaths,
            out ExecuteScriptFileTransaction transaction,
            out string message)
        {
            transaction = null;
            if (!TryResolveTargets(
                assetsDirectory, assetPaths, out var declared, out var targets, out message))
            {
                return false;
            }
            if (!TrySnapshot(assetsDirectory, out var before, out message))
                return false;
            if (!TryBackupTargets(targets, out var backups, out message))
                return false;
            transaction = new ExecuteScriptFileTransaction(
                assetsDirectory, declared, backups, before);
            return true;
        }

        public bool TryCaptureChanges(
            out List<ExecuteScriptFileChange> changes, out string message)
        {
            changes = new List<ExecuteScriptFileChange>();
            if (!TrySnapshot(_assetsDirectory, out var after, out message))
                return false;
            changes = FindChanges(_assetsDirectory, _before, after);
            return true;
        }

        public List<string> FindUndeclared(IEnumerable<ExecuteScriptFileChange> changes)
        {
            return (changes ?? Array.Empty<ExecuteScriptFileChange>())
                .Select(change => change.path)
                .Where(path => !_declaredPaths.Contains(path))
                .OrderBy(path => path, StringComparer.Ordinal)
                .ToList();
        }

        public void Commit()
        {
            foreach (var backup in _backups)
                backup.Commit();
            _completed = true;
        }

        public bool RollbackAndVerify(out string message)
        {
            var errors = new List<string>();
            for (var index = _backups.Count - 1; index >= 0; index--)
            {
                try
                {
                    _backups[index].Rollback();
                }
                catch (Exception ex)
                {
                    errors.Add($"Declared file rollback failed: {ex.Message}");
                }
            }
            if (!TrySnapshot(_assetsDirectory, out var after, out var snapshotError))
                errors.Add(snapshotError);
            else if (FindChanges(_assetsDirectory, _before, after).Count > 0)
                errors.Add("Post-rollback project file verification failed.");
            _completed = true;
            message = string.Join(" ", errors);
            return errors.Count == 0;
        }

        public void Dispose()
        {
            if (!_completed)
                RollbackAndVerify(out _);
        }

        private static bool TryResolveTargets(
            string assetsDirectory,
            IEnumerable<string> assetPaths,
            out HashSet<string> declared,
            out List<string> targets,
            out string message)
        {
            declared = new HashSet<string>(AssetPathComparer());
            targets = new List<string>();
            var fullTargets = new HashSet<string>(FilePathComparer());
            foreach (var assetPath in assetPaths ?? Array.Empty<string>())
            {
                if (!ProjectAssetPath.TryResolve(
                    assetsDirectory, assetPath, out var fullPath, out message))
                {
                    return false;
                }
                if (!fullTargets.Add(fullPath))
                {
                    message = $"Duplicate declared file target: {assetPath}";
                    return false;
                }
                declared.Add(assetPath);
                declared.Add(assetPath + ".meta");
                targets.Add(fullPath);
            }
            message = "";
            return true;
        }

        private static bool TryBackupTargets(
            IEnumerable<string> targets,
            out List<AssetFileMutationScope> backups,
            out string message)
        {
            backups = new List<AssetFileMutationScope>();
            foreach (var target in targets)
            {
                if (AssetFileMutationScope.TryBegin(
                    target, true, out var backup, out message))
                {
                    backups.Add(backup);
                    continue;
                }
                foreach (var created in backups)
                    created.Dispose();
                backups.Clear();
                return false;
            }
            message = "";
            return true;
        }

        private static bool TrySnapshot(
            string assetsDirectory,
            out Dictionary<string, FileSnapshot> snapshot,
            out string message)
        {
            snapshot = NewSnapshotDictionary();
            try
            {
                foreach (var file in EnumerateProjectFiles(assetsDirectory))
                    snapshot[Path.GetFullPath(file)] = FileSnapshot.Create(file);
                message = "";
                return true;
            }
            catch (Exception ex)
            {
                snapshot.Clear();
                message = $"Could not snapshot project files: {ex.Message}";
                return false;
            }
        }

        private static IEnumerable<string> EnumerateProjectFiles(string assetsDirectory)
        {
            var pending = new Stack<string>();
            pending.Push(assetsDirectory);
            while (pending.Count > 0)
            {
                var directory = pending.Pop();
                foreach (var file in Directory.EnumerateFiles(directory))
                    yield return file;
                foreach (var child in Directory.EnumerateDirectories(directory))
                {
                    var attributes = File.GetAttributes(child);
                    if ((attributes & FileAttributes.ReparsePoint) == 0)
                        pending.Push(child);
                }
            }
        }

        private static List<ExecuteScriptFileChange> FindChanges(
            string assetsDirectory,
            Dictionary<string, FileSnapshot> before,
            Dictionary<string, FileSnapshot> after)
        {
            var changes = new List<ExecuteScriptFileChange>();
            foreach (var pair in after)
            {
                if (!before.TryGetValue(pair.Key, out var previous))
                    changes.Add(NewChange(assetsDirectory, pair.Key, "created"));
                else if (!previous.Equals(pair.Value))
                    changes.Add(NewChange(assetsDirectory, pair.Key, "modified"));
            }
            foreach (var path in before.Keys.Where(path => !after.ContainsKey(path)))
                changes.Add(NewChange(assetsDirectory, path, "deleted"));
            return changes.OrderBy(change => change.path, StringComparer.Ordinal).ToList();
        }

        private static ExecuteScriptFileChange NewChange(
            string assetsDirectory, string fullPath, string change)
        {
            var relative = Path.GetRelativePath(assetsDirectory, fullPath)
                .Replace(Path.DirectorySeparatorChar, '/');
            return new ExecuteScriptFileChange
            {
                path = $"Assets/{relative}",
                change = change,
            };
        }

        private static Dictionary<string, FileSnapshot> NewSnapshotDictionary()
        {
            return new Dictionary<string, FileSnapshot>(FilePathComparer());
        }

        private static StringComparer FilePathComparer()
        {
            return Path.DirectorySeparatorChar == '\\'
                ? StringComparer.OrdinalIgnoreCase
                : StringComparer.Ordinal;
        }

        private static StringComparer AssetPathComparer()
        {
            return Path.DirectorySeparatorChar == '\\'
                ? StringComparer.OrdinalIgnoreCase
                : StringComparer.Ordinal;
        }

        private readonly struct FileSnapshot : IEquatable<FileSnapshot>
        {
            private readonly long _length;
            private readonly string _hash;
            private readonly bool _reparsePoint;

            private FileSnapshot(long length, string hash, bool reparsePoint)
            {
                _length = length;
                _hash = hash;
                _reparsePoint = reparsePoint;
            }

            public static FileSnapshot Create(string path)
            {
                var info = new FileInfo(path);
                var reparse = (info.Attributes & FileAttributes.ReparsePoint) != 0;
                if (reparse)
                    return new FileSnapshot(info.Length, "", true);
                using (var stream = File.OpenRead(path))
                using (var hasher = SHA256.Create())
                {
                    return new FileSnapshot(
                        info.Length, Convert.ToBase64String(hasher.ComputeHash(stream)), false);
                }
            }

            public bool Equals(FileSnapshot other)
            {
                return _length == other._length
                    && _hash == other._hash
                    && _reparsePoint == other._reparsePoint;
            }
        }
    }
}
