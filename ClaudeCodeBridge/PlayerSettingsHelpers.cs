using UnityEditor;
using UnityEditor.Build;
using UnityEngine;

namespace BWS.Editor.ClaudeCodeBridge
{
    /// <summary>
    /// Helper methods for PlayerSettingsCommandHandler.
    /// Extracted to keep the main handler under 500 LOC.
    /// </summary>
    public static class PlayerSettingsHelpers
    {
        /// <summary>
        /// Build a complete snapshot of all supported PlayerSettings properties.
        /// </summary>
        public static PlayerSettingsData BuildSettingsSnapshot()
        {
            return new PlayerSettingsData
            {
                // Core identity
                companyName = PlayerSettings.companyName,
                productName = PlayerSettings.productName,
                bundleVersion = PlayerSettings.bundleVersion,
                applicationIdentifier = PlayerSettings.applicationIdentifier,
                // Display
                defaultIsFullScreen = PlayerSettings.defaultIsFullScreen,
                runInBackground = PlayerSettings.runInBackground,
                defaultScreenWidth = PlayerSettings.defaultScreenWidth,
                defaultScreenHeight = PlayerSettings.defaultScreenHeight,
                fullScreenMode = PlayerSettings.fullScreenMode.ToString(),
                // Rendering
                colorSpace = PlayerSettings.colorSpace.ToString(),
                gpuSkinning = PlayerSettings.gpuSkinning,
                // Scripting
                scriptingBackend = PlayerSettings.GetScriptingBackend(
                    NamedBuildTarget.Standalone).ToString(),
                apiCompatibilityLevel = PlayerSettings.GetApiCompatibilityLevel(
                    NamedBuildTarget.Standalone).ToString(),
                allowUnsafeCode = PlayerSettings.allowUnsafeCode,
                il2CppCompilerConfiguration = PlayerSettings.GetIl2CppCompilerConfiguration(
                    NamedBuildTarget.Standalone).ToString(),
                // Splash
                showSplashScreen = PlayerSettings.SplashScreen.show,
                // GC
                incrementalGC = PlayerSettings.gcIncremental,
                // Android
                androidMinSdkVersion = PlayerSettings.Android.minSdkVersion.ToString(),
                androidTargetSdkVersion =
                    PlayerSettings.Android.targetSdkVersion.ToString(),
                targetArchitecture =
                    PlayerSettings.Android.targetArchitectures.ToString(),
                // iOS
                cameraUsageDescription =
                    PlayerSettings.iOS.cameraUsageDescription ?? "",
                locationUsageDescription =
                    PlayerSettings.iOS.locationUsageDescription ?? "",
                iOSTargetDevice = PlayerSettings.iOS.targetDevice.ToString(),
                // WebGL
                webGLMemorySize = PlayerSettings.WebGL.memorySize,
                webGLCompressionFormat =
                    PlayerSettings.WebGL.compressionFormat.ToString(),
            };
        }
    }
}
