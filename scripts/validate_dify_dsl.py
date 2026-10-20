#!/usr/bin/env python3
"""Validate a Dify app DSL YAML file for structural and workflow invariants.

This is a structural validator. It does not import the file into Dify.
Exit code 0 with VALIDATION_OK means all deterministic checks passed.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from typing import Any, Iterable

try:
    import yaml
except ImportError:  # pragma: no cover
    print("ERROR: PyYAML is required: pip install pyyaml", file=sys.stderr)
    raise SystemExit(2)

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


GRAPH_MODES = {"workflow", "advanced-chat", "agent-chat"}
SIMPLE_MODES = {"chat", "completion"}
ALL_MODES = GRAPH_MODES | SIMPLE_MODES

TERMINAL_TYPES = {"end", "answer"}
INTERNAL_TYPES = {"iteration-start", "loop-start"}

NODE_TYPES = {
    "start",
    "end",
    "answer",
    "llm",
    "knowledge-retrieval",
    "question-classifier",
    "if-else",
    "code",
    "template-transform",
    "http-request",
    "variable-aggregator",
    "variable-assigner",
    "parameter-extractor",
    "document-extractor",
    "iteration",
    "loop",
    "agent",
    "tool",
    "datasource",
    "trigger",
    "iteration-start",
    "loop-start",
}

FIXED_OUTPUTS: dict[str, set[str]] = {
    "end": set(),
    "answer": set(),
    "llm": {"text", "reasoning_content", "usage", "finish_reason", "structured_output"},
    "knowledge-retrieval": {"result"},
    "question-classifier": {"class_name", "class_id"},
    "if-else": set(),
    "template-transform": {"output"},
    "http-request": {"body", "status_code", "headers", "files"},
    "variable-aggregator": {"output"},
    "variable-assigner": set(),
    "document-extractor": {"text"},
    "iteration": {"output"},
    "loop": {"output"},
    "agent": {"text", "files", "json"},
    "tool": {"text", "files", "json"},
}

DYNAMIC_OUTPUT_TYPES = {"start", "code", "parameter-extractor"}

SYS_VARS = {
    "query",
    "files",
    "conversation_id",
    "user_id",
    "dialogue_count",
    "app_id",
    "workflow_id",
    "workflow_run_id",
    "timestamp",
    "tenant_id",
    "user_name",
}

VARIABLE_TYPES = {
    "text-input",
    "paragraph",
    "select",
    "number",
    "file",
    "file-list",
    "checkbox",
    "json",
}

COMPARISON_OPERATORS = {
    "contains",
    "not contains",
    "not_contains",
    "start with",
    "start_with",
    "end with",
    "end_with",
    "is",
    "is not",
    "is_not",
    "empty",
    "not empty",
    "not_empty",
    "=",
    "!=",
    "≠",
    ">",
    "<",
    ">=",
    "≥",
    "<=",
    "≤",
    "in",
    "not in",
    "not_in",
    "all of",
    "all_of",
    "exists",
    "not exists",
    "not_exists",
    "before",
    "after",
}

HTTP_METHODS = {"get", "post", "put", "patch", "delete", "head", "options"}
HTTP_BODY_TYPES = {"none", "json", "form-data", "x-www-form-urlencoded", "raw-text", "binary"}
AUTH_TYPES = {"no-auth", "api-key"}

MOJIBAKE_MARKERS = ("�", "鐢", "鏂", "绯", "鈫", "�")
TEMPLATE_REF_RE = re.compile(r"\{\{#([^#{}]+)#\}\}")
JINJA_VAR_RE = re.compile(r"\{\{\s*([A-Za-z_][A-Za-z0-9_]*)")
SAFE_NAME_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
VERSION_RE = re.compile(r"^\d+\.\d+\.\d+$")


class Report:
    def __init__(self) -> None:
        self.errors: list[str] = []
        self.warnings: list[str] = []

    def error(self, message: str) -> None:
        self.errors.append(message)

    def warn(self, message: str) -> None:
        self.warnings.append(message)

    def has_blocking_errors(self) -> bool:
        return bool(self.errors)


def as_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def nonempty_str(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def node_type(node: dict[str, Any]) -> str | None:
    data = node.get("data")
    if isinstance(data, dict):
        value = data.get("type")
        return value if isinstance(value, str) else None
    return None


def node_data(node: dict[str, Any]) -> dict[str, Any]:
    return as_dict(node.get("data"))


def is_selector(value: Any) -> bool:
    return (
        isinstance(value, list)
        and len(value) == 2
        and isinstance(value[0], str)
        and isinstance(value[1], str)
        and bool(value[0])
        and bool(value[1])
    )


def iter_template_refs(value: Any) -> Iterable[tuple[str, str]]:
    if isinstance(value, str):
        for match in TEMPLATE_REF_RE.findall(value):
            if "." in match:
                yield tuple(match.split(".", 1))  # type: ignore[arg-type]
    elif isinstance(value, list):
        for item in value:
            yield from iter_template_refs(item)
    elif isinstance(value, dict):
        for item in value.values():
            yield from iter_template_refs(item)


def iter_selector_fields(value: Any, node_ids: set[str], path: str = "") -> Iterable[tuple[list[str], str]]:
    """Find selector-shaped arrays without recursing into the selector itself."""
    if isinstance(value, list):
        if is_selector(value) and (value[0] in node_ids or value[0] in {"sys", "env", "conversation"}):
            yield value, path
            return
        for index, item in enumerate(value):
            yield from iter_selector_fields(item, node_ids, f"{path}[{index}]")
    elif isinstance(value, dict):
        for key, item in value.items():
            yield from iter_selector_fields(item, node_ids, f"{path}.{key}")


def reachable(upstream: str, downstream: str, incoming: dict[str, set[str]]) -> bool:
    if upstream == downstream:
        return False
    seen: set[str] = set()
    stack = list(incoming.get(downstream, set()))
    while stack:
        current = stack.pop()
        if current == upstream:
            return True
        if current in seen:
            continue
        seen.add(current)
        stack.extend(incoming.get(current, set()) - seen)
    return False


def require_dict(report: Report, value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        report.error(f"{label} must be a mapping/object")
        return {}
    return value


def require_list(report: Report, value: Any, label: str) -> list[Any]:
    if not isinstance(value, list):
        report.error(f"{label} must be a list")
        return []
    return value


def validate_model(report: Report, model: Any, label: str) -> None:
    data = require_dict(report, model, label)
    if not data:
        return
    for key in ("provider", "name", "mode"):
        if not nonempty_str(data.get(key)):
            report.error(f"{label}.{key} must be a non-empty string")
    if data.get("mode") not in {"chat", "completion"}:
        report.error(f"{label}.mode must be 'chat' or 'completion'")
    if not isinstance(data.get("completion_params"), dict):
        report.error(f"{label}.completion_params must be a mapping/object")


def validate_start(report: Report, data: dict[str, Any], file_upload_enabled: bool, mode: str) -> None:
    variables = require_list(report, data.get("variables"), "start.variables")
    seen: set[str] = set()
    for index, variable in enumerate(variables):
        label = f"start.variables[{index}]"
        item = require_dict(report, variable, label)
        name = item.get("variable")
        if not nonempty_str(name) or not SAFE_NAME_RE.match(str(name)):
            report.error(f"{label}.variable must be a safe identifier")
            continue
        if name in seen:
            report.error(f"{label}.variable duplicated: {name}")
        seen.add(name)
        vtype = item.get("type")
        if vtype not in VARIABLE_TYPES:
            report.error(f"{label}.type is invalid: {vtype!r}")
        if vtype == "select":
            options = require_list(report, item.get("options"), f"{label}.options")
            if not options:
                report.error(f"{label}.options must be non-empty for select")
        if vtype in {"file", "file-list"} and not file_upload_enabled:
            report.error(f"{label} is a file input but workflow.features.file_upload.enabled is false")
        if vtype == "text-input":
            max_length = item.get("max_length")
            if max_length is not None and (not isinstance(max_length, int) or max_length <= 0):
                report.error(f"{label}.max_length must be a positive integer")
    if mode == "workflow" and not variables:
        report.warn("workflow mode has no start variables; confirm the app needs no user input")


def validate_end(report: Report, data: dict[str, Any]) -> None:
    outputs = require_list(report, data.get("outputs"), "end.outputs")
    if not outputs:
        report.error("end.outputs must be non-empty")
    seen: set[str] = set()
    for index, output in enumerate(outputs):
        label = f"end.outputs[{index}]"
        item = require_dict(report, output, label)
        name = item.get("variable")
        if not nonempty_str(name) or not SAFE_NAME_RE.match(str(name)):
            report.error(f"{label}.variable must be a safe identifier")
        elif name in seen:
            report.error(f"{label}.variable duplicated: {name}")
        else:
            seen.add(name)
        selector = item.get("value_selector")
        if not is_selector(selector):
            report.error(f"{label}.value_selector must be [nodeId, outputKey]")


def validate_answer(report: Report, data: dict[str, Any]) -> None:
    answer = data.get("answer")
    if not nonempty_str(answer):
        report.error("answer.answer must be a non-empty string")
    if "variables" in data:
        require_list(report, data.get("variables"), "answer.variables")


def validate_llm(report: Report, data: dict[str, Any]) -> None:
    validate_model(report, data.get("model"), "llm.model")
    prompts = require_list(report, data.get("prompt_template"), "llm.prompt_template")
    if not prompts:
        report.error("llm.prompt_template must be non-empty")
    has_user = False
    prompt_texts: list[str] = []
    for index, prompt in enumerate(prompts):
        label = f"llm.prompt_template[{index}]"
        item = require_dict(report, prompt, label)
        role = item.get("role")
        if role not in {"system", "user", "assistant"}:
            report.error(f"{label}.role must be system/user/assistant")
        if not isinstance(item.get("text"), str):
            report.error(f"{label}.text must be a string")
        else:
            prompt_texts.append(item["text"])
        if role == "user":
            has_user = True
    memory_value = data.get("memory")
    memory = require_dict(report, memory_value, "llm.memory") if memory_value is not None else {}
    query_prompt = memory.get("query_prompt_template") if memory else None
    if query_prompt is not None and not isinstance(query_prompt, str):
        report.error("llm.memory.query_prompt_template must be a string")
    if memory:
        role_prefix = require_dict(report, memory.get("role_prefix"), "llm.memory.role_prefix")
        if role_prefix:
            for key in ("assistant", "user"):
                if key in role_prefix and not isinstance(role_prefix.get(key), str):
                    report.error(f"llm.memory.role_prefix.{key} must be a string")
        window = require_dict(report, memory.get("window"), "llm.memory.window")
        if window:
            if "enabled" in window and not isinstance(window.get("enabled"), bool):
                report.error("llm.memory.window.enabled must be a boolean")
            if "size" in window and (not isinstance(window.get("size"), int) or window.get("size") <= 0):
                report.error("llm.memory.window.size must be a positive integer")
    if not has_user and not (isinstance(query_prompt, str) and query_prompt.strip()):
        if not any("{{#sys.query#}}" in text for text in prompt_texts):
            report.warn("llm.prompt_template has no user message and no sys.query reference")
    variables = require_list(report, data.get("variables", []), "llm.variables")
    for index, variable in enumerate(variables):
        label = f"llm.variables[{index}]"
        item = require_dict(report, variable, label)
        if not nonempty_str(item.get("variable")):
            report.error(f"{label}.variable must be a non-empty string")
        if not is_selector(item.get("value_selector")):
            report.error(f"{label}.value_selector must be [nodeId, outputKey]")
    context = require_dict(report, data.get("context"), "llm.context")
    if context:
        if not isinstance(context.get("enabled"), bool):
            report.error("llm.context.enabled must be a boolean")
        if context.get("enabled") is True and not is_selector(context.get("variable_selector")):
            report.error("llm.context.variable_selector must be [nodeId, outputKey] when enabled")
    vision = require_dict(report, data.get("vision"), "llm.vision")
    if vision and not isinstance(vision.get("enabled"), bool):
        report.error("llm.vision.enabled must be a boolean")


def validate_knowledge(report: Report, data: dict[str, Any]) -> None:
    dataset_ids = require_list(report, data.get("dataset_ids"), "knowledge-retrieval.dataset_ids")
    if not dataset_ids:
        report.warn("knowledge-retrieval.dataset_ids is empty; replace with a real dataset ID before use")
    for index, dataset_id in enumerate(dataset_ids):
        if not nonempty_str(dataset_id):
            report.error(f"knowledge-retrieval.dataset_ids[{index}] must be a non-empty string")
        elif "placeholder" in str(dataset_id).lower():
            report.warn("knowledge-retrieval.dataset_ids contains a placeholder")
    mode = data.get("retrieval_mode")
    if mode not in {"single", "multiple"}:
        report.error("knowledge-retrieval.retrieval_mode must be 'single' or 'multiple'")
    if not is_selector(data.get("query_variable_selector")):
        report.error("knowledge-retrieval.query_variable_selector must be [nodeId, outputKey]")
    if mode == "multiple":
        config = require_dict(report, data.get("multiple_retrieval_config"), "knowledge-retrieval.multiple_retrieval_config")
        if config:
            top_k = config.get("top_k")
            if not isinstance(top_k, int) or top_k <= 0:
                report.error("knowledge-retrieval.multiple_retrieval_config.top_k must be a positive integer")
            if not isinstance(config.get("reranking_enable"), bool):
                report.error("knowledge-retrieval.multiple_retrieval_config.reranking_enable must be a boolean")
    elif mode == "single" and not isinstance(data.get("single_retrieval_config"), dict):
        report.error("knowledge-retrieval.single_retrieval_config is required when retrieval_mode is 'single'")


def validate_classifier(report: Report, data: dict[str, Any]) -> None:
    validate_model(report, data.get("model"), "question-classifier.model")
    if not is_selector(data.get("query_variable_selector")):
        report.error("question-classifier.query_variable_selector must be [nodeId, outputKey]")
    classes = require_list(report, data.get("classes"), "question-classifier.classes")
    if not classes:
        report.error("question-classifier.classes must be non-empty")
    seen: set[str] = set()
    for index, cls in enumerate(classes):
        label = f"question-classifier.classes[{index}]"
        item = require_dict(report, cls, label)
        class_id = item.get("id")
        if not nonempty_str(class_id):
            report.error(f"{label}.id must be a non-empty string")
        elif class_id in seen:
            report.error(f"{label}.id duplicated: {class_id}")
        else:
            seen.add(class_id)
        if not nonempty_str(item.get("name")):
            report.error(f"{label}.name must be a non-empty string")


def validate_ifelse(report: Report, data: dict[str, Any]) -> None:
    cases = require_list(report, data.get("cases"), "if-else.cases")
    if not cases:
        report.error("if-else.cases must be non-empty")
    seen: set[str] = set()
    for index, case in enumerate(cases):
        label = f"if-else.cases[{index}]"
        item = require_dict(report, case, label)
        case_id = item.get("case_id")
        if not nonempty_str(case_id):
            report.error(f"{label}.case_id must be a non-empty string")
        elif case_id == "false":
            report.error(f"{label}.case_id 'false' is reserved for the else branch")
        elif case_id in seen:
            report.error(f"{label}.case_id duplicated: {case_id}")
        else:
            seen.add(case_id)
        if item.get("logical_operator") not in {"and", "or"}:
            report.error(f"{label}.logical_operator must be 'and' or 'or'")
        conditions = require_list(report, item.get("conditions"), f"{label}.conditions")
        if not conditions:
            report.error(f"{label}.conditions must be non-empty")
        for cindex, condition in enumerate(conditions):
            clabel = f"{label}.conditions[{cindex}]"
            cond = require_dict(report, condition, clabel)
            if not nonempty_str(cond.get("id")):
                report.error(f"{clabel}.id must be a non-empty string")
            operator = cond.get("comparison_operator")
            if operator not in COMPARISON_OPERATORS:
                report.error(f"{clabel}.comparison_operator is invalid: {operator!r}")
            if not is_selector(cond.get("variable_selector")):
                report.error(f"{clabel}.variable_selector must be [nodeId, outputKey]")
            if operator not in {"empty", "not empty", "not_empty", "exists", "not exists", "not_exists"} and "value" not in cond:
                report.error(f"{clabel}.value is required for comparison operator {operator!r}")


def validate_code(report: Report, data: dict[str, Any]) -> None:
    language = data.get("code_language")
    if language not in {"python3", "javascript"}:
        report.error("code.code_language must be 'python3' or 'javascript'")
    code = data.get("code")
    if not nonempty_str(code):
        report.error("code.code must be a non-empty string")
    elif language == "python3" and not re.search(r"def\s+main\s*\(", code):
        report.warn("code.code does not define main() for python3")
    elif language == "javascript" and not re.search(r"function\s+main\s*\(", code):
        report.warn("code.code does not define main() for javascript")
    outputs = require_dict(report, data.get("outputs"), "code.outputs")
    if not outputs:
        report.error("code.outputs must be a non-empty mapping")
    for key, output in outputs.items():
        label = f"code.outputs.{key}"
        if not nonempty_str(key) or not SAFE_NAME_RE.match(str(key)):
            report.error(f"{label}: output key must be a safe identifier")
        item = require_dict(report, output, label)
        if not nonempty_str(item.get("type")):
            report.error(f"{label}.type must be a non-empty string")
    variables = require_list(report, data.get("variables"), "code.variables")
    for index, variable in enumerate(variables):
        label = f"code.variables[{index}]"
        item = require_dict(report, variable, label)
        if not nonempty_str(item.get("variable")):
            report.error(f"{label}.variable must be a non-empty string")
        if not is_selector(item.get("value_selector")):
            report.error(f"{label}.value_selector must be [nodeId, outputKey]")


def validate_template_transform(report: Report, data: dict[str, Any]) -> None:
    template = data.get("template")
    if not isinstance(template, str) or not template.strip():
        report.error("template-transform.template must be a non-empty string")
    variables = require_list(report, data.get("variables"), "template-transform.variables")
    names: set[str] = set()
    for index, variable in enumerate(variables):
        label = f"template-transform.variables[{index}]"
        item = require_dict(report, variable, label)
        name = item.get("variable")
        if not nonempty_str(name) or not SAFE_NAME_RE.match(str(name)):
            report.error(f"{label}.variable must be a safe identifier")
            continue
        if name in names:
            report.error(f"{label}.variable duplicated: {name}")
        names.add(name)
        if not is_selector(item.get("value_selector")):
            report.error(f"{label}.value_selector must be [nodeId, outputKey]")
    if isinstance(template, str):
        for match in JINJA_VAR_RE.findall(template):
            if match not in names:
                report.warn(f"template-transform.template uses undeclared variable: {match}")


def validate_http(report: Report, data: dict[str, Any]) -> None:
    method = data.get("method")
    if not isinstance(method, str) or method.lower() not in HTTP_METHODS:
        report.error("http-request.method is invalid")
    url = data.get("url")
    if not nonempty_str(url):
        report.error("http-request.url must be non-empty")
    elif not (str(url).lower().startswith(("http://", "https://")) or "{{#" in str(url)):
        report.error("http-request.url must be an http(s) URL or contain a Dify template reference")
    for key in ("headers", "params"):
        if key in data and not isinstance(data.get(key), str):
            report.error(f"http-request.{key} must be a string")
    body = require_dict(report, data.get("body"), "http-request.body")
    if body:
        body_type = body.get("type")
        if body_type not in HTTP_BODY_TYPES:
            report.error(f"http-request.body.type is invalid: {body_type!r}")
        if body_type in {"json", "form-data", "x-www-form-urlencoded"}:
            rows = require_list(report, body.get("data"), "http-request.body.data")
            for index, row in enumerate(rows):
                label = f"http-request.body.data[{index}]"
                item = require_dict(report, row, label)
                if not isinstance(item.get("key"), str):
                    report.error(f"{label}.key must be a string")
                if "value" not in item:
                    report.error(f"{label}.value is required")
    auth = require_dict(report, data.get("authorization"), "http-request.authorization")
    if auth:
        if auth.get("type") not in AUTH_TYPES:
            report.error("http-request.authorization.type must be 'no-auth' or 'api-key'")
    timeout = require_dict(report, data.get("timeout"), "http-request.timeout")
    if timeout:
        for key in ("max_connect_timeout", "max_read_timeout", "max_write_timeout"):
            if key in timeout and not isinstance(timeout.get(key), int):
                report.error(f"http-request.timeout.{key} must be an integer")
    require_list(report, data.get("variables", []), "http-request.variables")


def validate_variable_aggregator(report: Report, data: dict[str, Any]) -> None:
    if not nonempty_str(data.get("output_type")):
        report.error("variable-aggregator.output_type must be a non-empty string")
    variables = require_list(report, data.get("variables"), "variable-aggregator.variables")
    if not variables:
        report.error("variable-aggregator.variables must be non-empty")
    for index, selector in enumerate(variables):
        if not is_selector(selector):
            report.error(f"variable-aggregator.variables[{index}] must be [nodeId, outputKey]")


def validate_parameter_extractor(report: Report, data: dict[str, Any]) -> None:
    validate_model(report, data.get("model"), "parameter-extractor.model")
    if not is_selector(data.get("query")):
        report.error("parameter-extractor.query must be [nodeId, outputKey]")
    parameters = require_list(report, data.get("parameters"), "parameter-extractor.parameters")
    if not parameters:
        report.error("parameter-extractor.parameters must be non-empty")
    seen: set[str] = set()
    for index, parameter in enumerate(parameters):
        label = f"parameter-extractor.parameters[{index}]"
        item = require_dict(report, parameter, label)
        name = item.get("name")
        if not nonempty_str(name) or not SAFE_NAME_RE.match(str(name)):
            report.error(f"{label}.name must be a safe identifier")
        elif name in seen:
            report.error(f"{label}.name duplicated: {name}")
        else:
            seen.add(name)
        param_type = item.get("type")
        if param_type not in {"string", "number", "boolean", "object", "array[string]", "array[number]", "array[boolean]", "array[object]"}:
            report.error(f"{label}.type is invalid: {param_type!r}")
        if not isinstance(item.get("description"), str):
            report.error(f"{label}.description must be a string")
        if not isinstance(item.get("required"), bool):
            report.error(f"{label}.required must be a boolean")
    if data.get("reasoning_mode") not in {"prompt", "function_call"}:
        report.error("parameter-extractor.reasoning_mode must be 'prompt' or 'function_call'")


def validate_document_extractor(report: Report, data: dict[str, Any]) -> None:
    if not is_selector(data.get("variable_selector")):
        report.error("document-extractor.variable_selector must be [nodeId, outputKey]")


def validate_variable_assigner(report: Report, data: dict[str, Any]) -> None:
    items = data.get("items")
    if items is not None:
        rows = require_list(report, items, "variable-assigner.items")
        if not rows:
            report.error("variable-assigner.items must be non-empty")
        for index, row in enumerate(rows):
            label = f"variable-assigner.items[{index}]"
            item = require_dict(report, row, label)
            if not is_selector(item.get("variable_selector")):
                report.error(f"{label}.variable_selector must be [conversation, name] or [nodeId, outputKey]")
            if item.get("input_type") not in {"variable", "constant"}:
                report.error(f"{label}.input_type must be 'variable' or 'constant'")
            if item.get("operation") not in {"overwrite", "clear", "append", "extend", "set"}:
                report.error(f"{label}.operation is invalid")
        return
    variables = data.get("variables")
    if variables is None:
        report.error("variable-assigner requires items (newer DSL) or variables (legacy DSL)")
    else:
        require_list(report, variables, "variable-assigner.variables")
        report.warn("variable-assigner uses legacy 'variables'; verify against the target Dify export")


def validate_advanced_node(report: Report, data: dict[str, Any], nodetype: str) -> None:
    if nodetype == "iteration":
        if not is_selector(data.get("iterator_selector")):
            report.error("iteration.iterator_selector must be [nodeId, outputKey]")
        if not is_selector(data.get("output_selector")):
            report.error("iteration.output_selector must be [nodeId, outputKey]")
        if not nonempty_str(data.get("start_node_id")):
            report.error("iteration.start_node_id must be a non-empty string")
        if not isinstance(data.get("is_parallel"), bool):
            report.error("iteration.is_parallel must be a boolean")
        if not isinstance(data.get("parallel_nums"), int) or data.get("parallel_nums") <= 0:
            report.error("iteration.parallel_nums must be a positive integer")
        report.warn("iteration topology is version-sensitive; verify against a target-Dify export")
    elif nodetype == "loop":
        if not nonempty_str(data.get("start_node_id")):
            report.error("loop.start_node_id must be a non-empty string")
        if "loop_count" not in data and "break_conditions" not in data:
            report.error("loop requires loop_count or break_conditions")
        report.warn("loop node is version-sensitive; verify against a target-Dify export")
    elif nodetype == "agent":
        for key in ("agent_strategy_provider_name", "agent_strategy_name", "agent_strategy_label"):
            if not nonempty_str(data.get(key)):
                report.error(f"agent.{key} must be a non-empty string")
        if not isinstance(data.get("agent_parameters"), dict):
            report.error("agent.agent_parameters must be a mapping/object")
        report.warn("agent node requires the matching plugin dependency; verify dependencies[].value")
    elif nodetype == "tool":
        for key in ("provider_id", "provider_name", "tool_name", "tool_label"):
            if not nonempty_str(data.get(key)):
                report.error(f"tool.{key} must be a non-empty string")
        if not isinstance(data.get("tool_parameters"), dict):
            report.error("tool.tool_parameters must be a mapping/object")
        report.warn("tool node requires the matching plugin dependency; verify dependencies[].value")
    elif nodetype in {"datasource", "trigger"}:
        report.warn(f"{nodetype} node is version-sensitive; copy the exact shape from a target-Dify export")


def validate_node_contract(
    report: Report,
    data: dict[str, Any],
    nodetype: str,
    file_upload_enabled: bool,
    mode: str,
) -> None:
    if nodetype == "start":
        validate_start(report, data, file_upload_enabled, mode)
    elif nodetype == "end":
        validate_end(report, data)
    elif nodetype == "answer":
        validate_answer(report, data)
    elif nodetype == "llm":
        validate_llm(report, data)
    elif nodetype == "knowledge-retrieval":
        validate_knowledge(report, data)
    elif nodetype == "question-classifier":
        validate_classifier(report, data)
    elif nodetype == "if-else":
        validate_ifelse(report, data)
    elif nodetype == "code":
        validate_code(report, data)
    elif nodetype == "template-transform":
        validate_template_transform(report, data)
    elif nodetype == "http-request":
        validate_http(report, data)
    elif nodetype == "variable-aggregator":
        validate_variable_aggregator(report, data)
    elif nodetype == "parameter-extractor":
        validate_parameter_extractor(report, data)
    elif nodetype == "document-extractor":
        validate_document_extractor(report, data)
    elif nodetype == "variable-assigner":
        validate_variable_assigner(report, data)
    elif nodetype in {"iteration", "loop", "agent", "tool", "datasource", "trigger"}:
        validate_advanced_node(report, data, nodetype)


def validate_edges(
    report: Report,
    edges: list[Any],
    nodes_by_id: dict[str, dict[str, Any]],
) -> tuple[dict[str, set[str]], dict[str, set[str]]]:
    outgoing: dict[str, set[str]] = {node_id: set() for node_id in nodes_by_id}
    incoming: dict[str, set[str]] = {node_id: set() for node_id in nodes_by_id}
    branch_handles: dict[str, set[str]] = {}

    for node_id, node in nodes_by_id.items():
        data = node_data(node)
        nodetype = node_type(node)
        if nodetype == "if-else":
            handles = {str(case.get("case_id")) for case in as_list(data.get("cases")) if isinstance(case, dict) and case.get("case_id")}
            handles.add("false")
            branch_handles[node_id] = handles
        elif nodetype == "question-classifier":
            handles = {str(cls.get("id")) for cls in as_list(data.get("classes")) if isinstance(cls, dict) and cls.get("id")}
            branch_handles[node_id] = handles

    edge_ids: set[str] = set()
    edge_keys: set[tuple[str, str, str]] = set()

    for index, edge in enumerate(edges):
        label = f"edges[{index}]"
        item = require_dict(report, edge, label)
        if not item:
            continue
        edge_id = item.get("id")
        if not nonempty_str(edge_id):
            report.error(f"{label}.id must be a non-empty string")
        elif edge_id in edge_ids:
            report.error(f"{label}.id duplicated: {edge_id}")
        else:
            edge_ids.add(edge_id)

        source = item.get("source")
        target = item.get("target")
        source_handle = item.get("sourceHandle")
        target_handle = item.get("targetHandle")

        if not nonempty_str(source) or source not in nodes_by_id:
            report.error(f"{label}.source does not reference an existing node: {source!r}")
            continue
        if not nonempty_str(target) or target not in nodes_by_id:
            report.error(f"{label}.target does not reference an existing node: {target!r}")
            continue
        if source == target:
            report.error(f"{label} is a self-loop: {source}")
        if not nonempty_str(source_handle):
            report.error(f"{label}.sourceHandle must be non-empty")
        if not nonempty_str(target_handle):
            report.error(f"{label}.targetHandle must be non-empty")

        source_type = node_type(nodes_by_id[source])
        target_type = node_type(nodes_by_id[target])
        if source in branch_handles:
            if source_handle not in branch_handles[source]:
                report.error(
                    f"{label}.sourceHandle {source_handle!r} is not a valid branch handle for "
                    f"{source_type}; expected one of {sorted(branch_handles[source])}"
                )
        elif source_handle != "source":
            report.error(f"{label}.sourceHandle must be 'source' for {source_type}, got {source_handle!r}")
        if target_handle != "target":
            report.error(f"{label}.targetHandle must be 'target', got {target_handle!r}")

        edge_data = require_dict(report, item.get("data"), f"{label}.data")
        if edge_data:
            if "sourceType" in edge_data and edge_data.get("sourceType") != source_type:
                report.error(f"{label}.data.sourceType must be {source_type!r}")
            if "targetType" in edge_data and edge_data.get("targetType") != target_type:
                report.error(f"{label}.data.targetType must be {target_type!r}")
            if "isInIteration" in edge_data and not isinstance(edge_data.get("isInIteration"), bool):
                report.error(f"{label}.data.isInIteration must be a boolean")
            if "isInLoop" in edge_data and not isinstance(edge_data.get("isInLoop"), bool):
                report.error(f"{label}.data.isInLoop must be a boolean")

        key = (source, str(source_handle), target)
        if key in edge_keys:
            report.error(f"{label} duplicates an existing edge: {source} -{source_handle}-> {target}")
        edge_keys.add(key)
        outgoing[source].add(target)
        incoming[target].add(source)

    for node_id, handles in branch_handles.items():
        used = {
            str(edge.get("sourceHandle"))
            for edge in edges
            if isinstance(edge, dict) and edge.get("source") == node_id
        }
        for handle in sorted(handles):
            if handle not in used:
                report.warn(f"branch node {node_id} has no outgoing edge for handle: {handle}")
    for node_id, targets in outgoing.items():
        nodetype = node_type(nodes_by_id[node_id])
        if node_id not in branch_handles and len(targets) > 1:
            report.warn(f"node {node_id} ({nodetype}) has {len(targets)} outgoing edges; confirm this is intentional")
        if nodetype in TERMINAL_TYPES and targets:
            report.warn(f"terminal node {node_id} ({nodetype}) has outgoing edges")
        if nodetype == "start" and incoming.get(node_id):
            report.warn("start node has incoming edges")
    return outgoing, incoming


def validate_layout(
    report: Report,
    nodes_by_id: dict[str, dict[str, Any]],
    edges: list[Any],
    branch_handles: dict[str, set[str]] | None = None,
) -> None:
    positions: dict[str, tuple[float, float]] = {}
    occupied: dict[tuple[float, float], str] = {}
    for node_id, node in nodes_by_id.items():
        position = node.get("position")
        if not isinstance(position, dict):
            report.error(f"{node_id}: position must be a mapping/object")
            continue
        x = position.get("x")
        y = position.get("y")
        if not isinstance(x, (int, float)) or not isinstance(y, (int, float)):
            report.error(f"{node_id}: position.x and position.y must be numbers")
            continue
        positions[node_id] = (float(x), float(y))
        key = (float(x), float(y))
        if key in occupied:
            report.error(f"node positions overlap: {occupied[key]} and {node_id} at {key}")
        occupied[key] = node_id

    for edge in edges:
        if not isinstance(edge, dict):
            continue
        source = edge.get("source")
        target = edge.get("target")
        if source not in positions or target not in positions:
            continue
        sx, sy = positions[source]
        tx, ty = positions[target]
        if abs(tx - sx) < 200 and abs(ty - sy) < 120:
            report.error(f"edge {source}->{target} has overlapping positions; adjust x or y")
        elif abs(tx - sx) < 250 and abs(ty - sy) < 120:
            report.warn(f"edge {source}->{target} is visually tight; prefer a 350 x step")


def allowed_outputs_for(node: dict[str, Any]) -> set[str] | None:
    nodetype = node_type(node)
    data = node_data(node)
    if nodetype == "start":
        return {
            str(item.get("variable"))
            for item in as_list(data.get("variables"))
            if isinstance(item, dict) and item.get("variable")
        }
    if nodetype == "code":
        return {str(key) for key in as_dict(data.get("outputs")).keys()}
    if nodetype == "parameter-extractor":
        names = {
            str(item.get("name"))
            for item in as_list(data.get("parameters"))
            if isinstance(item, dict) and item.get("name")
        }
        names.update({"__is_success", "__reason"})
        return names
    return FIXED_OUTPUTS.get(nodetype or "")


def validate_output_key(
    report: Report,
    source_node: dict[str, Any],
    key: str,
    label: str,
) -> None:
    allowed = allowed_outputs_for(source_node)
    if allowed is None:
        return
    if key not in allowed:
        report.error(
            f"{label}: output '{key}' is not valid for node type "
            f"{node_type(source_node)!r}; allowed: {sorted(allowed)}"
        )


def validate_selector(
    report: Report,
    selector: Any,
    consumer: str,
    nodes_by_id: dict[str, dict[str, Any]],
    incoming: dict[str, set[str]],
    env_names: set[str],
    conversation_names: set[str],
    label: str,
) -> None:
    if not is_selector(selector):
        report.error(f"{label}: selector must be [nodeId, outputKey]")
        return
    ref, key = selector
    if ref in nodes_by_id:
        if ref == consumer:
            report.error(f"{label}: node cannot reference its own output")
            return
        # Some Dify/青莲 exports encode system variables as [startNodeId, "sys.query"].
        if key.startswith("sys.") and node_type(nodes_by_id[ref]) == "start":
            sys_key = key.split(".", 1)[1]
            if sys_key not in SYS_VARS:
                report.error(f"{label}: unknown system variable sys.{sys_key}")
            if not reachable(ref, consumer, incoming):
                report.error(f"{label}: referenced start node {ref} is not upstream of {consumer}")
            return
        validate_output_key(report, nodes_by_id[ref], key, label)
        if not reachable(ref, consumer, incoming):
            report.error(f"{label}: referenced node {ref} is not upstream of {consumer}")
    elif ref == "sys":
        if key not in SYS_VARS:
            report.error(f"{label}: unknown system variable sys.{key}")
    elif ref == "env":
        if key not in env_names:
            report.error(f"{label}: environment variable {key} is not declared in workflow.environment_variables")
    elif ref == "conversation":
        if key not in conversation_names:
            report.error(f"{label}: conversation variable {key} is not declared in workflow.conversation_variables")
    else:
        report.error(f"{label}: selector references unknown node: {ref}")


def iter_template_refs_with_path(value: Any, path: str = "") -> Iterable[tuple[str, str, str]]:
    if isinstance(value, str):
        for match in TEMPLATE_REF_RE.findall(value):
            if "." in match:
                ref, key = match.split(".", 1)
                yield ref, key, path
    elif isinstance(value, list):
        for index, item in enumerate(value):
            yield from iter_template_refs_with_path(item, f"{path}[{index}]")
    elif isinstance(value, dict):
        for key, item in value.items():
            if key == "code":
                continue
            yield from iter_template_refs_with_path(item, f"{path}.{key}")


def validate_node_references(
    report: Report,
    nodes_by_id: dict[str, dict[str, Any]],
    incoming: dict[str, set[str]],
    env_names: set[str],
    conversation_names: set[str],
) -> None:
    node_ids = set(nodes_by_id)
    for node_id, node in nodes_by_id.items():
        data = node_data(node)
        for selector, path in iter_selector_fields(data, node_ids):
            validate_selector(
                report,
                selector,
                node_id,
                nodes_by_id,
                incoming,
                env_names,
                conversation_names,
                f"{node_id}{path}",
            )
        for ref, key, path in iter_template_refs_with_path(data):
            label = f"{node_id}{path}"
            if ref in nodes_by_id:
                if ref == node_id:
                    report.error(f"{label}: node cannot reference its own output")
                    continue
                validate_output_key(report, nodes_by_id[ref], key, label)
                if not reachable(ref, node_id, incoming):
                    report.error(f"{label}: referenced node {ref} is not upstream of {node_id}")
            elif ref == "sys":
                if key not in SYS_VARS:
                    report.error(f"{label}: unknown system variable sys.{key}")
            elif ref == "env":
                if key not in env_names:
                    report.error(f"{label}: environment variable {key} is not declared")
            elif ref == "conversation":
                if key not in conversation_names:
                    report.error(f"{label}: conversation variable {key} is not declared")
            else:
                report.error(f"{label}: template reference points to unknown node: {ref}")


def validate_connectivity(
    report: Report,
    nodes_by_id: dict[str, dict[str, Any]],
    outgoing: dict[str, set[str]],
    incoming: dict[str, set[str]],
    mode: str,
) -> None:
    starts = [node_id for node_id, node in nodes_by_id.items() if node_type(node) == "start"]
    ends = [node_id for node_id, node in nodes_by_id.items() if node_type(node) == "end"]
    answers = [node_id for node_id, node in nodes_by_id.items() if node_type(node) == "answer"]

    if len(starts) != 1:
        report.error(f"{mode} graph must contain exactly one start node, found {len(starts)}")
        return
    if mode == "workflow":
        if len(ends) != 1:
            report.error(f"workflow graph must contain exactly one end node, found {len(ends)}")
        if answers:
            report.warn("workflow mode normally outputs through end, not answer")
    else:
        if not answers:
            report.error(f"{mode} graph must contain at least one answer node")
        if ends:
            report.warn(f"{mode} mode normally uses answer nodes, not end")
    terminals = ends if mode == "workflow" else answers
    if not terminals:
        report.error("graph has no terminal end/answer node")

    reachable_from_start: set[str] = set()
    stack = list(starts)
    while stack:
        current = stack.pop()
        if current in reachable_from_start:
            continue
        reachable_from_start.add(current)
        stack.extend(outgoing.get(current, set()) - reachable_from_start)

    can_reach_terminal: set[str] = set()
    stack = list(terminals)
    while stack:
        current = stack.pop()
        if current in can_reach_terminal:
            continue
        can_reach_terminal.add(current)
        stack.extend(incoming.get(current, set()) - can_reach_terminal)

    for node_id, node in nodes_by_id.items():
        if node.get("parentId") or node_type(node) in INTERNAL_TYPES:
            continue
        if node_type(node) != "start" and node_id not in reachable_from_start:
            report.error(f"{node_id}: node is not reachable from start")
        if node_type(node) not in TERMINAL_TYPES and node_id not in can_reach_terminal:
            report.error(f"{node_id}: node cannot reach an end/answer terminal")


def validate_environment_variables(
    report: Report,
    workflow: dict[str, Any],
) -> tuple[set[str], set[str]]:
    env_names: set[str] = set()
    conversation_names: set[str] = set()
    envs = require_list(report, workflow.get("environment_variables", []), "workflow.environment_variables")
    for index, env in enumerate(envs):
        label = f"workflow.environment_variables[{index}]"
        item = require_dict(report, env, label)
        name = item.get("name")
        if not nonempty_str(name) or not SAFE_NAME_RE.match(str(name)):
            report.error(f"{label}.name must be a safe identifier")
            continue
        if name in env_names:
            report.error(f"{label}.name duplicated: {name}")
        env_names.add(name)
        if item.get("value_type") not in {"string", "number", "secret"}:
            report.error(f"{label}.value_type must be string/number/secret")
        if "value" not in item:
            report.error(f"{label}.value is required")
        if "id" in item and not nonempty_str(item.get("id")):
            report.error(f"{label}.id must be a non-empty string")
        selector = item.get("selector")
        if selector is None:
            report.warn(f"{label}.selector is missing; target-Dify exports usually include [env, name]")
        elif not is_selector(selector) or selector[0] != "env" or selector[1] != name:
            report.error(f"{label}.selector must be [env, {name}]")
    conversations = require_list(report, workflow.get("conversation_variables", []), "workflow.conversation_variables")
    for index, conv in enumerate(conversations):
        label = f"workflow.conversation_variables[{index}]"
        item = require_dict(report, conv, label)
        name = item.get("name")
        if not nonempty_str(name) or not SAFE_NAME_RE.match(str(name)):
            report.error(f"{label}.name must be a safe identifier")
            continue
        if name in conversation_names:
            report.error(f"{label}.name duplicated: {name}")
        conversation_names.add(name)
        if item.get("value_type") not in {"string", "number", "object", "array[string]", "array[number]", "array[object]"}:
            report.error(f"{label}.value_type is invalid")
        if "value" not in item:
            report.error(f"{label}.value is required")
        if "id" in item and not nonempty_str(item.get("id")):
            report.error(f"{label}.id must be a non-empty string")
        selector = item.get("selector")
        if selector is None:
            report.warn(f"{label}.selector is missing; target-Dify exports usually include [conversation, name]")
        elif not is_selector(selector) or selector[0] != "conversation" or selector[1] != name:
            report.error(f"{label}.selector must be [conversation, {name}]")
    return env_names, conversation_names


def validate_features(report: Report, workflow: dict[str, Any]) -> bool:
    features = require_dict(report, workflow.get("features"), "workflow.features")
    if not features:
        report.warn("workflow.features is missing; copy the block from the base template")
        return False
    upload = require_dict(report, features.get("file_upload"), "workflow.features.file_upload")
    enabled = bool(upload.get("enabled")) if upload else False
    if upload:
        if not isinstance(upload.get("enabled"), bool):
            report.error("workflow.features.file_upload.enabled must be a boolean")
        if enabled:
            types = require_list(report, upload.get("allowed_file_types"), "workflow.features.file_upload.allowed_file_types")
            if not types:
                report.error("file upload is enabled but allowed_file_types is empty")
            methods = require_list(report, upload.get("allowed_file_upload_methods"), "workflow.features.file_upload.allowed_file_upload_methods")
            if not methods:
                report.error("file upload is enabled but allowed_file_upload_methods is empty")
            if not isinstance(upload.get("number_limits"), int) or upload.get("number_limits") <= 0:
                report.error("file upload is enabled but number_limits is invalid")
    for key in ("suggested_questions",):
        if key in features:
            require_list(report, features.get(key), f"workflow.features.{key}")
    for key in ("retriever_resource", "sensitive_word_avoidance", "speech_to_text", "suggested_questions_after_answer", "text_to_speech"):
        if key in features:
            item = require_dict(report, features.get(key), f"workflow.features.{key}")
            if item and "enabled" in item and not isinstance(item.get("enabled"), bool):
                report.error(f"workflow.features.{key}.enabled must be a boolean")
    opening = features.get("opening_statement")
    if opening is not None and not isinstance(opening, str):
        report.error("workflow.features.opening_statement must be a string or null")
    return enabled


KNOWN_VERSIONS = {
    "0.1.0", "0.1.1", "0.1.2", "0.1.3", "0.1.4", "0.1.5",
    "0.2.0", "0.2.1", "0.3.0", "0.3.1", "0.4.0", "0.4.1", "0.5.0",
}


def validate_document(
    data: Any,
    report: Report,
    allow_unknown_types: bool,
    skip_layout: bool,
) -> None:
    root = require_dict(report, data, "root")
    if not root:
        return
    if root.get("kind") != "app":
        report.error("root.kind must be 'app'")
    version = root.get("version")
    if not isinstance(version, str) or not VERSION_RE.match(version):
        report.error("root.version must be a semver string such as '0.3.0'")
    elif version not in KNOWN_VERSIONS:
        report.warn(f"root.version {version} is not in the known version list; verify against the target Dify")
    if not isinstance(root.get("dependencies"), list):
        report.error("root.dependencies must be a list")

    app = require_dict(report, root.get("app"), "root.app")
    mode = app.get("mode") if app else None
    if mode not in ALL_MODES:
        report.error(f"app.mode must be one of {sorted(ALL_MODES)}")
    if not nonempty_str(app.get("name")):
        report.error("app.name must be a non-empty string")
    if app.get("description") is not None and not isinstance(app.get("description"), str):
        report.error("app.description must be a string or null")
    if "use_icon_as_answer_icon" in app and not isinstance(app.get("use_icon_as_answer_icon"), bool):
        report.error("app.use_icon_as_answer_icon must be a boolean")

    if mode in SIMPLE_MODES:
        report.warn(f"mode {mode} does not use a workflow graph; this skill focuses on workflow/advanced-chat")
        return

    workflow = require_dict(report, root.get("workflow"), "root.workflow")
    if not workflow:
        return
    file_upload_enabled = validate_features(report, workflow)
    env_names, conversation_names = validate_environment_variables(report, workflow)
    graph = require_dict(report, workflow.get("graph"), "workflow.graph")
    if not graph:
        return
    raw_nodes = require_list(report, graph.get("nodes"), "workflow.graph.nodes")
    edges = require_list(report, graph.get("edges"), "workflow.graph.edges")
    if not raw_nodes:
        report.error("workflow.graph.nodes must be non-empty")
        return
    viewport = require_dict(report, graph.get("viewport"), "workflow.graph.viewport")
    if viewport:
        for key in ("x", "y", "zoom"):
            if key in viewport and not isinstance(viewport.get(key), (int, float)):
                report.error(f"workflow.graph.viewport.{key} must be a number")

    nodes_by_id: dict[str, dict[str, Any]] = {}
    for index, raw_node in enumerate(raw_nodes):
        label = f"workflow.graph.nodes[{index}]"
        node = require_dict(report, raw_node, label)
        if not node:
            continue
        node_id = node.get("id")
        if not nonempty_str(node_id):
            report.error(f"{label}.id must be a non-empty string")
            continue
        if "." in str(node_id):
            report.error(f"{label}.id must not contain dots: {node_id}")
        if node_id in nodes_by_id:
            report.error(f"{label}.id duplicated: {node_id}")
            continue
        nodes_by_id[str(node_id)] = node
        if node.get("type") != "custom":
            report.warn(f"{node_id}: node.type should be 'custom' in Dify export")
        data_obj = node_data(node)
        if not data_obj:
            report.error(f"{node_id}: data must be a mapping/object with a type")
            continue
        nodetype = node_type(node)
        if not nodetype:
            report.error(f"{node_id}: data.type is required")
            continue
        if nodetype not in NODE_TYPES:
            if allow_unknown_types:
                report.warn(f"{node_id}: unknown node type {nodetype!r} allowed by flag")
            else:
                report.error(f"{node_id}: unknown node type {nodetype!r}")
                continue
        if not nonempty_str(data_obj.get("title")):
            report.warn(f"{node_id}: data.title is empty")
        if "selected" in data_obj and not isinstance(data_obj.get("selected"), bool):
            report.error(f"{node_id}: data.selected must be a boolean")
        for key in ("width", "height"):
            if key in node and not isinstance(node.get(key), (int, float)):
                report.error(f"{node_id}: {key} must be a number")
        if "parentId" in node and not isinstance(node.get("parentId"), str):
            report.error(f"{node_id}: parentId must be a string")
        validate_node_contract(report, data_obj, nodetype, file_upload_enabled, mode)

    if any(node_type(node) in {"agent", "tool"} for node in nodes_by_id.values()):
        if not root.get("dependencies"):
            report.warn("agent/tool nodes usually require a plugin entry in root.dependencies")

    outgoing, incoming = validate_edges(report, edges, nodes_by_id)
    validate_node_references(report, nodes_by_id, incoming, env_names, conversation_names)
    validate_connectivity(report, nodes_by_id, outgoing, incoming, mode)
    if not skip_layout:
        validate_layout(report, nodes_by_id, edges)


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate a Dify app DSL YAML file.")
    parser.add_argument("path", help="path to the Dify DSL .yml/.yaml file")
    parser.add_argument("--strict", action="store_true", help="treat warnings as errors")
    parser.add_argument("--allow-unknown-types", action="store_true", help="allow node types not in the core whitelist")
    parser.add_argument("--skip-layout", action="store_true", help="skip canvas position checks")
    args = parser.parse_args()

    path = Path(args.path)
    if not path.exists():
        print(f"ERROR: file not found: {path}")
        return 1
    try:
        raw_text = path.read_bytes().decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        print(f"ERROR: file is not valid UTF-8: {exc}")
        return 1
    except OSError as exc:
        print(f"ERROR: cannot read file: {exc}")
        return 1

    report = Report()
    if any(marker in raw_text for marker in MOJIBAKE_MARKERS):
        report.error("mojibake marker found in generated text")
    if "{{$" in raw_text:
        report.error("FastGPT template syntax {{$...$}} found; Dify uses {{#node.output#}}")

    try:
        documents = [item for item in yaml.safe_load_all(raw_text) if item is not None]
    except yaml.YAMLError as exc:
        print(f"ERROR: invalid YAML: {exc}")
        return 1
    if len(documents) != 1:
        report.error(f"file must contain exactly one YAML document, found {len(documents)}")
        data = None
    else:
        data = documents[0]
        validate_document(data, report, args.allow_unknown_types, args.skip_layout)

    if args.strict:
        report.errors.extend(report.warnings)
        report.warnings = []

    for warning in sorted(set(report.warnings)):
        print(f"WARNING: {warning}")
    if report.has_blocking_errors():
        for error in sorted(set(report.errors)):
            print(f"ERROR: {error}")
        return 1
    print("VALIDATION_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
