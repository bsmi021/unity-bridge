"""Durable bridge operation state.

The bridge protocol is file based, so operation persistence should stay file
based too. One JSON file stores the latest state for recovery. A companion
JSONL file stores transition history for diagnostics.
"""

from __future__ import annotations

import hashlib
import json
import logging
import time
import uuid
from collections.abc import Callable
from dataclasses import dataclass, replace
from datetime import datetime
from pathlib import Path
from typing import Any

from unity_bridge.core.timeutil import (
    optional_int as _optional_int,
    parse_optional_datetime as _parse_optional_datetime,
    utc_now_iso as _utc_now,
)

logger = logging.getLogger("unity_bridge.operation")

SCHEMA_VERSION = 1

# The operation ledger files are written by BOTH this process and the C# bridge,
# so a write can transiently hit a cross-process file lock (e.g. Windows
# "being used by another process"). Ledger persistence is best-effort durability,
# never on the critical path: a failed write must never propagate and fail/retry
# the command itself (which would, for run-tests, spawn a duplicate run).
_LEDGER_WRITE_ATTEMPTS = 5
_LEDGER_WRITE_BASE_DELAY = 0.02


def _best_effort_write(do_write: Callable[[], None], path: Path) -> bool:
    """Run a write with bounded retries on transient file locks; never raises.

    Returns True on success, False if every attempt failed (logged as a warning).
    """
    last_exc: Exception | None = None
    for attempt in range(_LEDGER_WRITE_ATTEMPTS):
        try:
            do_write()
            return True
        except (PermissionError, OSError) as exc:
            last_exc = exc
            if attempt < _LEDGER_WRITE_ATTEMPTS - 1:
                time.sleep(_LEDGER_WRITE_BASE_DELAY * (2**attempt))
    logger.warning(
        "Ledger write failed for %s after %d attempts: %s",
        path,
        _LEDGER_WRITE_ATTEMPTS,
        last_exc,
    )
    return False


STATE_QUEUED = "queued"
STATE_ACCEPTED = "accepted"
STATE_RUNNING = "running"
STATE_RECOVERING = "recovering_after_reload"
STATE_COMPLETED = "completed"
STATE_FAILED = "failed"
STATE_INTERRUPTED = "interrupted"
STATE_ABANDONED = "abandoned"

TERMINAL_STATES = {
    STATE_COMPLETED,
    STATE_FAILED,
    STATE_INTERRUPTED,
    STATE_ABANDONED,
}

RETRY_READ_ONLY = "read_only"
RETRY_SAFE_BEFORE_START = "safe_before_start"
RETRY_IDEMPOTENT_MUTATION = "idempotent_mutation"
RETRY_NON_IDEMPOTENT = "non_idempotent"

ALLOWED_TRANSITIONS = {
    STATE_QUEUED: {
        STATE_ACCEPTED,
        STATE_RUNNING,
        STATE_COMPLETED,
        STATE_FAILED,
        STATE_INTERRUPTED,
        STATE_ABANDONED,
    },
    STATE_ACCEPTED: {
        STATE_RUNNING,
        STATE_COMPLETED,
        STATE_FAILED,
        STATE_INTERRUPTED,
        STATE_ABANDONED,
        STATE_RECOVERING,
    },
    STATE_RUNNING: {
        STATE_COMPLETED,
        STATE_FAILED,
        STATE_INTERRUPTED,
        STATE_ABANDONED,
        STATE_RECOVERING,
    },
    STATE_RECOVERING: {
        STATE_RUNNING,
        STATE_COMPLETED,
        STATE_FAILED,
        STATE_INTERRUPTED,
        STATE_ABANDONED,
    },
}


