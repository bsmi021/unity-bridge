"""Parity registry seeding and evaluation."""

from __future__ import annotations

from typing import Any

from .models import CLASSIFICATIONS


def seed_registry(surface: dict[str, Any]) -> dict[str, Any]:
    """Create an explicit classification registry from a discovered surface."""
    producer_by_id = _producers_by_id(surface)
    records = []
    for operation in surface["csharp_operations"]:
        candidates = producer_by_id.get(operation["id"], [])
        typed = next((item for item in candidates if item["cli_paths"]), None)
        records.append(_seed_record(operation, typed))
    return {
        "schema_version": "1.0",
        "surface": {
            "handlers": [item["id"] for item in surface["handlers"]],
            "python_command_types": surface["python_command_types"],
            "python_operations": surface["python_operations"],
            "cli_leaves": [item["path"] for item in surface["cli_leaves"]],
        },
        "records": records,
    }


def evaluate_registry(surface: dict[str, Any], registry: dict[str, Any]) -> dict[str, Any]:
    """Compare *surface* with *registry* and return a deterministic report."""
    current = _current_sets(surface)
    recorded = registry.get("surface", {})
    record_list = registry.get("records", [])
    record_map = {item.get("id"): item for item in record_list}
    unclassified = sorted(current["operations"] - set(record_map))
    removed_operations = sorted(set(record_map) - current["operations"])
    field_mismatches = _field_mismatches(surface, record_map)
    unsupported_python = _unsupported_python_operations(surface, current["operations"])
    without_sender = _without_sender(surface)
    diffs = _surface_diffs(current, recorded)
    invalid_records = _invalid_records(record_list)
    classification_counts = _classification_counts(record_map, current["operations"])
    gaps = sum(
        len(items)
        for items in [
            unclassified,
            removed_operations,
            field_mismatches,
            unsupported_python,
            without_sender,
            invalid_records,
            *diffs.values(),
        ]
    )
    counts = _surface_counts(surface, classification_counts, gaps)
    return {
        "schema_version": "1.0",
        "counts": counts,
        "unclassified_csharp_operations": unclassified,
        "removed_csharp_operations": removed_operations,
        "invalid_registry_records": invalid_records,
        "registered_without_python_sender": without_sender,
        "field_name_mismatches": field_mismatches,
        "python_operations_without_csharp_dispatch": unsupported_python,
        **diffs,
        "is_complete": gaps == 0,
    }


def _current_sets(surface: dict[str, Any]) -> dict[str, set[str]]:
    return {
        "handlers": {item["id"] for item in surface["handlers"]},
        "operations": {item["id"] for item in surface["csharp_operations"]},
        "python_command_types": set(surface["python_command_types"]),
        "python_operations": set(surface["python_operations"]),
        "cli_leaves": {item["path"] for item in surface["cli_leaves"]},
    }


def _surface_diffs(current: dict[str, set[str]], recorded: dict[str, Any]) -> dict[str, list[str]]:
    diffs = {}
    for key in ("handlers", "python_command_types", "python_operations", "cli_leaves"):
        previous = set(recorded.get(key, []))
        diffs[f"added_{key}"] = sorted(current[key] - previous)
        diffs[f"removed_{key}"] = sorted(previous - current[key])
    return diffs


def _without_sender(surface: dict[str, Any]) -> list[str]:
    raw_submit_available = any(item["path"] == "operation submit" for item in surface["cli_leaves"])
    if raw_submit_available:
        return []
    registered_types = {item["command_type"] for item in surface["handlers"]}
    return sorted(registered_types - set(surface["python_command_types"]))


def _unsupported_python_operations(
    surface: dict[str, Any], csharp_operations: set[str]
) -> list[str]:
    concrete = {
        item["id"] for item in surface["python_producers"] if item["operation_variable"] is None
    }
    return sorted(concrete - csharp_operations)


def _surface_counts(
    surface: dict[str, Any], classifications: dict[str, int], gaps: int
) -> dict[str, int]:
    return {
        "handlers": len(surface["handlers"]),
        "csharp_operations": len(surface["csharp_operations"]),
        "python_command_types": len(surface["python_command_types"]),
        "python_operations": len(surface["python_operations"]),
        "cli_leaves": len(surface["cli_leaves"]),
        **classifications,
        "gaps": gaps,
    }


