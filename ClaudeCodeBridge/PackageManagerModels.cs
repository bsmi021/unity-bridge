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
        public string operation;       // "list", "search", "search-all", "add", "remove", "info", "embed", "resolve"
        public string packageName;     // For remove, info, embed
        public string identifier;      // For add (name@version or git URL)
        public string query;           // For search
        public string source;          // For list filter
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
