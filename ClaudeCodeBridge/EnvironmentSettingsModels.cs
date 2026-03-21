using System;

namespace BWS.Editor.ClaudeCodeBridge
{
    [Serializable]
    public class EnvironmentSettingsParams
    {
        public string operation;

        // Skybox
        public string skyboxMaterial;

        // Ambient
        public string ambientMode;
        public bool setAmbientMode;
        public float ambientIntensity;
        public bool setAmbientIntensity;
        public float ambientLightR;
        public float ambientLightG;
        public float ambientLightB;
        public bool setAmbientLight;
        public float ambientSkyColorR;
        public float ambientSkyColorG;
        public float ambientSkyColorB;
        public bool setAmbientSkyColor;
        public float ambientEquatorColorR;
        public float ambientEquatorColorG;
        public float ambientEquatorColorB;
        public bool setAmbientEquatorColor;
        public float ambientGroundColorR;
        public float ambientGroundColorG;
        public float ambientGroundColorB;
        public bool setAmbientGroundColor;

        // Fog
        public bool fog;
        public bool setFog;
        public string fogMode;
        public bool setFogMode;
        public float fogColorR;
        public float fogColorG;
        public float fogColorB;
        public bool setFogColor;
        public float fogDensity;
        public bool setFogDensity;
        public float fogStartDistance;
        public bool setFogStartDistance;
        public float fogEndDistance;
        public bool setFogEndDistance;

        // Reflection
        public string defaultReflectionMode;
        public bool setDefaultReflectionMode;
        public int defaultReflectionResolution;
        public bool setDefaultReflectionResolution;
        public int reflectionBounces;
        public bool setReflectionBounces;
        public float reflectionIntensity;
        public bool setReflectionIntensity;
    }

    [Serializable]
    public class EnvironmentSettingsResult
    {
        public bool success;
        public string operation;
        public string message;

        // Skybox
        public string skyboxMaterial;

        // Ambient
        public string ambientMode;
        public float ambientIntensity;
        public float ambientLightR;
        public float ambientLightG;
        public float ambientLightB;
        public float ambientSkyColorR;
        public float ambientSkyColorG;
        public float ambientSkyColorB;
        public float ambientEquatorColorR;
        public float ambientEquatorColorG;
        public float ambientEquatorColorB;
        public float ambientGroundColorR;
        public float ambientGroundColorG;
        public float ambientGroundColorB;

        // Fog
        public bool fog;
        public string fogMode;
        public float fogColorR;
        public float fogColorG;
        public float fogColorB;
        public float fogDensity;
        public float fogStartDistance;
        public float fogEndDistance;

        // Reflection
        public string defaultReflectionMode;
        public int defaultReflectionResolution;
        public int reflectionBounces;
        public float reflectionIntensity;
    }
}
