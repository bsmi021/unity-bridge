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
            registerHandler(new ExecuteScriptCommandHandler());

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

            // Phase 4: Critical Gaps
            registerHandler(new SelectionCommandHandler());
            registerHandler(new EditorPrefsCommandHandler());
            registerHandler(new BuildScenesCommandHandler());
            registerHandler(new TransformCommandHandler());
            registerHandler(new SerializedPropertyCommandHandler());
            registerHandler(new PhysicsConfigCommandHandler());
            registerHandler(new QualitySettingsCommandHandler());
            registerHandler(new TagsLayersCommandHandler());
            registerHandler(new EditorConfigCommandHandler());

            // Phase 5: Quick Wins
            registerHandler(new RemoveComponentCommandHandler());
            registerHandler(new ComponentToggleCommandHandler());
            registerHandler(new ConsoleLogCommandHandler());

            // Phase 4 expansion: Build, Platform, Pipeline
            registerHandler(new ScriptExecutionOrderCommandHandler());
            registerHandler(new AssemblyReloadLockCommandHandler());
            registerHandler(new FindReferencesCommandHandler());

            // Phase 4 expansion: Specialized Workflow Gaps
            registerHandler(new NavMeshCommandHandler());
            registerHandler(new AnimationClipCommandHandler());
            registerHandler(new TerrainCommandHandler());
            registerHandler(new ReflectionProbeCommandHandler());
            registerHandler(new OcclusionCullingCommandHandler());

            // Phase 6a: Settings expansion
            registerHandler(new TimeSettingsCommandHandler());
            registerHandler(new GraphicsSettingsCommandHandler());
            registerHandler(new EnvironmentSettingsCommandHandler());
            registerHandler(new AudioSettingsCommandHandler());

            // Phase 6b: Scene / Material / Component / Inspector gaps
            registerHandler(new ComponentCopyCommandHandler());
            registerHandler(new ComponentResetCommandHandler());
            registerHandler(new SceneViewCommandHandler());
            registerHandler(new GameViewCommandHandler());
            registerHandler(new ProfilerControlCommandHandler());

            // Phase 6c: Addressables & Tilemap
            registerHandler(new AddressablesCommandHandler());
            registerHandler(new TilemapCommandHandler());

            // Phase 6d: Input System authoring
            registerHandler(new InputSystemCommandHandler());

            // Phase 6e: Misc authoring tools
            registerHandler(new ClipboardCommandHandler());
            registerHandler(new PresetCommandHandler());
            registerHandler(new SceneTemplateCommandHandler());
            registerHandler(new MonoScriptCommandHandler());
            registerHandler(new DeepSerializeCommandHandler());
            registerHandler(new WindowCommandHandler());

            // Phase 7a: Query & Report
            registerHandler(new SyncSolutionCommandHandler());
            registerHandler(new CloudServicesCommandHandler());
            registerHandler(new Physics2DConfigCommandHandler());
            registerHandler(new SearchQueryCommandHandler());

            // Unity 6.4: Identity & Audit
            registerHandler(new ObjectIdentityCommandHandler());
            registerHandler(new ProjectAuditorCommandHandler());
            registerHandler(new CodeCoverageCommandHandler());
            registerHandler(new UIToolkitCommandHandler());
            registerHandler(new RenderPipelineCommandHandler());
            registerHandler(new GraphicsStateCommandHandler());
            registerHandler(new GraphToolkitCommandHandler());
            registerHandler(new SceneStateCommandHandler());
            registerHandler(new EntitiesCommandHandler());
            registerHandler(new AdaptivePerformanceCommandHandler());
            registerHandler(new MultiplayerPlayModeCommandHandler());

            // Core handlers registered previously as "disabled pending Unity import"
            // (m3 from gap-analysis-report) — now enabled.
            registerHandler(new CaptureScreenshotCommandHandler());
            registerHandler(new PlayModeControlCommandHandler());
            registerHandler(new AssetOperationCommandHandler());

            // Original handlers (split into partial classes during LOC refactor)
            registerHandler(new AnimatorOperationCommandHandler());
            registerHandler(new MaterialOperationCommandHandler());
            registerHandler(new BuildOperationCommandHandler());
            registerHandler(new SceneOperationCommandHandler());
            registerHandler(new PrefabOperationCommandHandler());
        }
    }
}
