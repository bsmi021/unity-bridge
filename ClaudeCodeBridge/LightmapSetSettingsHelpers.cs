using System;
using UnityEditor;
using UnityEngine;

namespace BWS.Editor.ClaudeCodeBridge
{
    /// <summary>
    /// Helper to apply writable lightmap settings changes.
    /// Extracted to keep LightmapOperationCommandHandler under 500 LOC.
    /// </summary>
    public static class LightmapSetSettingsHelpers
    {
        public static void Apply(
            LightmapSetSettingsParams p, LightingSettings settings)
        {
            if (p.setBakedGI)
                settings.bakedGI = p.bakedGI;

            if (p.setRealtimeGI)
                settings.realtimeGI = p.realtimeGI;

            if (p.setLightmapper)
            {
                settings.lightmapper = (LightingSettings.Lightmapper)
                    Enum.Parse(typeof(LightingSettings.Lightmapper),
                        p.lightmapper, true);
            }

            if (p.setBounceBoost)
                settings.albedoBoost = p.bounceBoost;

            if (p.setIndirectIntensity)
                settings.indirectScale = p.indirectIntensity;

            if (p.setDirectSampleCount)
                settings.directSampleCount = p.directSampleCount;

            if (p.setIndirectSampleCount)
                settings.indirectSampleCount = p.indirectSampleCount;

            if (p.setLightmapMaxSize)
                settings.lightmapMaxSize = p.lightmapMaxSize;

            if (p.setLightmapResolution)
                settings.lightmapResolution = p.lightmapResolution;

            if (p.setMaxBounces)
                settings.maxBounces = p.maxBounces;

            if (p.setCompressLightmaps)
                settings.compressLightmaps = p.compressLightmaps;

            if (p.setAmbientOcclusion)
                settings.ao = p.ambientOcclusion;

            if (p.setAoMaxDistance)
                settings.aoMaxDistance = p.aoMaxDistance;

            EditorUtility.SetDirty(settings);
        }
    }

    // -----------------------------------------------------------------
    // Models for set-settings
    // -----------------------------------------------------------------

    [Serializable]
    public class LightmapSetSettingsParams
    {
        public string operation;

        public bool bakedGI;
        public bool setBakedGI;
        public bool realtimeGI;
        public bool setRealtimeGI;
        public string lightmapper;
        public bool setLightmapper;
        public float bounceBoost;
        public bool setBounceBoost;
        public float indirectIntensity;
        public bool setIndirectIntensity;
        public int directSampleCount;
        public bool setDirectSampleCount;
        public int indirectSampleCount;
        public bool setIndirectSampleCount;
        public int lightmapMaxSize;
        public bool setLightmapMaxSize;
        public float lightmapResolution;
        public bool setLightmapResolution;
        public int maxBounces;
        public bool setMaxBounces;
        public bool compressLightmaps;
        public bool setCompressLightmaps;
        public bool ambientOcclusion;
        public bool setAmbientOcclusion;
        public float aoMaxDistance;
        public bool setAoMaxDistance;
    }
}
