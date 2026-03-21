using System;
using System.Collections.Generic;
using UnityEditor;
using UnityEngine;

namespace BWS.Editor.ClaudeCodeBridge
{
    /// <summary>
    /// Command handler for animation clip operations.
    ///
    /// SUPPORTED OPERATIONS:
    /// 1. "create"         - Create a new AnimationClip asset
    /// 2. "get-info"       - Get clip info (length, frameRate, wrapMode, etc.)
    /// 3. "set-curve"      - Set an animation curve on a clip
    /// 4. "get-curves"     - List all curve bindings on a clip
    /// 5. "add-event"      - Add an animation event to a clip
    /// 6. "set-properties" - Set clip properties (loop, wrapMode, frameRate)
    /// </summary>
    public class AnimationClipCommandHandler : ICommandHandler
    {
        public string CommandType => "animation-clip";

        public BridgeResponse Execute(BridgeCommand command)
        {
            try
            {
                if (EditorApplication.isCompiling)
                {
                    return BridgeResponse.Error(command.commandId, command.commandType,
                        "Cannot perform animation clip operations while scripts are compiling.");
                }

                var parameters = JsonUtility.FromJson<AnimationClipParams>(
                    command.parametersJson ?? "{}");
                if (parameters == null)
                    parameters = new AnimationClipParams();

                BridgeLogger.LogDebug($"Executing animation-clip operation: {parameters.operation}");

                switch (parameters.operation?.ToLower())
                {
                    case "create":
                        return ExecuteCreate(command, parameters);
                    case "get-info":
                        return ExecuteGetInfo(command, parameters);
                    case "set-curve":
                        return ExecuteSetCurve(command, parameters);
                    case "get-curves":
                        return ExecuteGetCurves(command, parameters);
                    case "add-event":
                        return ExecuteAddEvent(command, parameters);
                    case "set-properties":
                        return ExecuteSetProperties(command, parameters);
                    default:
                        return BridgeResponse.Error(
                            command.commandId, command.commandType,
                            $"Unknown animation-clip operation: {parameters.operation}. "
                            + "Supported: create, get-info, set-curve, get-curves, "
                            + "add-event, set-properties");
                }
            }
            catch (Exception ex)
            {
                BridgeLogger.LogError($"AnimationClip operation error: {ex}");
                return BridgeResponse.Error(command.commandId, command.commandType, ex.ToString());
            }
        }

        private BridgeResponse ExecuteCreate(BridgeCommand command, AnimationClipParams p)
        {
            if (string.IsNullOrEmpty(p.clipPath))
            {
                return BridgeResponse.Error(command.commandId, command.commandType,
                    "clipPath is required for create operation.");
            }

            var clip = new AnimationClip();
            if (p.frameRate > 0) clip.frameRate = p.frameRate;

            AssetDatabase.CreateAsset(clip, p.clipPath);
            AssetDatabase.SaveAssets();

            var result = new AnimationClipResult
            {
                operation = "create",
                clipPath = p.clipPath,
                success = true,
                message = $"AnimationClip created at {p.clipPath}"
            };
            return BridgeResponse.Success(
                command.commandId, command.commandType, JsonUtility.ToJson(result));
        }

        private BridgeResponse ExecuteGetInfo(BridgeCommand command, AnimationClipParams p)
        {
            var clip = LoadClip(p.clipPath);
            if (clip is null)
            {
                return BridgeResponse.Error(command.commandId, command.commandType,
                    $"AnimationClip not found at: {p.clipPath}");
            }

            var bindings = AnimationUtility.GetCurveBindings(clip);
            var events = AnimationUtility.GetAnimationEvents(clip);

            var result = new AnimationClipInfoResult
            {
                operation = "get-info",
                clipPath = p.clipPath,
                length = clip.length,
                frameRate = clip.frameRate,
                wrapMode = clip.wrapMode.ToString(),
                isLooping = clip.isLooping,
                eventCount = events.Length,
                curveCount = bindings.Length,
                success = true,
                message = "Animation clip info retrieved"
            };
            return BridgeResponse.Success(
                command.commandId, command.commandType, JsonUtility.ToJson(result));
        }

        private BridgeResponse ExecuteSetCurve(BridgeCommand command, AnimationClipParams p)
        {
            var clip = LoadClip(p.clipPath);
            if (clip is null)
            {
                return BridgeResponse.Error(command.commandId, command.commandType,
                    $"AnimationClip not found at: {p.clipPath}");
            }

            if (string.IsNullOrEmpty(p.propertyName))
            {
                return BridgeResponse.Error(command.commandId, command.commandType,
                    "propertyName is required for set-curve operation.");
            }

            var binding = new EditorCurveBinding
            {
                path = p.relativePath ?? "",
                type = ResolveType(p.componentType ?? "Transform"),
                propertyName = p.propertyName
            };

            var keyframes = new List<Keyframe>();
            if (p.keyframes is not null)
            {
                foreach (var kf in p.keyframes)
                    keyframes.Add(new Keyframe(kf.time, kf.value));
            }

            var curve = new AnimationCurve(keyframes.ToArray());
            AnimationUtility.SetEditorCurve(clip, binding, curve);
            EditorUtility.SetDirty(clip);
            AssetDatabase.SaveAssets();

            var result = new AnimationClipResult
            {
                operation = "set-curve",
                clipPath = p.clipPath,
                success = true,
                message = $"Curve set for {p.propertyName} with {keyframes.Count} keyframes"
            };
            return BridgeResponse.Success(
                command.commandId, command.commandType, JsonUtility.ToJson(result));
        }

