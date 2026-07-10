"""Source contracts for the Unity compile command lifecycle."""

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]


def test_waited_compile_persists_recovery_marker_before_refresh() -> None:
    source = (REPO_ROOT / "ClaudeCodeBridge" / "CompileCommandHandler.cs").read_text(
        encoding="utf-8"
    )

    execute_start = source.index("private static BridgeResponse TriggerAndWait")
    execute_end = source.index("private static void RemovePendingWait", execute_start)
    execute_source = source[execute_start:execute_end]

    marker_index = execute_source.index("SessionState.SetString(PendingCommandIdKey")
    refresh_index = execute_source.index("AssetDatabase.Refresh")

    assert marker_index < refresh_index
