"""Python bridge-payload producer discovery."""

from __future__ import annotations

import ast
from dataclasses import replace
from pathlib import Path
from typing import Iterable

from .models import FunctionFacts, PythonProducer


def discover_python(
    root: Path,
) -> tuple[list[PythonProducer], dict[str, FunctionFacts]]:
    """Discover bridge command producers and their local call graphs."""
    command_root = root / "src" / "unity_bridge" / "commands"
    producers: list[PythonProducer] = []
    all_facts: dict[str, FunctionFacts] = {}
    for path in sorted(command_root.glob("*.py")):
        module = f"unity_bridge.commands.{path.stem}"
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        source = path.relative_to(root).as_posix()
        module_producers, facts = _python_module_facts(tree, module, source)
        producers.extend(_concretize_dynamic(module_producers, facts))
        all_facts.update({f"{module}:{name}": value for name, value in facts.items()})
    unique = {_producer_key(item): item for item in producers}
    return sorted(unique.values(), key=_producer_sort_key), all_facts


def _python_module_facts(
    tree: ast.Module, module: str, source_path: str
) -> tuple[list[PythonProducer], dict[str, FunctionFacts]]:
    producers = []
    facts: dict[str, FunctionFacts] = {}
    functions = [
        node for node in tree.body if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    ]
    for function in functions:
        assignments = _dict_assignments(function)
        calls = tuple(_local_calls(function))
        parameters = tuple(arg.arg for arg in function.args.args + function.args.kwonlyargs)
        facts[function.name] = FunctionFacts(parameters=parameters, calls=calls)
        producers.extend(_function_producers(function, module, source_path, assignments))
    return producers, facts


def _function_producers(
    function: ast.FunctionDef | ast.AsyncFunctionDef,
    module: str,
    source_path: str,
    assignments: dict[str, tuple[set[str], ast.expr | None]],
) -> list[PythonProducer]:
    producers = []
    for call in ast.walk(function):
        if not isinstance(call, ast.Call) or _call_name(call) not in {
            "send_command",
            "send_command_with_retry",
        }:
            continue
        command_type = _string_value(_call_argument(call, "command_type", 0))
        if command_type is None:
            continue
        params_expr = _call_argument(call, "parameters", 1)
        fields, operation, variable = _parameter_contract(params_expr, assignments)
        producers.append(
            PythonProducer(
                command_type=command_type,
                operation=operation,
                operation_variable=variable,
                fields=tuple(sorted(fields)),
                module=module,
                function=function.name,
                source=f"{source_path}:{getattr(call, 'lineno', 1)}",
            )
        )
    return producers


def _dict_assignments(function: ast.AST) -> dict[str, tuple[set[str], ast.expr | None]]:
    assignments: dict[str, tuple[set[str], ast.expr | None]] = {}
    for node in ast.walk(function):
        target, value = _assignment_parts(node)
        if isinstance(target, ast.Name) and isinstance(value, ast.Dict):
            fields, operation, _ = _literal_dict(value)
            assignments[target.id] = (fields, operation)
        if isinstance(target, ast.Subscript) and isinstance(target.value, ast.Name):
            key = _string_value(target.slice)
            if key and target.value.id in assignments:
                assignments[target.value.id][0].add(key)
    return assignments


def _assignment_parts(node: ast.AST) -> tuple[ast.expr | None, ast.expr | None]:
    if isinstance(node, ast.Assign):
        return node.targets[0], node.value
    if isinstance(node, ast.AnnAssign):
        return node.target, node.value
    return None, None


def _parameter_contract(
    expression: ast.expr | None,
    assignments: dict[str, tuple[set[str], ast.expr | None]],
) -> tuple[set[str], str | None, str | None]:
    if isinstance(expression, ast.Dict):
        fields, operation_expression, operation = _literal_dict(expression)
    elif isinstance(expression, ast.Name) and expression.id in assignments:
        fields, operation_expression = assignments[expression.id]
        fields, operation = set(fields), _string_value(operation_expression)
    elif expression is not None:
        return set(), None, "unknown"
    else:
        return set(), None, None
    variable = operation_expression.id if isinstance(operation_expression, ast.Name) else None
    return fields, operation, variable