@dataclass(frozen=True)
class OperationRecord:
    """Current persisted state for one bridge command."""

    command_id: str
    command_type: str
    state: str
    parameters_hash: str
    retry_policy: str
    schema_version: int = SCHEMA_VERSION
    domain_generation: int | None = None
    idempotency_key: str | None = None
    command_path: str | None = None
    response_path: str | None = None
    created_at: str | None = None
    accepted_at: str | None = None
    started_at: str | None = None
    last_progress_at: str | None = None
    terminal_at: str | None = None
    last_busy_reason: str | None = None
    last_error: str | None = None

    @property
    def is_terminal(self) -> bool:
        """Whether this operation cannot transition further."""
        return self.state in TERMINAL_STATES

    def to_dict(self) -> dict[str, Any]:
        """Serialize with camelCase keys for C# JsonUtility compatibility."""
        return {
            "schemaVersion": self.schema_version,
            "commandId": self.command_id,
            "commandType": self.command_type,
            "state": self.state,
            "parametersHash": self.parameters_hash,
            "retryPolicy": self.retry_policy,
            "domainGeneration": self.domain_generation,
            "idempotencyKey": self.idempotency_key,
            "commandPath": self.command_path,
            "responsePath": self.response_path,
            "createdAt": self.created_at,
            "acceptedAt": self.accepted_at,
            "startedAt": self.started_at,
            "lastProgressAt": self.last_progress_at,
            "terminalAt": self.terminal_at,
            "lastBusyReason": self.last_busy_reason,
            "lastError": self.last_error,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> OperationRecord:
        """Deserialize from the persisted camelCase JSON shape."""
        return cls(
            schema_version=int(data.get("schemaVersion", SCHEMA_VERSION)),
            command_id=str(data["commandId"]),
            command_type=str(data["commandType"]),
            state=str(data["state"]),
            parameters_hash=str(data.get("parametersHash") or ""),
            retry_policy=str(data.get("retryPolicy") or RETRY_NON_IDEMPOTENT),
            domain_generation=_optional_int(data.get("domainGeneration")),
            idempotency_key=data.get("idempotencyKey"),
            command_path=data.get("commandPath"),
            response_path=data.get("responsePath"),
            created_at=data.get("createdAt"),
            accepted_at=data.get("acceptedAt"),
            started_at=data.get("startedAt"),
            last_progress_at=data.get("lastProgressAt"),
            terminal_at=data.get("terminalAt"),
            last_busy_reason=data.get("lastBusyReason"),
            last_error=data.get("lastError"),
        )


class OperationStateMachine:
    """Transition rules for operation lifecycle states."""

    @staticmethod
    def transition(
        record: OperationRecord,
        to_state: str,
        *,
        reason: str | None = None,
        busy_reason: str | None = None,
    ) -> OperationRecord:
        """Return a new record after a validated transition."""
        if record.state == to_state:
            return _touch(record, to_state, reason, busy_reason)
        allowed = ALLOWED_TRANSITIONS.get(record.state, set())
        if to_state not in allowed:
            raise ValueError(f"Invalid operation transition: {record.state} -> {to_state}")
        return _touch(record, to_state, reason, busy_reason)


class OperationStore:
    """Persist operation JSON snapshots and JSONL transition events."""

    def __init__(self, project_root: Path) -> None:
        self.project_root = Path(project_root)
        self.operations_path = self.project_root / ".claude" / "unity" / "operations"
        self.operations_path.mkdir(parents=True, exist_ok=True)

    def record_path(self, command_id: str) -> Path:
        """Path to the current-state JSON file for a command."""
        return self.operations_path / f"{command_id}.json"

    def events_path(self, command_id: str) -> Path:
        """Path to the JSONL event history for a command."""
        return self.operations_path / f"{command_id}.events.jsonl"

    def create_queued(
        self,
        *,
        command_id: str,
        command_type: str,
        parameters: dict[str, Any] | None,
        command_path: Path,
        response_path: Path,
        domain_generation: int | None,
        retry_policy: str,
        idempotency_key: str | None = None,
    ) -> OperationRecord:
        """Create the initial queued record before writing a command file."""
        timestamp = _utc_now()
        record = OperationRecord(
            command_id=command_id,
            command_type=command_type,
            state=STATE_QUEUED,
            parameters_hash=parameters_hash(parameters),
            retry_policy=retry_policy,
            domain_generation=domain_generation,
            idempotency_key=idempotency_key,
            command_path=str(command_path),
            response_path=str(response_path),
            created_at=timestamp,
            last_progress_at=timestamp,
        )
        self.write(record)
        self.append_event(record, None, STATE_QUEUED, "created", None)
        return record

    def load(self, command_id: str) -> OperationRecord | None:
        """Load the latest operation record, if present."""
        path = self.record_path(command_id)
        if not path.exists():
            return None
        last_exc: Exception | None = None
        for attempt in range(_LEDGER_WRITE_ATTEMPTS):
            try:
                return OperationRecord.from_dict(json.loads(path.read_text(encoding="utf-8-sig")))
            except FileNotFoundError:
                return None
            except (
                PermissionError,
                OSError,
                UnicodeDecodeError,
                json.JSONDecodeError,
                KeyError,
                ValueError,
            ) as exc:
                last_exc = exc
                if attempt < _LEDGER_WRITE_ATTEMPTS - 1:
                    time.sleep(_LEDGER_WRITE_BASE_DELAY * (2**attempt))
        logger.warning(
            "Ledger read failed for %s after %d attempts: %s",
            path,
            _LEDGER_WRITE_ATTEMPTS,
            last_exc,
        )
        return None

    def list_records(
        self,
        *,
        include_terminal: bool = False,
        limit: int = 50,
    ) -> list[OperationRecord]:
        """List operation records, newest progress first."""
        records: list[OperationRecord] = []
        for path in self.operations_path.glob("*.json"):
            try:
                record = OperationRecord.from_dict(json.loads(path.read_text(encoding="utf-8-sig")))
            except (json.JSONDecodeError, KeyError, OSError):
                continue
            if include_terminal or not record.is_terminal:
                records.append(record)
        records.sort(key=lambda item: item.last_progress_at or "", reverse=True)
        return records[:limit]

    def cleanup_terminal(
        self,
        *,
        older_than: datetime,
        dry_run: bool = False,
    ) -> tuple[list[str], list[str]]:
        """Delete terminal operation snapshots/events older than a cutoff."""
        deleted: list[str] = []
        skipped: list[str] = []
        for record in self.list_records(include_terminal=True, limit=10_000):
            if not record.is_terminal:
                skipped.append(str(self.record_path(record.command_id)))
                continue
            terminal_at = _parse_optional_datetime(record.terminal_at)
            if terminal_at is None or terminal_at >= older_than:
                skipped.append(str(self.record_path(record.command_id)))
                continue
            targets = [self.record_path(record.command_id), self.events_path(record.command_id)]
            for path in targets:
                if not path.exists():
                    continue
                if dry_run:
                    deleted.append(str(path))
                else:
                    try:
                        path.unlink()
                        deleted.append(str(path))
                    except OSError:
                        skipped.append(str(path))
        return deleted, skipped

    def write(self, record: OperationRecord) -> None:
        """Atomically write a current-state record (best-effort, never raises)."""
        path = self.record_path(record.command_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        content = json.dumps(record.to_dict(), indent=2)

        def _do() -> None:
            # Unique temp name so concurrent writers never collide on the temp.
            temp = path.with_suffix(f".{uuid.uuid4().hex}.tmp")
            try:
                temp.write_text(content, encoding="utf-8")
                temp.replace(path)
            except BaseException:
                temp.unlink(missing_ok=True)
                raise

        _best_effort_write(_do, path)

    def transition(
        self,
        command_id: str,
        to_state: str,
        *,
        reason: str | None = None,
        busy_reason: str | None = None,
    ) -> OperationRecord | None:
        """Load, transition, write, and append a JSONL event."""
        current = self.load(command_id)
        if current is None:
            return None
        if current.is_terminal and current.state != to_state:
            self.append_event(current, current.state, current.state, "ignored_transition", reason)
            return current
        previous = current.state
        try:
            updated = OperationStateMachine.transition(
                current,
                to_state,
                reason=reason,
                busy_reason=busy_reason,
            )
        except ValueError:
            # The other writer (the C# bridge) advanced the record to a state we
            # cannot legally transition from. Do not clobber its progress.
            self.append_event(current, current.state, to_state, "rejected_transition", reason)
            return current
        # Re-load immediately before writing: if the other writer advanced to a
        # terminal state between our load and write, keep the terminal state
        # rather than regressing it (best-effort guard for the cross-process race).
        latest = self.load(command_id)
        if latest is not None and latest.is_terminal and not updated.is_terminal:
            self.append_event(
                latest, current.state, to_state, "skipped_concurrent_terminal", reason
            )
            return latest
        self.write(updated)
        self.append_event(updated, previous, to_state, "transition", reason)
        return updated

    def append_event(
        self,
        record: OperationRecord,
        from_state: str | None,
        to_state: str,
        event_type: str,
        reason: str | None,
    ) -> None:
        """Append a diagnostic transition event as JSONL."""
        event = {
            "schemaVersion": SCHEMA_VERSION,
            "timestamp": _utc_now(),
            "commandId": record.command_id,
            "commandType": record.command_type,
            "fromState": from_state,
            "toState": to_state,
            "eventType": event_type,
            "reason": reason,
            "domainGeneration": record.domain_generation,
        }
        path = self.events_path(record.command_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        line = json.dumps(event) + "\n"

        def _do() -> None:
            with path.open("a", encoding="utf-8") as handle:
                handle.write(line)

        _best_effort_write(_do, path)


def parameters_hash(parameters: dict[str, Any] | None) -> str:
    """Return a stable SHA-256 hash for command parameters."""
    payload = json.dumps(parameters or {}, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def retry_policy_for_command(command_type: str) -> str:
    """Classify a command for post-acceptance retry decisions."""
    try:
        from unity_bridge.core.protocol import PARALLEL_SAFE_COMMANDS
    except ImportError:
        PARALLEL_SAFE_COMMANDS = set()
    if command_type in PARALLEL_SAFE_COMMANDS:
        return RETRY_READ_ONLY
    return RETRY_NON_IDEMPOTENT


def terminal_state_for_response_status(status: str) -> str | None:
    """Map bridge response status to an operation state."""
    if status == "success":
        return STATE_COMPLETED
    if status == "error":
        return STATE_FAILED
    return None


def _touch(
    record: OperationRecord,
    to_state: str,
    reason: str | None,
    busy_reason: str | None,
) -> OperationRecord:
    timestamp = _utc_now()
    updates: dict[str, Any] = {
        "state": to_state,
        "last_progress_at": timestamp,
        "last_busy_reason": busy_reason or record.last_busy_reason,
        "last_error": reason if reason else record.last_error,
    }
    if to_state == STATE_ACCEPTED and record.accepted_at is None:
        updates["accepted_at"] = timestamp
    if to_state == STATE_RUNNING and record.started_at is None:
        updates["started_at"] = timestamp
    if to_state in TERMINAL_STATES and record.terminal_at is None:
        updates["terminal_at"] = timestamp
    return replace(record, **updates)
