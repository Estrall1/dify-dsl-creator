# Dify DSL Validation Checklist

A file is structurally ready only when `scripts/validate_dify_dsl.py` prints `VALIDATION_OK`.

## Gate 1. File And Encoding

- UTF-8, no BOM requirement (BOM is tolerated on read).
- Exactly one YAML document.
- `.yml` or `.yaml` extension.
- No mojibake markers.
- No FastGPT `{{$...$}}` syntax.
- YAML parses successfully.

## Gate 2. Root

- `kind: app`.
- `version` is semver.
- `app` is an object with `name`, `mode`.
- `dependencies` is a list.
- `workflow` exists for `workflow` / `advanced-chat`.

## Gate 3. App Metadata

- `app.mode` is `workflow`, `advanced-chat`, or `agent-chat`.
- `app.name` is non-empty.
- `app.use_icon_as_answer_icon` is boolean when present.
- `app.description` is a string when present.

## Gate 4. Workflow Features

- `workflow.features` exists.
- `file_upload.enabled` is boolean.
- If file upload is enabled:
  - `allowed_file_types` non-empty.
  - `allowed_file_upload_methods` non-empty.
  - `number_limits` positive integer.
- `opening_statement` is string or null.
- `suggested_questions` is a list.
- `retriever_resource`, `speech_to_text`, `text_to_speech`, `sensitive_word_avoidance`, `suggested_questions_after_answer` use boolean `enabled` when present.

## Gate 5. Graph Shape

- `workflow.graph.nodes` non-empty.
- `workflow.graph.edges` is a list.
- `workflow.graph.viewport` is an object with numeric `x`, `y`, `zoom`.
- Node IDs are unique, non-empty strings without dots.
- Each node has `data.type`, `data.title`, `position`.
- `position` and `positionAbsolute` use numeric `x`, `y`.

## Gate 6. Mode Topology

- Exactly one `start`.
- `workflow` mode: exactly one `end`.
- `advanced-chat` mode: at least one `answer`.
- Every non-start node is reachable from `start`.
- Every node can reach an `end` or `answer`.
- No isolated business nodes.
- No node with no outgoing edge unless it is a terminal.

## Gate 7. Node Contracts

### `start`

- `variables` is a list.
- Each `variable` is a safe identifier and unique.
- `type` is one of `text-input`, `paragraph`, `select`, `number`, `file`, `file-list`, `checkbox`, `json`.
- `select` has non-empty `options`.
- File variables require file upload enabled.

### `end`

- `outputs` non-empty.
- Each output has a safe `variable` and a valid `value_selector`.

### `answer`

- `answer` non-empty string.

### `llm`

- `model.provider`, `model.name`, `model.mode`, `model.completion_params`.
- `prompt_template` non-empty; roles and text types valid.
- `context.enabled` boolean; selector required when enabled.
- `vision.enabled` boolean.

### `knowledge-retrieval`

- `dataset_ids` list.
- `retrieval_mode` is `single` or `multiple`.
- Matching retrieval config exists.
- `query_variable_selector` valid.
- Placeholder dataset IDs are warnings to replace.

### `question-classifier`

- `classes` non-empty.
- Class IDs unique and non-empty.
- `name` non-empty.
- `model` and `query_variable_selector` valid.

### `if-else`

- `cases` non-empty.
- `case_id` unique; `false` is reserved.
- `logical_operator` is `and` or `or`.
- Each case has non-empty `conditions`.
- Each condition has `id`, `comparison_operator`, `variable_selector`.
- `value` present unless the operator is empty/exists.

### `code`

- `code_language` is `python3` or `javascript`.
- `code` non-empty and defines `main`.
- `outputs` non-empty mapping with types.
- `variables` selectors valid.

### `template-transform`

- `template` non-empty.
- `variables` valid.
- Template local variables are declared.

### `http-request`

- `method` valid.
- `url` non-empty.
- `headers`, `params` strings.
- `body.type` valid; body rows have `key` and `value`.
- `authorization.type` valid.
- `timeout` values integers.

### `variable-aggregator`

- `variables` non-empty selectors.
- `output_type` non-empty.

### `parameter-extractor`

- `model`, `query`, `parameters`, `reasoning_mode`.
- Parameter names unique and safe.
- Parameter types valid.

### `document-extractor`

- `variable_selector` valid.

## Gate 8. Edges

- Every edge has `id`, `source`, `sourceHandle`, `target`, `targetHandle`, `data`.
- `source` / `target` exist.
- No self-loops.
- Normal `sourceHandle: source`, `targetHandle: target`.
- `question-classifier` branch handles are class IDs.
- `if-else` branch handles are `case_id` or `false`.
- `data.sourceType` / `data.targetType` match node types.
- No duplicate edges.
- Every class and case has an outgoing edge (warnings when missing).

## Gate 9. References

- Selector arrays are exactly two strings.
- Selector node IDs exist.
- Output keys are valid for the source node type.
- Template references use `{{#nodeId.outputKey#}}`.
- System variables are known.
- Environment variables are declared.
- Conversation variables are declared.
- Referenced nodes are upstream in the graph.
- No FastGPT syntax, legacy moustache syntax, or subpaths.
- Newly generated files should use node IDs rather than display titles.
- Existing 青莲 exports may contain title-based prompt references; preserve them and verify at runtime.

## Gate 9b. Qinglian 0.3.1 Specifics

- `version: 0.3.1` when starting from `assets/base-qinglian-chatflow.yml`.
- Marketplace dependencies use `type: marketplace` and `marketplace_plugin_unique_identifier`.
- `llm.memory` is optional; if present, `query_prompt_template`, `role_prefix`, and `window` should be well-formed.
- System-variable selectors may be `[startNodeId, 'sys.query']`.
- `http-request` may include `retry_config` and `ssl_verify`.
- Edge `data.isInLoop` must be boolean when present.
- `if-else` may export only explicit cases; else is the `false` handle.
- A “blank flow” export with `app.mode: advanced-chat` is a Chatflow, not a workflow.
- `assets/base-qinglian-chatflow.yml` is rebuilt from a real blank Chatflow export.
- `assets/base-qinglian-workflow.yml` is built from the real blank `mode: workflow` export and adds `llm` + `end`.
- `assets/qinglian-blank-workflow.yml` is the raw blank workflow export: only `start`, no `end`. It is expected to fail final completeness validation.

## Gate 10. Layout

- No two nodes share the same position.
- Connected nodes are not stacked: at least 200 x or 120 y separation.
- Prefer 350 x step and 180 y branch spacing.
- Branch siblings do not overlap.

## Gate 11. Final Status

- Run the validator.
- Any `ERROR:` is blocking.
- Fix and rerun until `VALIDATION_OK`.
- Replace placeholders before production use.
- Perform one test import in the target Dify instance.
