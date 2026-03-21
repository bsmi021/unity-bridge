using System;
using UnityEditor;
using UnityEngine;

namespace BWS.Editor.ClaudeCodeBridge
{
    /// <summary>
    /// Command handler for audio settings operations.
    ///
    /// SUPPORTED OPERATIONS:
    /// 1. "get" - Read current audio settings
    /// 2. "set" - Modify audio settings
    ///
    /// GUARDS:
    /// - EditorApplication.isCompiling: blocks all operations
    /// - EditorApplication.isPlaying: blocks set operation
    /// </summary>
    public class AudioSettingsCommandHandler : ICommandHandler
    {
        public string CommandType => "audio-settings";

        public BridgeResponse Execute(BridgeCommand command)
        {
            try
            {
                if (EditorApplication.isCompiling)
                {
                    return BridgeResponse.Error(command.commandId, command.commandType,
                        "Cannot access audio settings while compiling.");
                }

                var parameters = JsonUtility.FromJson<AudioSettingsParams>(
                    command.parametersJson ?? "{}");
                if (parameters == null)
                    parameters = new AudioSettingsParams();

                AudioSettingsResult result;
                switch (parameters.operation?.ToLower())
                {
                    case "get":
                        result = ExecuteGet();
                        break;
                    case "set":
                        result = ExecuteSet(parameters);
                        break;
                    default:
                        result = new AudioSettingsResult
                        {
                            success = false,
                            operation = parameters.operation,
                            message = $"Unknown operation: {parameters.operation}. "
                                + "Supported: get, set"
                        };
                        break;
                }

                var resultJson = JsonUtility.ToJson(result);
                return BridgeResponse.Success(
                    command.commandId, command.commandType, resultJson);
            }
            catch (Exception ex)
            {
                BridgeLogger.LogError($"AudioSettings error: {ex}");
                return BridgeResponse.Error(
                    command.commandId, command.commandType, ex.ToString());
            }
        }

        private AudioSettingsResult ExecuteGet()
        {
            var config = AudioSettings.GetConfiguration();

            return new AudioSettingsResult
            {
                success = true,
                operation = "get",
                outputSampleRate = AudioSettings.outputSampleRate,
                speakerMode = config.speakerMode.ToString(),
                dspBufferSize = config.dspBufferSize,
                numRealVoices = config.numRealVoices,
                numVirtualVoices = config.numVirtualVoices,
                globalVolume = AudioListener.volume,
                globalPause = AudioListener.pause,
                message = "Audio settings retrieved"
            };
        }

        private AudioSettingsResult ExecuteSet(AudioSettingsParams p)
        {
            if (EditorApplication.isPlaying)
            {
                return new AudioSettingsResult
                {
                    success = false,
                    operation = "set",
                    message = "Cannot modify audio settings in play mode."
                };
            }

            if (p.setGlobalVolume)
                AudioListener.volume = Mathf.Clamp01(p.globalVolume);

            if (p.setGlobalPause)
                AudioListener.pause = p.globalPause;

            if (p.setSpeakerMode || p.setDspBufferSize)
            {
                var config = AudioSettings.GetConfiguration();
                if (p.setSpeakerMode)
                {
                    config.speakerMode =
                        (AudioSpeakerMode)Enum.Parse(
                            typeof(AudioSpeakerMode), p.speakerMode, true);
                }
                if (p.setDspBufferSize)
                    config.dspBufferSize = p.dspBufferSize;
                AudioSettings.Reset(config);
            }

            if (p.setOutputSampleRate)
            {
                var config = AudioSettings.GetConfiguration();
                config.sampleRate = p.outputSampleRate;
                AudioSettings.Reset(config);
            }

            var result = ExecuteGet();
            result.operation = "set";
            result.message = "Audio settings updated";
            return result;
        }
    }

    // -----------------------------------------------------------------
    // Models
    // -----------------------------------------------------------------

    [Serializable]
    public class AudioSettingsParams
    {
        public string operation;

        public int outputSampleRate;
        public bool setOutputSampleRate;
        public string speakerMode;
        public bool setSpeakerMode;
        public int dspBufferSize;
        public bool setDspBufferSize;
        public float globalVolume;
        public bool setGlobalVolume;
        public bool globalPause;
        public bool setGlobalPause;
    }

    [Serializable]
    public class AudioSettingsResult
    {
        public bool success;
        public string operation;
        public string message;

        public int outputSampleRate;
        public string speakerMode;
        public int dspBufferSize;
        public int numRealVoices;
        public int numVirtualVoices;
        public float globalVolume;
        public bool globalPause;
    }
}
