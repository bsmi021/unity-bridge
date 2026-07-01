using System;
using System.Collections.Generic;
using UnityEngine;

namespace BWS.Editor.ClaudeCodeBridge
{
    /// <summary>
    /// Parameters for the package-operation command.
    /// </summary>
    [Serializable]
    public class PackageOperationParams
    {
        public string operation;       // "list", "search", "add", "batch", "pack", etc.
        public string packageName;     // For remove, info, embed
        public string identifier;      // For add (name@version or git URL)
        public string query;           // For search
        public string source;          // For list filter
        public string[] packagesToAdd; // For batch
        public string[] packagesToRemove; // For batch
        public string packageFolder;   // For pack
        public string targetFolder;    // For pack
        public bool confirmClearCache; // For clear-cache
        public bool offlineMode;
        public bool includeIndirectDependencies;
    }

    /// <summary>
    /// Result data for the package-operation command.
    /// </summary>
    [Serializable]
    public class PackageOperationResult
    {
        public string operation;
        public List<PackageInfoData> packages = new List<PackageInfoData>();
        public PackageInfoData package;  // Single package result (add, remove, info, embed)
        public string packageName;
        public string[] packagesToAdd;
        public string[] packagesToRemove;
        public string packageFolder;
        public string targetFolder;
        public string tarballPath;
        public int totalCount;
        public bool success;
        public string message;
    }

    /// <summary>
    /// Serializable package information.
    /// </summary>
    [Serializable]
    public class PackageInfoData
    {
        public string name;
        public string version;
        public string displayName;
        public string description;
        public string source;          // "registry", "git", "embedded", "local"
        public string status;          // "installed", "available"
        public string resolvedPath;
        public List<PackageDependency> dependencies = new List<PackageDependency>();
        public List<string> keywords = new List<string>();
        public string author;
        public string documentationUrl;
    }

    /// <summary>
    /// Package dependency reference.
    /// </summary>
    [Serializable]
    public class PackageDependency
    {
        public string name;
        public string version;
    }
}
