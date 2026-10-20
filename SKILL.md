---
name: dify-dsl-creator
description: Generate, repair, and validate import-ready Dify app DSL YAML for workflow and advanced-chat (Chatflow) apps. Use for Dify workflow/agent DSL creation, node/variable/edge validation, version compatibility, readable canvas layout, and deterministic structural checks.
---

# Dify DSL Creator

Treat this skill as a specification plus a deterministic structural validator. Generate by copying known-good YAML shapes, then prove the file passes `scripts/validate_dify_dsl.py`.

## Scope

Supported:

- `app.mode: workflow` — 工作流应用，使用 `start` + `end`，通过结束节点定义输出。
- `app.mode: advanced-chat` — Chatflow / 对话流应用，使用 `start` + `answer`，通过直接回复节点输出。
- 常用节点：`start`、`end`、`answer`、`llm`、`knowledge-retrieval`、`question-classifier`、`if-else`、`code`、`template-transform`、`http-request`、`variable-aggregator`、`parameter-extractor`、`document-extractor`、`variable-assigner`。
- 读取、修复、补全用户已有的 Dify DSL YAML。

## Target Platform

- 默认面向标准 Dify 的 YAML DSL。
- 如果目标是**青莲 Dify**：不要假设它与上游 Dify 的版本、插件标识、模型 provider、导入格式完全一致。
- 青莲 Dify 的最稳妥流程：先从青莲导出一个空白 `workflow` 和一个空白 `advanced-chat` 应用，用它的 `version`、`app`、`workflow.features` 和空图结构作为底座。
- 详细检查表见 `references/qinglian-dify-profile.md`。
- 如果青莲只支持 JSON 导入/导出，需要先确认格式，再决定是否增加 JSON 适配层。

## Agent Apps

Dify 的“智能体”通常有两类：

- `advanced-chat` + LLM / 知识库 / 工具节点：最常用，可按 Chatflow 方式生成。
- `agent-chat` + `agent` 节点：依赖具体的 Agent 策略插件、模型和工具 schema。

生成 Agent 应用时：

1. 先确认目标 Dify 版本和 Agent 策略（如 ReAct、Function Calling）。
2. 要求用户提供目标 Dify 导出的 Agent 节点或空白 Agent 应用 DSL。
3. 复制 `agent` 节点、`dependencies[]` 和插件标识。
4. 不要凭空编造 `agent_strategy_provider_name`、`provider_id`、`tool_name` 或工具参数 schema。
5. 如果用户只是要“会调用工具/知识库的助手”，优先用 `advanced-chat` + `llm` + 知识检索/工具节点，结构更稳定。

Not safe to hand-write without a real contract:

- `iteration`、`loop`、`agent`、`tool`、`datasource`、`trigger`、插件节点。
- 这些节点必须先让用户提供目标 Dify 导出的同类节点 YAML，或提供插件标识、版本、工具 schema，再按其结构复制。

## Required Resources

Load these first:

1. `references/dsl-structure.md`
2. `references/node-contracts.md`
3. `references/variable-reference-rules.md`
4. `references/validation-checklist.md`
5. `scripts/validate_dify_dsl.py`

Load when needed:

- `references/node-templates.md` — 可直接复制的常用节点 YAML 片段。
- `references/workflow-patterns.md` — RAG、分类路由、HTTP、参数提取等组合模式。
- `references/qinglian-dify-profile.md` — 青莲 Dify 发行版的适配检查表。
- `references/version-compatibility.md` — DSL 版本与目标 Dify 版本不匹配时如何处理。
- `references/troubleshooting.md` — 导入报错、变量找不到、连线异常。
- `assets/base-workflow.yml` — 最小可导入工作流骨架（标准 Dify，0.3.0）。
- `assets/base-chatflow.yml` — 最小可导入 Chatflow 骨架（标准 Dify，0.3.0）。
- `assets/base-qinglian-chatflow.yml` — 青莲 Dify 0.3.1 已验证结构的 Chatflow 骨架。
- `assets/base-qinglian-workflow.yml` — 青莲 0.3.1 可用最小 workflow 骨架（已按空白 workflow 导出校准）。
- `assets/qinglian-blank-workflow.yml` — 青莲原始空白 workflow 导出，仅含 `start`，用于查看根结构。

## Execution Protocol

Follow this order exactly.

