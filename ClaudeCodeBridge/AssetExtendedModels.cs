using System;
using System.Collections.Generic;
using UnityEngine;

namespace BWS.Editor.ClaudeCodeBridge
{
    /// <summary>
    /// Parameters for the asset-extended-operation command.
    /// Extends AssetDatabase operations with create, delete, copy, move,
    /// GUID conversion, folder management, and package export/import.
    /// </summary>
    [Serializable]
    public class AssetExtendedOperationParams
    {
        public string operation;
        public string assetPath;
        public string sourcePath;
        public string destinationPath;
        public bool overwrite = false;
        public string assetType;
        public bool useTrash = false;
        public bool recursive = true;
        public string input;               // For guid operation
        public string folderPath;
        public List<string> assetPaths = new List<string>();  // For export
        public string outputPath;
        public bool includeDependencies = true;
        public bool interactive = false;
        public string packagePath;         // For import-package
        public int renderTextureWidth;     // For RenderTexture creation
        public int renderTextureHeight;    // For RenderTexture creation
        public int renderTextureDepth;     // For RenderTexture creation
        public string initialContent;      // For text-based asset creation
        public string reserializeMode;     // For reserialize: "assets", "metadata", or null
    }

    /// <summary>
    /// Result data for the asset-extended-operation command.
    /// </summary>
    [Serializable]
    public class AssetExtendedOperationResult
    {
        public string operation;
        public AssetInfo asset;
        public List<AssetInfo> dependencies = new List<AssetInfo>();
        public string assetPath;
        public string sourcePath;
        public string destinationPath;
        public string folderPath;
        public List<string> subfolders = new List<string>();
        public string path;                // For guid result
        public string guid;                // For guid result
        public string sha256;              // For hash result
        public string importerType;        // For import-model result
        public string input;               // For guid input echo
        public string outputPath;
        public int exportedAssets;
        public long fileSizeBytes;
        public bool usedTrash;
        public string errorDetail;         // Raw return value from MoveAsset()
        public int totalCount;
        public bool success;
        public string message;
    }
}
