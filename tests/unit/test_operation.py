"""Unit tests for durable operation state."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from unity_bridge.core.operation import (
    RETRY_NON_IDEMPOTENT,
    RETRY_READ_ONLY,
    SCHEMA_VERSION,
    STATE_ACCEPTED,
    STATE_COMPLETED,
    STATE_QUEUED,
    STATE_RUNNING,
    OperationRecord,
    OperationStateMachine,
    OperationStore,
    parameters_hash,
    retry_policy_for_command,
    terminal_state_for_response_status,
)
from unity_bridge.commands.operation import operation_list, operation_status


def _record(command_id: str = "rec", state: str = "queued") -> OperationRecord:
    return OperationRecord(
        command_id=command_id,
        command_type="run-tests",
        state=state,
        parameters_hash="h",
        retry_policy="non_idempotent",
        schema_version=SCHEMA_VERSION,
    )


class TestLedgerWriteResilience:
    """Cross-process file contention (Python + C# writing the same ledger file)
    must never propagate out of the ledger and fail/retry the command."""

    def test_write_retries_transient_lock_then_succeeds(self, fake_project: Path) -> None:
        store = OperationStore(fake_project)
        calls = {"n": 0}
        real_replace = Path.replace

        def flaky_replace(self: Path, target):  # type: ignore[no-untyped-def]
            calls["n"] += 1
            if calls["n"] < 3:
                raise PermissionError("[WinError 32] being used by another process")
            return real_replace(self, target)

        with patch.object(Path, "replace", flaky_replace):
            store.write(_record("retry-ok"))  # must not raise

        assert calls["n"] >= 3
        assert store.load("retry-ok") is not None

    def test_write_swallows_persistent_lock(self, fake_project: Path) -> None:
        store = OperationStore(fake_project)

        def always_locked(self: Path, target):  # type: ignore[no-untyped-def]
            raise PermissionError("being used by another process")

        with patch.object(Path, "replace", always_locked):
            # Must NOT raise - a ledger write failure is best-effort, never fatal.
            store.write(_record("never"))

    def test_transition_does_not_raise_on_write_failure(self, fake_project: Path) -> None:
        store = OperationStore(fake_project)
        store.create_queued(
            command_id="t",
            command_type="run-tests",
            parameters={},
            command_path=fake_project / "c.json",
            response_path=fake_project / "r.json",
            domain_generation=None,
            retry_policy="non_idempotent",
        )

        def always_locked(self: Path, target):  # type: ignore[no-untyped-def]
            raise PermissionError("being used by another process")

        with patch.object(Path, "replace", always_locked):
            result = store.transition("t", STATE_ACCEPTED, reason="accept")

        # Returns (best-effort) rather than propagating the lock error.
        assert result is not None

    def test_load_retries_transient_lock_then_succeeds(self, fake_project: Path) -> None:
        store = OperationStore(fake_project)
        store.create_queued(
            command_id="locked",
            command_type="run-tests",
            parameters={},
            command_path=fake_project / "command.json",
            response_path=fake_project / "response.json",
            domain_generation=None,
            retry_policy="non_idempotent",
        )
        calls = {"n": 0}
        real_read_text = Path.read_text

        def flaky_read_text(self: Path, *args, **kwargs):  # type: ignore[no-untyped-def]
            if self == store.record_path("locked") and calls["n"] < 2:
                calls["n"] += 1
                raise PermissionError("[WinError 32] being used by another process")
            return real_read_text(self, *args, **kwargs)

        with patch.object(Path, "read_text", flaky_read_text):
            record = store.load("locked")

        assert record is not None
        assert record.command_id == "locked"
        assert calls["n"] == 2

    def test_load_retries_transient_decode_error_then_succeeds(
        self,
        fake_project: Path,
    ) -> None:
        store = OperationStore(fake_project)
        store.create_queued(
            command_id="partial",
            command_type="run-tests",
            parameters={},
            command_path=fake_project / "command.json",
            response_path=fake_project / "response.json",
            domain_generation=None,
            retry_policy="non_idempotent",
        )
        calls = {"n": 0}
        real_read_text = Path.read_text

        def flaky_read_text(self: Path, *args, **kwargs):  # type: ignore[no-untyped-def]
            if self == store.record_path("partial") and calls["n"] < 2:
                calls["n"] += 1
                raise UnicodeDecodeError("utf-8", b"\xff", 0, 1, "invalid start byte")
            return real_read_text(self, *args, **kwargs)

        with patch.object(Path, "read_text", flaky_read_text):
            record = store.load("partial")

        assert record is not None
        assert record.command_id == "partial"
        assert calls["n"] == 2


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


def _make_record(store: OperationStore, command_id: str, state: str) -> None:
    store.create_queued(
        command_id=command_id,
        command_type="set-component-data",
        parameters={},
        command_path=store.project_root / "cmd.json",
        response_path=store.project_root / "resp.json",
        domain_generation=None,
        retry_policy=RETRY_NON_IDEMPOTENT,
    )
    if state != STATE_QUEUED:
        store.transition(command_id, state, reason="setup")


def test_store_transition_rejects_invalid_without_raising(fake_project: Path) -> None:
    """store.transition must not raise on an illegal transition (the other
    writer advanced the state); it returns the current record unchanged."""
    store = OperationStore(fake_project)
    _make_record(store, "id", STATE_RUNNING)

    # RUNNING -> ACCEPTED is not allowed; should be rejected gracefully.
    result = store.transition("id", STATE_ACCEPTED, reason="stale")

    assert result is not None
    assert result.state == STATE_RUNNING


def test_store_transition_does_not_clobber_concurrent_terminal(fake_project: Path) -> None:
    """C2: if the C# writer advances to a terminal state between our load and
    write, the Python transition must not overwrite it with a non-terminal one."""
    store = OperationStore(fake_project)
    _make_record(store, "id", STATE_ACCEPTED)
    completed = store.load("id")
    object.__setattr__(completed, "state", STATE_COMPLETED)

    accepted = store.load("id")  # state == accepted
    # First load (top of transition) sees ACCEPTED; reload-before-write sees COMPLETED.
    with patch.object(store, "load", side_effect=[accepted, completed]):
        result = store.transition("id", STATE_RUNNING, reason="unity running")

    assert result is not None
    assert result.state == STATE_COMPLETED
    # The non-terminal RUNNING write must have been skipped (disk not regressed).
    assert store.load("id").state != STATE_RUNNING


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