1. Confirm the target:
   - Dify 版本或 DSL 版本。
   - `app.mode`：`workflow` 还是 `advanced-chat`。
   - 应用名称、用途、输入项、处理步骤、输出格式。
   - 模型 provider / name、知识库 ID、API 地址、插件依赖。
2. If the user can provide a blank app export from their Dify, use it as the base file. This is the strongest version-compatibility guarantee.
3. Otherwise:
   - 青莲 Dify 的 `advanced-chat`：复制 `assets/base-qinglian-chatflow.yml`。
   - 青莲 Dify 的 `workflow`：复制 `assets/base-qinglian-workflow.yml`；它的根结构和 `features` 已按青莲空白 workflow 导出校准。需要查看原始空白结构时参考 `assets/qinglian-blank-workflow.yml`。
   - 标准 Dify：复制 `assets/base-workflow.yml` 或 `assets/base-chatflow.yml`。
4. Create a node inventory before writing YAML:
   - `nodeId`
   - `data.type`
   - purpose
   - required fields
   - output keys
   - upstream dependencies
   - visual predecessor / successor
   - canvas position
5. Copy node shapes from `references/node-templates.md` or `references/node-contracts.md`; fill scenario values.
6. Fill all selector/value fields after node IDs are fixed.
7. Generate `graph.edges` last.
8. Apply readable layout:
   - standard Dify main chain x: `80, 430, 780, 1130, 1480...` (350 step)
   - 青莲 Dify default main chain x: `80, 380, 680, 980, 1280...` (300 step)
   - branch siblings y: `282, 462, 642...` (180 step)
   - do not place connected nodes at the same position.
9. Save as UTF-8 `.yml` or `.yaml`.
10. Run `python scripts/validate_dify_dsl.py <file>`.
11. Fix every `ERROR:` and rerun until the script prints `VALIDATION_OK`.
12. Treat warnings as design review items; fix layout/reference warnings before calling the file ready.

## Root Shape

The generated YAML must contain:

```yaml
app:
  description: ''
  icon: 🤖
  icon_background: '#FFEAD5'
  mode: workflow        # or advanced-chat
  name: 应用名称
  use_icon_as_answer_icon: false
dependencies: []
kind: app
version: 0.3.0
workflow:
  conversation_variables: []
  environment_variables: []
  features: {}
  graph:
    edges: []
    nodes: []
    viewport:
      x: 0
      y: 0
      zoom: 0.7
```

`kind` must be `app`. `version` must be a quoted or plain semver such as `0.3.0`.

## Node Inventory Rules

- Exactly one `start` node in a graph app.
- `workflow` mode: exactly one `end` node. Do not use `answer` as the workflow output.
- `advanced-chat` mode: at least one `answer` node. `end` is not needed.
- Every non-start node must be reachable from `start`.
- Every node must be able to reach an `end` or `answer` terminal node.
- Do not create isolated demo nodes.
- Do not add nodes that are not referenced by the intended path.

## Node IDs

- Use unique string IDs.
- Recommended: 13-digit timestamp-like IDs such as `'1730000000001'`.
- Readable IDs such as `start`, `llm_1`, `answer_1` are acceptable only if the target Dify export style accepts them; do not mix styles.
- Keep IDs stable after writing variable references.
- Do not use dots in node IDs.

## Variable References

Two different syntaxes exist. Do not mix them up.

1. Structured selector fields use arrays:

```yaml
value_selector:
- '1730000000002'
- text
```

or:

```yaml
query_variable_selector:
- sys
- query
```

2. Prompt / answer / URL / header / body text uses Dify template syntax:

```text
{{#1730000000002.text#}}
{{#sys.query#}}
{{#env.API_BASE_URL#}}
{{#conversation.history#}}
```

Rules:

- Normal node output: `{{#nodeId.outputKey#}}`.
- System input: `{{#sys.query#}}`, `{{#sys.files#}}`.
- Environment variable: `{{#env.NAME#}}`.
- Conversation variable: `{{#conversation.NAME#}}`.
- Never use FastGPT syntax: `{{$nodeId.outputKey$}}`, `["nodeId", "outputKey"]` inside prompt text, or `{{nodeId.outputKey}}`.
- A referenced node must be upstream of the consuming node in the visual edge graph.
- `template-transform.template` uses Jinja variables declared in its own `variables` list, for example `{{ query }}`; it is not the same as `{{#node.output#}}`.
- Do not reference undeclared start variables, environment variables, or conversation variables.

