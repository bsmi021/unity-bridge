namespace BWS.Editor.ClaudeCodeBridge
{
    /// <summary>
    /// Registers all command handlers with the bridge.
    /// Extracted from ClaudeUnityBridge to keep it under 500 LOC.
    /// </summary>
    public static class BridgeCommandRegistry
    {
        /// <summary>
        /// Register all command handlers on the bridge instance.
        /// Called during initialization.
        /// </summary>
        public static void RegisterAll(System.Action<ICommandHandler> registerHandler)
        {
            // Core handlers
            registerHandler(new RunTestsCommandHandler());
            registerHandler(new QueryHierarchyCommandHandler());
            registerHandler(new GetComponentDataCommandHandler());
            registerHandler(new SetComponentDataCommandHandler());
            registerHandler(new AddComponentCommandHandler());
            registerHandler(new ValidatePrefabCommandHandler());
            registerHandler(new ProfilerSampleCommandHandler());
            registerHandler(new ReadConsoleCommandHandler());
            registerHandler(new GameObjectOperationCommandHandler());
            registerHandler(new BridgeStatusCommandHandler());

            // Phase 1 new handlers
            registerHandler(new ClearConsoleCommandHandler());
            registerHandler(new GetSelectionCommandHandler());
            registerHandler(new RefreshAssetsCommandHandler());
            registerHandler(new FocusObjectCommandHandler());

            // Phase 2 handlers
            registerHandler(new CompileCommandHandler());
            registerHandler(new ExecuteMenuItemCommandHandler());

            // Phase 2: Developer Workflow APIs
            registerHandler(new CompilationPipelineCommandHandler());
            registerHandler(new UndoCommandHandler());
            registerHandler(new TestListCommandHandler());
            registerHandler(new PrefabOverrideCommandHandler());
            registerHandler(new GameObjectUtilityCommandHandler());

            // Phase 1 expansion: Core Platform APIs
            registerHandler(new PlayerSettingsCommandHandler());
            registerHandler(new AssetExtendedCommandHandler());
#if UNITY_6000_0_OR_NEWER
            registerHandler(new BuildProfileCommandHandler());
#endif
            registerHandler(new PackageManagerCommandHandler());

            // Phase 3: Specialized APIs
            registerHandler(new ShaderInspectionCommandHandler());
            registerHandler(new LightmapOperationCommandHandler());
            registerHandler(new ImportSettingsCommandHandler());
            registerHandler(new SceneSetupCommandHandler());

            // Original handlers (split into partial classes during LOC refactor)
            registerHandler(new AnimatorOperationCommandHandler());
            registerHandler(new MaterialOperationCommandHandler());
            registerHandler(new BuildOperationCommandHandler());
            registerHandler(new SceneOperationCommandHandler());
            registerHandler(new PrefabOperationCommandHandler());
        }
    }
}
