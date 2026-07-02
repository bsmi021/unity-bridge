"""Static contract tests for the C# heartbeat generator."""

from __future__ import annotations

from pathlib import Path


def test_heartbeat_generator_emits_editor_readiness_fields() -> None:
    source = Path("ClaudeCodeBridge/HeartbeatGenerator.cs").read_text(encoding="utf-8")

    assert "EditorApplication.isUpdating" in source
    assert "EditorApplication.isPlayingOrWillChangePlaymode" in source
    assert "CompilationPipeline.compilationStarted" in source
    assert "CompilationPipeline.compilationFinished" in source
    assert "AssemblyReloadEvents.beforeAssemblyReload" in source
    assert "AssemblyReloadEvents.afterAssemblyReload" in source
    assert "public bool isUpdating;" in source
    assert "public bool isReloadingAssemblies;" in source
    assert "public string lastBusyReason;" in source
    assert "public string lastBusyTimestamp;" in source
    assert "public int domainGeneration;" in source
    assert "public string lastReloadTimestamp;" in source
    assert 'SessionState.GetInt("UnityBridge.DomainGeneration"' in source
    assert "public static int DomainGeneration" in source
    assert '"reloading_assemblies"' in source


def test_heartbeat_generator_wires_unity_65_lifecycle_callbacks() -> None:
    source = Path("ClaudeCodeBridge/HeartbeatGenerator.cs").read_text(encoding="utf-8")

    assert "#if UNITY_6000_5_OR_NEWER" in source
    assert "OnCodeUnloading" in source
    assert "OnCodeLoaded" in source
    assert "OnEnteringPlayMode" in source
    assert "OnExitingPlayMode" in source
    assert "MarkAssemblyReloadStarting()" in source
    assert "MarkAssemblyReloadFinished()" in source


def test_bridge_operation_ledger_contract_exists() -> None:
    source = Path("ClaudeCodeBridge/BridgeOperationLedger.cs").read_text(encoding="utf-8")

    assert "class BridgeOperationLedger" in source
    assert "operations" in source
    assert "events.jsonl" in source
    assert 'StateQueued = "queued"' in source
    assert 'StateAccepted = "accepted"' in source
    assert 'StateRunning = "running"' in source
    assert 'StateInterrupted = "interrupted"' in source
    assert "RecoverAfterReload()" in source
    assert "WriteAtomic" in source


def test_bridge_operation_ledger_atomic_writes_are_retryable() -> None:
    source = Path("ClaudeCodeBridge/BridgeOperationLedger.cs").read_text(encoding="utf-8")

    assert "AtomicWriteMaxAttempts" in source
    assert "Guid.NewGuid()" in source
    assert "File.Replace(tempPath, path, null)" in source
    assert "Thread.Sleep(RetryDelayMs(attempt))" in source
    assert "TryDeleteTemp(tempPath)" in source


def test_bridge_operation_ledger_writes_utf8_without_bom() -> None:
    source = Path("ClaudeCodeBridge/BridgeOperationLedger.cs").read_text(encoding="utf-8")

    assert "new UTF8Encoding(false, true)" in source
    assert "new StreamWriter(stream, Encoding.UTF8)" not in source


def test_claude_unity_bridge_wires_operation_ledger() -> None:
    source = Path("ClaudeCodeBridge/ClaudeUnityBridge.cs").read_text(encoding="utf-8")

    assert "BridgeOperationLedger.EnsureInitialized()" in source
    assert "BridgeOperationLedger.RecoverAfterReload()" in source
    assert "BridgeOperationLedger.MarkAccepted(command, commandFilePath)" in source
    assert "BridgeOperationLedger.WriteAtomic(filePath, responseJson)" in source
    assert "BridgeOperationLedger.MarkResponse(response)" in source
    assert "Operation ledger terminal-state update failed" in source
