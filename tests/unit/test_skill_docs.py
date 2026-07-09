"""Regression checks for the shipped Codex skill and project agents."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SKILL_DIR = ROOT / ".agents" / "skills" / "unity-bridge-cli"
SKILL_PATH = SKILL_DIR / "SKILL.md"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _frontmatter(text: str) -> dict[str, str]:
    lines = text.splitlines()
    assert lines[0] == "---"
    end = lines[1:].index("---") + 1
    data: dict[str, str] = {}
    current_key: str | None = None
    current_value: list[str] = []

    for line in lines[1:end]:
        if line.startswith(" ") and current_key:
            current_value.append(line.strip())
            continue
        if current_key:
            data[current_key] = " ".join(current_value).strip()
        key, value = line.split(":", 1)
        current_key = key.strip()
        current_value = [value.strip().strip(">")]

    if current_key:
        data[current_key] = " ".join(current_value).strip()
    return data


def test_skill_description_stays_codex_discoverable() -> None:
    metadata = _frontmatter(_read(SKILL_PATH))
    description = metadata["description"]

    assert len(description) <= 1024
    assert "unity-bridge CLI" in description
    assert "Unity Editor automation" in description
    assert "Timeline" in description


def test_skill_mentions_cli_only_interface_and_operation_polling() -> None:
    skill = _read(SKILL_PATH)

    assert "Use the CLI first" in skill
    # This repo's own internal MCP interface (mcp/ package + serve command)
    # is retired; the unrelated third-party unity-mcp server is a separate,
    # optional supplemental tool documented in its own section.
    assert "internal MCP interface (a `mcp/` package + `serve` command) has been fully retired" in skill
    assert "unity-bridge vs. unity-mcp" in skill
    assert "unity-bridge operation status COMMAND_ID" in skill
    assert "unity-bridge operation wait COMMAND_ID" in skill
    assert "test run --detach" in skill
    assert "test compile --detach" in skill
    assert ".claude/unity/" in skill
    assert "UNITY_BRIDGE_EDITOR_READY_TIMEOUT" in skill
    assert "UNITY_BRIDGE_IN_FLIGHT_BUSY_GRACE" in skill


def test_skill_has_no_active_mcp_tooling_references() -> None:
    """MCP is mentioned only in the retirement note, never as something to use."""
    skill = _read(SKILL_PATH)

    assert "unity-bridge serve" not in skill
    assert "unity_submit_command" not in skill
    assert "unity_operation_status" not in skill


def test_specialized_reference_covers_new_package_provided_commands() -> None:
    specialized_reference = _read(SKILL_DIR / "references" / "specialized-commands.md")

    assert "timeline create-track" in specialized_reference
    assert "cinemachine list-cameras" in specialized_reference
    assert "localization list-locales" in specialized_reference
    assert "memory-profiler take-snapshot" in specialized_reference
    assert "vfx get-info" in specialized_reference


def test_skill_openai_yaml_metadata_exists() -> None:
    metadata = _read(SKILL_DIR / "agents" / "openai.yaml")

    assert "display_name: Unity Bridge CLI" in metadata
    assert "short_description: Operate Unity through the bridge CLI." in metadata
    assert "default_prompt: Use $unity-bridge-cli" in metadata
    assert "allow_implicit_invocation: true" in metadata


def test_reference_docs_cover_recent_build_and_addressables_commands() -> None:
    build_reference = _read(SKILL_DIR / "references" / "build-commands.md")
    specialized_reference = _read(SKILL_DIR / "references" / "specialized-commands.md")

    assert "profile set-scenes" in build_reference
    assert "profile set-defines" in build_reference
    assert "profile build" in build_reference
    assert "addressables profiles" in specialized_reference
    assert "addressables set-profile" in specialized_reference
    assert "addressables set-label" in specialized_reference
    assert "addressables analyze" in specialized_reference


def test_codex_project_agents_are_registered_on_disk() -> None:
    agent_dir = ROOT / ".codex" / "agents"
    for name in ("unity-bridge-explorer.toml", "unity-bridge-reviewer.toml"):
        source = _read(agent_dir / name)
        assert "name =" in source
        assert "description =" in source
        assert "developer_instructions =" in source
        assert 'sandbox_mode = "read-only"' in source
