using System;
using System.Collections.Generic;
using UnityEditor;
using UnityEditor.Build;
using UnityEngine;

namespace BWS.Editor.ClaudeCodeBridge
{
    /// <summary>
    /// Builds getter/setter dictionaries for PlayerSettings properties.
    /// Extracted from PlayerSettingsCommandHandler to stay under 500 LOC.
    /// Covers 28 properties across core, display, rendering, scripting,
    /// Android, iOS, and WebGL platforms.
    /// </summary>
    public static class PlayerSettingsPropertyMap
    {
        public static Dictionary<string, Func<string>> BuildGetters()
        {
            return new Dictionary<string, Func<string>>(StringComparer.OrdinalIgnoreCase)
            {
                // Core identity
                { "companyName", () => PlayerSettings.companyName },
                { "productName", () => PlayerSettings.productName },
                { "bundleVersion", () => PlayerSettings.bundleVersion },
                { "applicationIdentifier", () => PlayerSettings.applicationIdentifier },
                // Display
                { "defaultIsFullScreen", () =>
                    PlayerSettings.defaultIsFullScreen.ToString() },
                { "runInBackground", () =>
                    PlayerSettings.runInBackground.ToString() },
                { "defaultScreenWidth", () =>
                    PlayerSettings.defaultScreenWidth.ToString() },
                { "defaultScreenHeight", () =>
                    PlayerSettings.defaultScreenHeight.ToString() },
                { "fullScreenMode", () =>
                    PlayerSettings.fullScreenMode.ToString() },
                // Rendering
                { "colorSpace", () => PlayerSettings.colorSpace.ToString() },
                { "gpuSkinning", () => PlayerSettings.gpuSkinning.ToString() },
                // Scripting
                { "scriptingBackend", () => PlayerSettings.GetScriptingBackend(
                    NamedBuildTarget.Standalone).ToString() },
                { "apiCompatibilityLevel", () =>
                    PlayerSettings.GetApiCompatibilityLevel(
                        NamedBuildTarget.Standalone).ToString() },
                { "allowUnsafeCode", () =>
                    PlayerSettings.allowUnsafeCode.ToString() },
                { "il2CppCompilerConfiguration", () =>
                    PlayerSettings.GetIl2CppCompilerConfiguration(
                        NamedBuildTarget.Standalone).ToString() },
                // Splash
                { "showSplashScreen", () =>
                    PlayerSettings.SplashScreen.show.ToString() },
                // GC
                { "incrementalGC", () =>
                    PlayerSettings.gcIncremental.ToString() },
                // Android
                { "androidMinSdkVersion", () =>
                    PlayerSettings.Android.minSdkVersion.ToString() },
                { "androidTargetSdkVersion", () =>
                    PlayerSettings.Android.targetSdkVersion.ToString() },
                { "targetArchitecture", () =>
                    PlayerSettings.Android.targetArchitectures.ToString() },
                // iOS
                { "cameraUsageDescription", () =>
                    PlayerSettings.iOS.cameraUsageDescription ?? "" },
                { "locationUsageDescription", () =>
                    PlayerSettings.iOS.locationUsageDescription ?? "" },
                { "iOSTargetDevice", () =>
                    PlayerSettings.iOS.targetDevice.ToString() },
                // WebGL
                { "webGLMemorySize", () =>
                    PlayerSettings.WebGL.memorySize.ToString() },
                { "webGLCompressionFormat", () =>
                    PlayerSettings.WebGL.compressionFormat.ToString() },
            };
        }

        public static Dictionary<string, Action<string>> BuildSetters()
        {
            return new Dictionary<string, Action<string>>(StringComparer.OrdinalIgnoreCase)
            {
                // Core identity
                { "companyName", v => PlayerSettings.companyName = v },
                { "productName", v => PlayerSettings.productName = v },
                { "bundleVersion", v => PlayerSettings.bundleVersion = v },
                { "applicationIdentifier", v =>
                    PlayerSettings.applicationIdentifier = v },
                // Display
                { "defaultIsFullScreen", v =>
                    PlayerSettings.defaultIsFullScreen = bool.Parse(v) },
                { "runInBackground", v =>
                    PlayerSettings.runInBackground = bool.Parse(v) },
                { "defaultScreenWidth", v =>
                    PlayerSettings.defaultScreenWidth = int.Parse(v) },
                { "defaultScreenHeight", v =>
                    PlayerSettings.defaultScreenHeight = int.Parse(v) },
                { "fullScreenMode", v => PlayerSettings.fullScreenMode =
                    (FullScreenMode)Enum.Parse(typeof(FullScreenMode), v, true) },
                // Rendering
                { "colorSpace", v => PlayerSettings.colorSpace =
                    (ColorSpace)Enum.Parse(typeof(ColorSpace), v, true) },
                { "gpuSkinning", v =>
                    PlayerSettings.gpuSkinning = bool.Parse(v) },
                // Scripting
                { "scriptingBackend", v => PlayerSettings.SetScriptingBackend(
                    NamedBuildTarget.Standalone,
                    (ScriptingImplementation)Enum.Parse(
                        typeof(ScriptingImplementation), v, true)) },
                { "apiCompatibilityLevel", v =>
                    PlayerSettings.SetApiCompatibilityLevel(
                        NamedBuildTarget.Standalone,
                        (ApiCompatibilityLevel)Enum.Parse(
                            typeof(ApiCompatibilityLevel), v, true)) },
                { "allowUnsafeCode", v =>
                    PlayerSettings.allowUnsafeCode = bool.Parse(v) },
                { "il2CppCompilerConfiguration", v =>
                    PlayerSettings.SetIl2CppCompilerConfiguration(
                        NamedBuildTarget.Standalone,
                        (Il2CppCompilerConfiguration)Enum.Parse(
                            typeof(Il2CppCompilerConfiguration), v, true)) },
                // Splash
                { "showSplashScreen", v =>
                    PlayerSettings.SplashScreen.show = bool.Parse(v) },
                // GC
                { "incrementalGC", v =>
                    PlayerSettings.gcIncremental = bool.Parse(v) },
                // Android
                { "androidMinSdkVersion", v =>
                    PlayerSettings.Android.minSdkVersion =
                        (AndroidSdkVersions)Enum.Parse(
                            typeof(AndroidSdkVersions), v, true) },
                { "androidTargetSdkVersion", v =>
                    PlayerSettings.Android.targetSdkVersion =
                        (AndroidSdkVersions)Enum.Parse(
                            typeof(AndroidSdkVersions), v, true) },
                { "targetArchitecture", v =>
                    PlayerSettings.Android.targetArchitectures =
                        (AndroidArchitecture)Enum.Parse(
                            typeof(AndroidArchitecture), v, true) },
                // iOS
                { "cameraUsageDescription", v =>
                    PlayerSettings.iOS.cameraUsageDescription = v },
                { "locationUsageDescription", v =>
                    PlayerSettings.iOS.locationUsageDescription = v },
                { "iOSTargetDevice", v => PlayerSettings.iOS.targetDevice =
                    (UnityEditor.iOSTargetDevice)Enum.Parse(
                        typeof(UnityEditor.iOSTargetDevice), v, true) },
                // WebGL
                { "webGLMemorySize", v =>
                    PlayerSettings.WebGL.memorySize = int.Parse(v) },
                { "webGLCompressionFormat", v =>
                    PlayerSettings.WebGL.compressionFormat =
                        (WebGLCompressionFormat)Enum.Parse(
                            typeof(WebGLCompressionFormat), v, true) },
            };
        }
    }
}
