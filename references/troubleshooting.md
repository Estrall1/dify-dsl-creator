# Dify DSL Troubleshooting

## 1. YAML Parse Errors

Symptoms:

- Import fails before showing the app.
- `mapping values are not allowed here`
- `found character '\t' that cannot start any token`

Fixes:

- Use spaces, not tabs.
- Quote strings containing `:`, `#`, `{`, `}`, or leading zeros.
- Quote timestamp-like node IDs: `'1730000000001'`.
- Keep exactly one YAML document.

## 2. Version Rejected

Symptom: `DSL version is not supported`.

Fix:

1. Export a blank app from the target Dify.
2. Copy its `version` and root structure.
3. If the target is older, downgrade node fields or use `version: 0.1.5` with basic nodes only.

## 3. Missing Start Or End

Symptoms:

- Workflow cannot run.
- Import validation complains about graph shape.

Fix:

- `workflow` mode: exactly one `start` and one `end`.
- `advanced-chat`: exactly one `start` and at least one `answer`.
- Do not use `answer` as the only terminal in `workflow` mode.

## 4. Variable Not Found

Symptoms:

- Node input panel shows an empty or unresolved variable.
- Runtime error: variable does not exist.

Checklist:

- Selector is `[nodeId, outputKey]` with exactly two strings.
- Node ID is the real graph node ID, not the title.
- Output key is valid for the source node type.
- Source node is upstream of the consumer.
- Template text uses `{{#nodeId.outputKey#}}`.
- Environment/conversation variables are declared.

Common mistakes:

```text
{{$nodeId.outputKey$}}          -> FastGPT syntax
{{nodeId.outputKey}}            -> legacy syntax
["nodeId", "outputKey"]         -> invalid inside prompt text
{{#llm.result#}}                -> LLM output is text, not result
{{#knowledge.text#}}            -> knowledge output is result
{{#extractor.name#}}            -> valid; extractor.field is not
```

## 5. Edge Handle Errors

Symptoms:

- Branch never runs.
- Canvas shows disconnected handles.

Fixes:

- Normal edge: `sourceHandle: source`, `targetHandle: target`.
- Classifier: `sourceHandle` equals `classes[].id`.
- If-else: `sourceHandle` equals `case_id`, else `false`.
- Do not use `IF`, `ELSE`, `text`, `result`, or output keys as handles.

## 6. Empty Or Wrong Outputs

- `llm` output: `text`.
- `knowledge-retrieval` output: `result`.
- `http-request` output: `body`, `status_code`, `headers`.
- `template-transform` output: `output`.
- `variable-aggregator` output: `output`.
- `document-extractor` output: `text`.
- `code` output: keys declared in `outputs`.
- `parameter-extractor` output: parameter names plus `__is_success`, `__reason`.

## 7. File Input Not Working

Checklist:

- `start.variables[].type: file` or `file-list`.
- `workflow.features.file_upload.enabled: true`.
- `allowed_file_types` and `allowed_file_upload_methods` non-empty.
- `document-extractor.variable_selector` points to the file variable.
- Downstream text nodes use `document-extractor.text`.

## 8. Plugin Or Agent Node Missing

Symptoms:

- Import succeeds but node shows "plugin not installed".
- Tool node has no provider.

Fixes:

- Copy the complete node from a target-Dify export.
- Copy the matching `dependencies[]` entry.
- Install the plugin in the target workspace.
- Do not invent `provider_id` or marketplace identifiers.

## 8a. 空白 Workflow 校验报“缺少结束节点”

症状：

```text
ERROR: graph has no terminal end/answer node
ERROR: workflow graph must contain exactly one end node, found 0
```

原因：

- 青莲的空白 `workflow` 导出默认只有 `start`，没有 `end`。
- 这是空白底座，不是完成应用。

处理：

- 把它当结构参考，不要直接当最终文件。
- 生成时添加 `end` 节点，并用 `start → ... → end` 连线。
- 可直接从 `assets/base-qinglian-workflow.yml` 起稿。

## 8b. HTTP 请求变量没有替换

症状：

- 请求体里仍然是 `{{user_query}}` 原文。
- 搜索 API 收到空查询。
- 鉴权失败，因为 Key 没有被环境变量替换。

原因：

- `http-request.variables` 为空，但 `body` 里用了模板变量。

修复：

```yaml
variables:
- variable: user_query
  value_selector:
  - '1792459508377'
  - sys.query
- variable: tavily_api_key
  value_selector:
  - env
  - TAVILY_API_KEY
```

然后 `body` 中使用 `{{user_query}}`、`{{tavily_api_key}}`。
不要把 API Key 直接写进 `body`；在 `workflow.environment_variables` 中声明 `secret` 类型变量。

## 9. Layout Problems

- Use x step 350.
- Use y step 180 for branches.
- Keep `position` and `positionAbsolute` identical.
- Do not place connected nodes on top of each other.

## 10. Final Rule

`VALIDATION_OK` is a structural check, not a guarantee that a specific Dify instance, model, dataset, or plugin is configured correctly. Always perform one test import and one test run.