def _literal_dict(value: ast.Dict) -> tuple[set[str], ast.expr | None, str | None]:
    fields: set[str] = set()
    operation_expression = None
    for key, item in zip(value.keys, value.values):
        name = _string_value(key)
        if name is None:
            continue
        fields.add(name)
        if name == "operation":
            operation_expression = item
    return fields, operation_expression, _string_value(operation_expression)


def _concretize_dynamic(
    producers: list[PythonProducer], facts: dict[str, FunctionFacts]
) -> list[PythonProducer]:
    result = list(producers)
    frontier = [item for item in producers if item.operation_variable]
    seen = {_producer_key(item) for item in result}
    for _ in range(6):
        additions = _concrete_additions(frontier, facts, seen)
        result.extend(additions)
        frontier = [item for item in additions if item.operation_variable]
        if not frontier:
            break
    return result


def _concrete_additions(
    frontier: list[PythonProducer],
    facts: dict[str, FunctionFacts],
    seen: set[tuple[object, ...]],
) -> list[PythonProducer]:
    additions = []
    for producer in frontier:
        for caller, caller_facts in facts.items():
            for callee, args, keywords in caller_facts.calls:
                candidate = _concrete_candidate(producer, caller, callee, args, keywords, facts)
                if candidate and _producer_key(candidate) not in seen:
                    additions.append(candidate)
                    seen.add(_producer_key(candidate))
    return additions


def _concrete_candidate(
    producer: PythonProducer,
    caller: str,
    callee: str,
    args: tuple[ast.expr, ...],
    keywords: dict[str, ast.expr],
    facts: dict[str, FunctionFacts],
) -> PythonProducer | None:
    if callee != producer.function:
        return None
    expression = _bound_argument(
        producer.operation_variable or "", facts[callee].parameters, args, keywords
    )
    operation = _string_value(expression)
    variable = expression.id if isinstance(expression, ast.Name) else None
    if operation is None and variable is None:
        return None
    return replace(
        producer,
        operation=operation,
        operation_variable=variable,
        function=caller,
    )


def _local_calls(
    function: ast.AST,
) -> Iterable[tuple[str, tuple[ast.expr, ...], dict[str, ast.expr]]]:
    for node in ast.walk(function):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            keywords = {item.arg: item.value for item in node.keywords if item.arg}
            yield node.func.id, tuple(node.args), keywords


def _call_name(call: ast.Call) -> str:
    if isinstance(call.func, ast.Attribute):
        return call.func.attr
    if isinstance(call.func, ast.Name):
        return call.func.id
    return ""


def _call_argument(call: ast.Call, keyword: str, position: int) -> ast.expr | None:
    for item in call.keywords:
        if item.arg == keyword:
            return item.value
    return call.args[position] if len(call.args) > position else None


def _bound_argument(
    name: str,
    parameters: tuple[str, ...],
    arguments: tuple[ast.expr, ...],
    keywords: dict[str, ast.expr],
) -> ast.expr | None:
    if name in keywords:
        return keywords[name]
    if name not in parameters:
        return None
    index = parameters.index(name)
    return arguments[index] if index < len(arguments) else None


def _string_value(value: ast.expr | None) -> str | None:
    return value.value if isinstance(value, ast.Constant) and isinstance(value.value, str) else None


def _producer_key(item: PythonProducer) -> tuple[object, ...]:
    return (
        item.command_type,
        item.operation,
        item.operation_variable,
        item.fields,
        item.module,
        item.function,
    )


def _producer_sort_key(item: PythonProducer) -> tuple[object, ...]:
    return (item.identifier, item.module, item.function, item.fields)
