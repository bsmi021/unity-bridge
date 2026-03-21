using System;
using UnityEditor;
using UnityEngine;
using UnityEngine.Rendering;

namespace BWS.Editor.ClaudeCodeBridge
{
    /// <summary>
    /// Helpers for applying environment settings changes.
    /// Extracted from EnvironmentSettingsCommandHandler to stay under 500 LOC.
    /// </summary>
    public static class EnvironmentSetHelpers
    {
        public static void Apply(EnvironmentSettingsParams p)
        {
            ApplySkybox(p);
            ApplyAmbient(p);
            ApplyFog(p);
            ApplyReflection(p);
        }

        private static void ApplySkybox(EnvironmentSettingsParams p)
        {
            if (!string.IsNullOrEmpty(p.skyboxMaterial))
            {
                if (p.skyboxMaterial == "none")
                {
                    RenderSettings.skybox = null;
                }
                else
                {
                    var mat = AssetDatabase.LoadAssetAtPath<Material>(
                        p.skyboxMaterial);
                    if (mat is not null)
                        RenderSettings.skybox = mat;
                }
            }
        }

        private static void ApplyAmbient(EnvironmentSettingsParams p)
        {
            if (p.setAmbientMode)
            {
                RenderSettings.ambientMode =
                    (AmbientMode)Enum.Parse(
                        typeof(AmbientMode), p.ambientMode, true);
            }

            if (p.setAmbientIntensity)
                RenderSettings.ambientIntensity = p.ambientIntensity;

            if (p.setAmbientLight)
            {
                RenderSettings.ambientLight = new Color(
                    p.ambientLightR, p.ambientLightG, p.ambientLightB);
            }

            if (p.setAmbientSkyColor)
            {
                RenderSettings.ambientSkyColor = new Color(
                    p.ambientSkyColorR, p.ambientSkyColorG,
                    p.ambientSkyColorB);
            }

            if (p.setAmbientEquatorColor)
            {
                RenderSettings.ambientEquatorColor = new Color(
                    p.ambientEquatorColorR, p.ambientEquatorColorG,
                    p.ambientEquatorColorB);
            }

            if (p.setAmbientGroundColor)
            {
                RenderSettings.ambientGroundColor = new Color(
                    p.ambientGroundColorR, p.ambientGroundColorG,
                    p.ambientGroundColorB);
            }
        }

        private static void ApplyFog(EnvironmentSettingsParams p)
        {
            if (p.setFog)
                RenderSettings.fog = p.fog;

            if (p.setFogMode)
            {
                RenderSettings.fogMode =
                    (FogMode)Enum.Parse(typeof(FogMode), p.fogMode, true);
            }

            if (p.setFogColor)
            {
                RenderSettings.fogColor = new Color(
                    p.fogColorR, p.fogColorG, p.fogColorB);
            }

            if (p.setFogDensity)
                RenderSettings.fogDensity = p.fogDensity;

            if (p.setFogStartDistance)
                RenderSettings.fogStartDistance = p.fogStartDistance;

            if (p.setFogEndDistance)
                RenderSettings.fogEndDistance = p.fogEndDistance;
        }

        private static void ApplyReflection(EnvironmentSettingsParams p)
        {
            if (p.setDefaultReflectionMode)
            {
                RenderSettings.defaultReflectionMode =
                    (DefaultReflectionMode)Enum.Parse(
                        typeof(DefaultReflectionMode),
                        p.defaultReflectionMode, true);
            }

            if (p.setDefaultReflectionResolution)
            {
                RenderSettings.defaultReflectionResolution =
                    p.defaultReflectionResolution;
            }

            if (p.setReflectionBounces)
                RenderSettings.reflectionBounces = p.reflectionBounces;

            if (p.setReflectionIntensity)
                RenderSettings.reflectionIntensity = p.reflectionIntensity;
        }
    }
}