        private BridgeResponse ExecuteGetCurves(BridgeCommand command, AnimationClipParams p)
        {
            var clip = LoadClip(p.clipPath);
            if (clip is null)
            {
                return BridgeResponse.Error(command.commandId, command.commandType,
                    $"AnimationClip not found at: {p.clipPath}");
            }

            var bindings = AnimationUtility.GetCurveBindings(clip);
            var curves = new List<CurveBindingInfo>();
            foreach (var b in bindings)
            {
                curves.Add(new CurveBindingInfo
                {
                    path = b.path,
                    componentType = b.type.Name,
                    propertyName = b.propertyName
                });
            }

            var result = new AnimationClipCurvesResult
            {
                operation = "get-curves",
                clipPath = p.clipPath,
                curves = curves,
                success = true,
                message = $"Found {curves.Count} curve bindings"
            };
            return BridgeResponse.Success(
                command.commandId, command.commandType, JsonUtility.ToJson(result));
        }

        private BridgeResponse ExecuteAddEvent(BridgeCommand command, AnimationClipParams p)
        {
            var clip = LoadClip(p.clipPath);
            if (clip is null)
            {
                return BridgeResponse.Error(command.commandId, command.commandType,
                    $"AnimationClip not found at: {p.clipPath}");
            }

            var existingEvents = AnimationUtility.GetAnimationEvents(clip);
            var eventList = new List<AnimationEvent>(existingEvents);

            var newEvent = new AnimationEvent
            {
                time = p.eventTime,
                functionName = p.eventFunction ?? "OnAnimationEvent"
            };
            if (!string.IsNullOrEmpty(p.eventStringParam))
                newEvent.stringParameter = p.eventStringParam;
            if (p.eventIntParam != 0)
                newEvent.intParameter = p.eventIntParam;
            if (p.eventFloatParam != 0f)
                newEvent.floatParameter = p.eventFloatParam;

            eventList.Add(newEvent);
            AnimationUtility.SetAnimationEvents(clip, eventList.ToArray());
            EditorUtility.SetDirty(clip);
            AssetDatabase.SaveAssets();

            var result = new AnimationClipResult
            {
                operation = "add-event",
                clipPath = p.clipPath,
                success = true,
                message = $"Event added at time {p.eventTime}: {newEvent.functionName}"
            };
            return BridgeResponse.Success(
                command.commandId, command.commandType, JsonUtility.ToJson(result));
        }

        private BridgeResponse ExecuteSetProperties(BridgeCommand command, AnimationClipParams p)
        {
            var clip = LoadClip(p.clipPath);
            if (clip is null)
            {
                return BridgeResponse.Error(command.commandId, command.commandType,
                    $"AnimationClip not found at: {p.clipPath}");
            }

            if (p.frameRate > 0)
                clip.frameRate = p.frameRate;

            // Set loop via AnimationClipSettings
            var settings = AnimationUtility.GetAnimationClipSettings(clip);
            if (p.setLooping)
                settings.loopTime = p.looping;
            if (!string.IsNullOrEmpty(p.wrapMode))
            {
                if (Enum.TryParse<WrapMode>(p.wrapMode, true, out var mode))
                    clip.wrapMode = mode;
            }
            AnimationUtility.SetAnimationClipSettings(clip, settings);

            EditorUtility.SetDirty(clip);
            AssetDatabase.SaveAssets();

            var result = new AnimationClipResult
            {
                operation = "set-properties",
                clipPath = p.clipPath,
                success = true,
                message = "Animation clip properties updated"
            };
            return BridgeResponse.Success(
                command.commandId, command.commandType, JsonUtility.ToJson(result));
        }

        // -----------------------------------------------------------------
        // Helpers
        // -----------------------------------------------------------------

        private static AnimationClip LoadClip(string path)
        {
            if (string.IsNullOrEmpty(path)) return null;
            return AssetDatabase.LoadAssetAtPath<AnimationClip>(path);
        }

        private static Type ResolveType(string typeName)
        {
            // Try common Unity types first
            var type = Type.GetType($"UnityEngine.{typeName}, UnityEngine.CoreModule");
            if (type is not null) return type;

            type = Type.GetType($"UnityEngine.{typeName}, UnityEngine");
            if (type is not null) return type;

            // Try fully-qualified name
            type = Type.GetType(typeName);
            return type ?? typeof(Transform);
        }
    }

    // -----------------------------------------------------------------
    // Models
    // -----------------------------------------------------------------

    [Serializable]
    public class AnimationClipParams
    {
        public string operation;
        public string clipPath;

        // set-curve
        public string relativePath;
        public string componentType;
        public string propertyName;
        public List<SerializableKeyframe> keyframes = new List<SerializableKeyframe>();

        // add-event
        public float eventTime;
        public string eventFunction;
        public string eventStringParam;
        public int eventIntParam;
        public float eventFloatParam;

        // set-properties
        public float frameRate = -1f;
        public bool looping;
        public bool setLooping;
        public string wrapMode;
    }

    [Serializable]
    public class SerializableKeyframe
    {
        public float time;
        public float value;
    }

    [Serializable]
    public class AnimationClipResult
    {
        public string operation;
        public string clipPath;
        public bool success;
        public string message;
    }

    [Serializable]
    public class AnimationClipInfoResult
    {
        public string operation;
        public string clipPath;
        public float length;
        public float frameRate;
        public string wrapMode;
        public bool isLooping;
        public int eventCount;
        public int curveCount;
        public bool success;
        public string message;
    }

    [Serializable]
    public class AnimationClipCurvesResult
    {
        public string operation;
        public string clipPath;
        public List<CurveBindingInfo> curves = new List<CurveBindingInfo>();
        public bool success;
        public string message;
    }

    [Serializable]
    public class CurveBindingInfo
    {
        public string path;
        public string componentType;
        public string propertyName;
    }
}
