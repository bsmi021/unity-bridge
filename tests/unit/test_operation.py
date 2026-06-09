"""Unit tests for durable operation state."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from unity_bridge.core.operation import (
    RETRY_NON_IDEMPOTENT,
    RETRY_READ_ONLY,
    STATE_ACCEPTED,
    STATE_COMPLETED,
    STATE_QUEUED,
    OperationStateMachine,
    OperationStore,
    parameters_hash,
    retry_policy_for_command,
    terminal_state_for_response_status,
)
from unity_bridge.commands.operation import operation_list, operation_status


def test_parameters_hash_is_stable_for_sorted_json() -> None:
    left = parameters_hash({"b": 2, "a": 1})
    right = parameters_hash({"a": 1, "b": 2})
    assert left == right
    assert len(left) == 64


def test_operation_store_writes_json_and_jsonl(fake_project: Path) -> None:
    store = OperationStore(fake_project)
    command_path = fake_project / ".claude" / "unity" / "commands" / "id-test.json"
    response_path = fake_project / ".claude" / "unity" / "responses" / "id-test.json"

    record = store.create_queued(
        command_id="id",
        command_type="query-hierarchy",
        parameters={"depth": 1},
        command_path=command_path,
        response_path=response_path,
        domain_generation=7,
        retry_policy=RETRY_READ_ONLY,
    )

    stored = json.loads(store.record_path("id").read_text(encoding="utf-8"))
    events = store.events_path("id").read_text(encoding="utf-8").strip().splitlines()

    assert record.state == STATE_QUEUED
    assert stored["schemaVersion"] == 1
    assert stored["commandId"] == "id"
    assert stored["state"] == STATE_QUEUED
    assert stored["domainGeneration"] == 7
    assert len(events) == 1
    assert json.loads(events[0])["toState"] == STATE_QUEUED


def test_operation_store_load_accepts_utf8_bom_snapshot(fake_project: Path) -> None:
    store = OperationStore(fake_project)
    command_path = fake_project / ".claude" / "unity" / "commands" / "id-test.json"
    response_path = fake_project / ".claude" / "unity" / "responses" / "id-test.json"
    store.create_queued(
        command_id="id",
        command_type="query-hierarchy",
        parameters={},
        command_path=command_path,
        response_path=response_path,
        domain_generation=None,
        retry_policy=RETRY_READ_ONLY,
    )
    record_path = store.record_path("id")
    record_path.write_bytes(b"\xef\xbb\xbf" + record_path.read_bytes())

    record = store.load("id")

    assert record is not None
    assert record.command_id == "id"
    assert record.state == STATE_QUEUED


def test_operation_store_transitions_and_logs_event(fake_project: Path) -> None:
    store = OperationStore(fake_project)
    path = fake_project / "cmd.json"
    store.create_queued(
        command_id="id",
        command_type="query-hierarchy",
        parameters={},
        command_path=path,
        response_path=path,
        domain_generation=None,
        retry_policy=RETRY_READ_ONLY,
    )

    accepted = store.transition("id", STATE_ACCEPTED, reason="Unity accepted command")
    completed = store.transition("id", STATE_COMPLETED, reason="success")
    event_lines = store.events_path("id").read_text(encoding="utf-8").strip().splitlines()

    assert accepted is not None
    assert accepted.accepted_at is not None
    assert completed is not None
    assert completed.is_terminal is True
    assert completed.terminal_at is not None
    assert len(event_lines) == 3
    assert json.loads(event_lines[-1])["toState"] == STATE_COMPLETED


def test_operation_state_machine_rejects_invalid_transition(fake_project: Path) -> None:
    store = OperationStore(fake_project)
    store.create_queued(
        command_id="id",
        command_type="set-component-data",
        parameters={},
        command_path=fake_project / "cmd.json",
        response_path=fake_project / "resp.json",
        domain_generation=None,
        retry_policy=RETRY_NON_IDEMPOTENT,
    )
    completed = store.transition("id", STATE_COMPLETED, reason="success")

    assert completed is not None
    with pytest.raises(ValueError):
        OperationStateMachine.transition(record=completed, to_state=STATE_ACCEPTED)


def test_retry_policy_classifies_parallel_safe_commands() -> None:
    assert retry_policy_for_command("query-hierarchy") == RETRY_READ_ONLY
    assert retry_policy_for_command("set-component-data") == RETRY_NON_IDEMPOTENT


def test_terminal_response_status_mapping() -> None:
    assert terminal_state_for_response_status("success") == STATE_COMPLETED
    assert terminal_state_for_response_status("error") == "failed"
    assert terminal_state_for_response_status("running") is None


async def test_operation_status_command_returns_record(fake_project: Path) -> None:
    store = OperationStore(fake_project)
    store.create_queued(
        command_id="id",
        command_type="query-hierarchy",
        parameters={},
        command_path=fake_project / "cmd.json",
        response_path=fake_project / "resp.json",
        domain_generation=2,
        retry_policy=RETRY_READ_ONLY,
    )

    result = await operation_status(fake_project, "id")

    assert result.success is True
    assert result.data["commandId"] == "id"
    assert result.data["domainGeneration"] == 2


async def test_operation_status_command_reports_missing(fake_project: Path) -> None:
    result = await operation_status(fake_project, "missing")

    assert result.success is False
    assert result.exit_code == 2
    assert result.data["status"] == "not_found"


async def test_operation_list_command_hides_terminal_by_default(fake_project: Path) -> None:
    store = OperationStore(fake_project)
    store.create_queued(
        command_id="active",
        command_type="query-hierarchy",
        parameters={},
        command_path=fake_project / "active.json",
        response_path=fake_project / "active-response.json",
        domain_generation=None,
        retry_policy=RETRY_READ_ONLY,
    )
    store.create_queued(
        command_id="done",
        command_type="query-hierarchy",
        parameters={},
        command_path=fake_project / "done.json",
        response_path=fake_project / "done-response.json",
        domain_generation=None,
        retry_policy=RETRY_READ_ONLY,
    )
    store.transition("done", STATE_COMPLETED, reason="success")

    active_only = await operation_list(fake_project)
    include_all = await operation_list(fake_project, include_terminal=True)

    assert active_only.data["count"] == 1
    assert active_only.data["operations"][0]["commandId"] == "active"
    assert include_all.data["count"] == 2
