namespace BWS.Editor.ClaudeCodeBridge
{
    public static class BridgeEditorSceneCleanup
    {
        public static bool PrepareForAutomation(string context, out string message)
        {
            return BridgeSceneModalRecovery.PrepareForAutomation(context, out message);
        }

        public static bool PrepareForExplicitSave(string context, out string message)
        {
            return BridgeSceneModalRecovery.PrepareForExplicitSave(context, out message);
        }

        public static string DiscardUnsavedBlankScenes(string context)
        {
            return BridgeSceneModalRecovery.DiscardUnsavedBlankScenes(context);
        }
    }
}
