#if UNITY_6000_5_OR_NEWER
using UnityEditor;
using UnityEditor.Build.Profile;
using UnityEngine;

namespace BWS.Editor.ClaudeCodeBridge
{
    internal sealed class BuildProfileCreateCallback : ScriptableObject
    {
        private const double FallbackDelaySeconds = 5.0;
        private const double DeadlineSeconds = 25.0;

        [SerializeField] private string _commandId;
        [SerializeField] private string _commandType;
        [SerializeField] private bool _scheduled;
        [SerializeField] private BuildProfile _profile;
        [SerializeField] private double _fallbackAt;
        [SerializeField] private double _deadlineAt;

        internal void Initialize(string commandId, string commandType)
        {
            _commandId = commandId;
            _commandType = commandType;
        }

        internal void Begin(BuildProfile profile)
        {
            if (_scheduled)
                return;

            _profile = profile;
            var now = EditorApplication.timeSinceStartup;
            _fallbackAt = now + FallbackDelaySeconds;
            _deadlineAt = now + DeadlineSeconds;
            EditorApplication.update += CheckPersistedFallback;
        }

        public void OnProfileReady(BuildProfile profile)
        {
            ScheduleSuccess(profile, "unity-callback");
        }

        private void CheckPersistedFallback()
        {
            var now = EditorApplication.timeSinceStartup;
            if (now >= _fallbackAt && !string.IsNullOrEmpty(AssetDatabase.GetAssetPath(_profile)))
            {
                ScheduleSuccess(_profile, "persisted-asset-fallback");
                return;
            }

            if (now >= _deadlineAt)
                WriteTerminalFailure();
        }

        private void ScheduleSuccess(BuildProfile profile, string completionSource)
        {
            if (_scheduled)
                return;

            _scheduled = true;
            EditorApplication.update -= CheckPersistedFallback;
            var commandId = _commandId;
            var commandType = _commandType;
            EditorApplication.delayCall += () =>
            {
                try
                {
                    BuildProfileCreateOperation.WriteCreateResult(
                        commandId, commandType, profile, completionSource);
                }
                finally
                {
                    DestroyImmediate(this);
                }
            };
        }

        private void WriteTerminalFailure()
        {
            if (_scheduled)
                return;

            _scheduled = true;
            EditorApplication.update -= CheckPersistedFallback;
            ClaudeUnityBridge.WriteResponseStatic(BridgeResponse.Error(
                _commandId,
                _commandType,
                "Build profile creation produced neither a callback nor a persisted asset."));
            DestroyImmediate(this);
        }
    }
}
#endif