def _seed_record(operation: dict[str, Any], typed: dict[str, Any] | None) -> dict[str, Any]:
    base = {
        "id": operation["id"],
        "command_type": operation["command_type"],
        "operation": operation["operation"],
        "proof": [f"csharp:{path}" for path in operation["proof"]],
    }
    if typed is None:
        return _raw_record(base, operation["command_type"])
    cli_path = typed["cli_paths"][0]
    return {
        **base,
        "classification": "typed_cli",
        "cli_path": cli_path,
        "rationale": "Exact CLI leaf reaches a matching Python bridge payload producer.",
        "proof": [*base["proof"], f"python:{typed['source']}", f"cli:{cli_path}"],
    }


def _raw_record(base: dict[str, Any], command_type: str) -> dict[str, Any]:
    return {
        **base,
        "classification": "raw_only",
        "rationale": "Registered bridge operation has no verified exact typed CLI leaf.",
        "proof": [*base["proof"], f"raw:operation submit {command_type}"],
    }


def _field_mismatches(
    surface: dict[str, Any], records: dict[str | None, dict[str, Any]]
) -> list[dict[str, Any]]:
    csharp = {item["id"]: item for item in surface["csharp_operations"]}
    producers = _producers_by_id(surface)
    mismatches = []
    for identifier, record in sorted(records.items(), key=lambda item: str(item[0])):
        mismatch = _field_mismatch(identifier, record, csharp, producers)
        if mismatch:
            mismatches.append(mismatch)
    return mismatches


def _field_mismatch(
    identifier: str | None,
    record: dict[str, Any],
    csharp: dict[str, dict[str, Any]],
    producers: dict[str, list[dict[str, Any]]],
) -> dict[str, Any] | None:
    if record.get("classification") != "typed_cli" or identifier not in csharp:
        return None
    cli_path = record.get("cli_path")
    candidates = [item for item in producers.get(identifier, []) if cli_path in item["cli_paths"]]
    csharp_fields = csharp[identifier]["fields"]
    if not candidates or not csharp_fields:
        return None
    python_fields = {field for item in candidates for field in item["fields"]}
    python_only = sorted(python_fields - set(csharp_fields))
    if not python_only:
        return None
    return {
        "id": identifier,
        "cli_path": cli_path,
        "python_only": python_only,
        "csharp_fields": csharp_fields,
    }


def _invalid_records(records: list[dict[str, Any]]) -> list[str]:
    invalid, seen = [], set()
    for index, record in enumerate(records):
        identifier = record.get("id")
        reasons = _record_errors(record, identifier in seen)
        if isinstance(identifier, str):
            seen.add(identifier)
        if reasons:
            invalid.append(f"record[{index}] {identifier!r}: {', '.join(reasons)}")
    return invalid


def _record_errors(record: dict[str, Any], duplicate: bool) -> list[str]:
    identifier = record.get("id")
    reasons = []
    if not isinstance(identifier, str) or not identifier:
        reasons.append("missing id")
    elif duplicate:
        reasons.append("duplicate id")
    if record.get("classification") not in CLASSIFICATIONS:
        reasons.append("invalid classification")
    if not record.get("rationale"):
        reasons.append("missing rationale")
    if not record.get("proof"):
        reasons.append("missing proof")
    if record.get("classification") == "typed_cli" and not record.get("cli_path"):
        reasons.append("typed_cli missing cli_path")
    return reasons


def _classification_counts(
    records: dict[str | None, dict[str, Any]], current: set[str]
) -> dict[str, int]:
    counts = {name: 0 for name in sorted(CLASSIFICATIONS)}
    classified = 0
    for identifier in current:
        record = records.get(identifier)
        if record and record.get("classification") in counts:
            counts[record["classification"]] += 1
            classified += 1
    return {"classified": classified, **counts}


def _producers_by_id(surface: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    result: dict[str, list[dict[str, Any]]] = {}
    for producer in surface["python_producers"]:
        result.setdefault(producer["id"], []).append(producer)
    return result
