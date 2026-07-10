using System;
using System.IO;

namespace BWS.Editor.ClaudeCodeBridge
{
    /// <summary>
    /// Preserves an asset file and its metadata until a file mutation commits.
    /// </summary>
    internal sealed class AssetFileMutationScope : IDisposable
    {
        private readonly string _destinationPath;
        private readonly string _metadataPath;
        private readonly string _destinationBackupPath;
        private readonly string _metadataBackupPath;
        private bool _completed;

        public bool DestinationExisted { get; }
        public bool MetadataExisted { get; }

        private AssetFileMutationScope(
            string destinationPath,
            bool destinationExisted,
            bool metadataExisted,
            string destinationBackupPath,
            string metadataBackupPath)
        {
            _destinationPath = destinationPath;
            _metadataPath = destinationPath + ".meta";
            DestinationExisted = destinationExisted;
            MetadataExisted = metadataExisted;
            _destinationBackupPath = destinationBackupPath;
            _metadataBackupPath = metadataBackupPath;
        }

        public static bool TryBegin(
            string destinationPath,
            bool overwrite,
            out AssetFileMutationScope scope,
            out string message)
        {
            scope = null;
            message = "";
            if (Directory.Exists(destinationPath))
            {
                message = $"Destination is a directory: {destinationPath}";
                return false;
            }

            var destinationExisted = File.Exists(destinationPath);
            var metadataPath = destinationPath + ".meta";
            var metadataExisted = File.Exists(metadataPath);
            if ((destinationExisted || metadataExisted) && !overwrite)
            {
                message = "Destination already exists. Set overwrite=true to replace it explicitly.";
                return false;
            }

            return TryCreateScope(
                destinationPath, destinationExisted, metadataExisted, out scope, out message);
        }

        public void CopyFrom(string sourcePath)
        {
            File.Copy(sourcePath, _destinationPath, DestinationExisted);
        }

        public void Commit()
        {
            _completed = true;
            DeleteBackups();
        }

        public void Rollback()
        {
            if (_completed)
                return;

            RestorePath(_destinationPath, _destinationBackupPath, DestinationExisted);
            RestorePath(_metadataPath, _metadataBackupPath, MetadataExisted);
            _completed = true;
            DeleteBackups();
        }

        public void Dispose()
        {
            if (!_completed)
                Rollback();
            DeleteBackups();
        }

        private static bool TryCreateScope(
            string destinationPath,
            bool destinationExisted,
            bool metadataExisted,
            out AssetFileMutationScope scope,
            out string message)
        {
            string destinationBackup = null;
            string metadataBackup = null;
            try
            {
                if (destinationExisted)
                    destinationBackup = CreateBackup(destinationPath);
                if (metadataExisted)
                    metadataBackup = CreateBackup(destinationPath + ".meta");
                scope = new AssetFileMutationScope(
                    destinationPath,
                    destinationExisted,
                    metadataExisted,
                    destinationBackup,
                    metadataBackup);
                message = "";
                return true;
            }
            catch (Exception ex)
            {
                TryDelete(destinationBackup);
                TryDelete(metadataBackup);
                scope = null;
                message = $"Could not preserve the existing destination: {ex.Message}";
                return false;
            }
        }

        private static string CreateBackup(string sourcePath)
        {
            var backupPath = Path.Combine(
                Path.GetTempPath(), $"unity-bridge-{Guid.NewGuid():N}.bak");
            File.Copy(sourcePath, backupPath, false);
            return backupPath;
        }

        private static void RestorePath(string path, string backupPath, bool existed)
        {
            if (existed)
                File.Copy(backupPath, path, true);
            else if (File.Exists(path))
                File.Delete(path);
        }

        private void DeleteBackups()
        {
            TryDelete(_destinationBackupPath);
            TryDelete(_metadataBackupPath);
        }

        private static void TryDelete(string path)
        {
            try
            {
                if (!string.IsNullOrEmpty(path) && File.Exists(path))
                    File.Delete(path);
            }
            catch
            {
                // A temporary backup cleanup failure must not corrupt the destination.
            }
        }
    }
}