## Edge Rules

- Every edge object:

```yaml
- data:
    isInIteration: false
    sourceType: llm
    targetType: answer
  id: edge-llm-answer
  source: '1730000000002'
  sourceHandle: source
  target: '1730000000003'
  targetHandle: target
  type: custom
  zIndex: 0
```

- Normal `sourceHandle` is `source`.
- Normal `targetHandle` is `target`.
- `question-classifier` branch handle is the class `id`, for example `'1'`, `'2'`.
- `if-else` branch handle is the `case_id`; the else branch is `false`. Do not use the literal labels `IF` or `ELSE`.
- `source` and `target` are node IDs, never handle IDs.
- Do not use data keys such as `text`, `result`, `query`, `output`, `body` as edge handles.
- Do not add one edge per variable reference. Edges express execution order; data bindings live inside node fields.
- Every edge must connect two existing nodes and participate in the path.

## Node-Specific Hard Rules

- `start.variables` defines workflow inputs. In `advanced-chat`, `variables: []` is valid and `sys.query` is available.
- Required file inputs use `start.variables[].type: file` or `file-list`, and `workflow.features.file_upload.enabled: true`.
- `end.outputs` must be non-empty; each output has `variable` and `value_selector`.
- `answer.answer` must be a non-empty string.
- `llm` must include `model`, `prompt_template`, `variables`, `context`, and `vision`. `model` needs `provider`, `name`, `mode`, `completion_params`.
- `knowledge-retrieval` must include `dataset_ids`, `retrieval_mode`, `query_variable_selector`, and the matching retrieval config.
- `question-classifier` must include `model`, `query_variable_selector`, and non-empty `classes` with unique `id` and Chinese `name`.
- `if-else.cases` must be non-empty; each case has `case_id`, `logical_operator`, and non-empty `conditions`.
- `code` must include `code_language`, `code`, `variables`, and non-empty `outputs`.
- `template-transform` must include `template` and `variables`.
- `http-request` must include `method`, non-empty `url`, `headers`, `params`, `body`, `authorization`, `timeout`, and `variables`.
- `variable-aggregator.variables` must be a non-empty list of selectors.
- `parameter-extractor` must include `model`, `query`, non-empty `parameters`, and `reasoning_mode`.
- `document-extractor` must include `variable_selector`.

## Version Compatibility

- Default generated version for standard Dify: `0.3.0`.
- Verified 青莲 Dify `advanced-chat` export: `0.3.1`. Use `assets/base-qinglian-chatflow.yml`.
- Qinglian blank `workflow` export is verified: `mode: workflow`, `version: 0.3.1`, only a `start` node, no `end`. `assets/base-qinglian-workflow.yml` adds `start(query) → llm → end` on top of that exact root/features shape.
- A blank workflow export will fail final completeness validation because it has no `end`; that is expected. Use it as a skeleton, not as a finished app.
- Qinglian-specific conventions:
  - system-variable selectors may be `[startNodeId, 'sys.query']`
  - `llm.memory` is optional per node
  - `http-request` may include `retry_config` and `ssl_verify`
  - edges may include `isInIteration` / `isInLoop`
  - `dependencies` uses marketplace `marketplace_plugin_unique_identifier`
- If import reports an unsupported DSL version, first export a blank app from the target Dify and copy its `version` and root shape.
- For older Dify, `0.1.5` supports the common nodes in this skill.
- Do not copy a newer node schema into an older DSL version; downgrade node fields or use the target export.
- See `references/version-compatibility.md` and `references/qinglian-dify-profile.md`.

## Validation

- Save the YAML to disk before validation unless the user asks for chat-only output.
- Run the bundled validator from the skill directory or by absolute path.
- Any `ERROR:` is blocking.
- `VALIDATION_OK` means structural validation passed. It does not prove the target Dify instance accepts every plugin or model configuration; recommend one test import.
- If the validator cannot run, report `未验证：未能运行校验脚本`.
- Do not call the file import-ready if validation did not pass.

## Final Response

Return a concise Chinese report:

1. `需求确认`
2. `生成结果` / `修复结果`
3. `验证报告`（包含 `VALIDATION_OK` 或 `未通过`）
4. `文件路径`
5. `导入建议`（目标 Dify 版本、需替换的占位符、建议先测试导入）

Do not paste the whole YAML unless the user asks.
