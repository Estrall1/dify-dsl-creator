# Dify Node Contracts

Every node object is wrapped as described in `dsl-structure.md`. This file documents the fields inside `data`.

## 1. Common Fields

```yaml
data:
  type: llm
  title: LLM
  desc: ''
  selected: false
```

- `type` — runtime node type.
- `title` — Chinese canvas title.
- `desc` — optional description.
- `selected` — boolean, normally `false`.

## 2. `start`

```yaml
data:
  type: start
  title: 开始
  desc: ''
  selected: false
  variables:
  - variable: query
    label: 用户输入
    type: text-input
    required: true
    max_length: 48
    options: []
```

`variables[].type` allowed values:

- `text-input`
- `paragraph`
- `select`
- `number`
- `file`
- `file-list`
- `checkbox`
- `json`

Rules:

- `variable` must be a safe identifier.
- `select` requires non-empty `options`.
- `file` / `file-list` requires `workflow.features.file_upload.enabled: true`.
- In `advanced-chat`, `variables: []` is valid; use `{{#sys.query#}}`.

Outputs: each declared variable name.

## 3. `end`

```yaml
data:
  type: end
  title: 结束
  desc: ''
  selected: false
  outputs:
  - variable: result
    value_selector:
    - '1730000000002'
    - text
```

Rules:

- `outputs` must be non-empty in `workflow` mode.
- `variable` must be a safe identifier.
- `value_selector` is `[nodeId, outputKey]`.

Outputs: none.

## 4. `answer`

```yaml
data:
  type: answer
  title: 直接回复
  desc: ''
  selected: false
  answer: '{{#1730000000002.text#}}'
  variables: []
```

Rules:

- `answer` must be a non-empty string.
- Use `{{#nodeId.outputKey#}}` for dynamic content.
- Do not put arrays or FastGPT syntax in `answer`.

Outputs: none.

## 5. `llm`

```yaml
data:
  type: llm
  title: LLM
  desc: ''
  selected: false
  model:
    provider: openai
    name: gpt-4o-mini
    mode: chat
    completion_params:
      temperature: 0.7
  prompt_template:
  - role: system
    text: 你是一个专业的中文助手。
  - role: user
    text: '{{#sys.query#}}'
  variables: []
  context:
    enabled: false
    variable_selector: []
  vision:
    enabled: false
```

Rules:

- `model.provider`, `model.name`, `model.mode`, `model.completion_params` required.
- `mode`: `chat` or `completion`.
- `prompt_template` must be non-empty; roles are `system`, `user`, `assistant`.
- `context.enabled: true` requires `context.variable_selector`, normally `[knowledgeRetrievalId, result]`.
- `vision.enabled` must be boolean.
- `variables` is optional and follows `{variable, value_selector}`.
- Do not add custom input keys to `llm.data`; put all context into prompts or `context`.
- 青莲 Dify 0.3.1 的 LLM 节点可能包含 `memory`，也可能省略：
  ```yaml
  memory:
    query_prompt_template: '{{#sys.query#}}'
    role_prefix:
      assistant: ''
      user: ''
    window:
      enabled: false
      size: 10
  ```
  Chatflow 中用户可以只写 system prompt，把用户输入交给 `memory.query_prompt_template`。
- 青莲导出中 `prompt_template` 的消息可能带 `id`；保留或省略通常都不影响结构校验，生成时以目标导出的写法为准。

Outputs: `text`, `reasoning_content`, `usage`, `finish_reason`, `structured_output`.

## 6. `knowledge-retrieval`

```yaml
data:
  type: knowledge-retrieval
  title: 知识检索
  desc: ''
  selected: false
  dataset_ids:
  - dataset-id-placeholder
  retrieval_mode: multiple
  query_variable_selector:
  - sys
  - query
  multiple_retrieval_config:
    top_k: 4
    score_threshold: null
    reranking_enable: false
    reranking_mode: weighted_score
    reranking_model:
      provider: ''
      model: ''
    weights:
      vector_setting:
        vector_weight: 0.7
        embedding_provider_name: ''
        embedding_model_name: ''
      keyword_setting:
        keyword_weight: 0.3
```

Rules:

- `dataset_ids` must contain real knowledge base IDs before use.
- `retrieval_mode`: `single` or `multiple`.
- `multiple_retrieval_config` required for `multiple`; `single_retrieval_config` required for `single`.
- `query_variable_selector` is normally `[sys, query]` or `[startId, query]`.
- 青莲 Dify 0.3.1 导出使用 `[startNodeId, 'sys.query']`：
  ```yaml
  query_variable_selector:
  - '1792459508377'
  - sys.query
  ```

Outputs: `result`.

Downstream LLM usage:

```yaml
context:
  enabled: true
  variable_selector:
  - '1730000000102'
  - result
```

## 7. `question-classifier`

```yaml
data:
  type: question-classifier
  title: 问题分类
  desc: ''
  selected: false
  model:
    provider: openai
    name: gpt-4o-mini
    mode: chat
    completion_params:
      temperature: 0
  query_variable_selector:
  - '1730000000001'
  - query
  instruction: 请判断用户问题属于哪个类别。
  classes:
  - id: '1'
    name: 产品咨询
  - id: '2'
    name: 售后服务
```

Rules:

- `classes` must be non-empty.
- `id` unique and stable; edge `sourceHandle` equals the class ID.
- `name` is user-facing Chinese text.
- `query_variable_selector` is required.

Outputs: `class_name`, `class_id`.

## 8. `if-else`

```yaml
data:
  type: if-else
  title: 条件分支
  desc: ''
  selected: false
  cases:
  - case_id: 'true'
    logical_operator: and
    conditions:
    - id: '1'
      comparison_operator: contains
      value: 退款
      variable_selector:
      - '1730000000001'
      - query
```

Rules:

- `cases` non-empty.
- `case_id: 'true'` for the first branch; additional cases use stable IDs.
- `case_id: 'false'` is reserved for the else edge handle.
- `logical_operator`: `and` or `or`.
- `conditions` non-empty; each has `id`, `comparison_operator`, `variable_selector`.
- `value` is required except for empty/exists operators.
- 青莲 Dify 0.3.1 的 condition 还带 `varType`，例如 `varType: array[object]`，用于知识检索结果：
  ```yaml
  conditions:
  - comparison_operator: empty
    id: f820e7c5-1f88-4bb7-98f4-c1cf45064dac
    value: ''
    varType: array[object]
    variable_selector:
    - '1792459850498'
    - result
  ```
- 青莲导出可能只写显式 case（如 `true`），不写 else case；else 仍用 `sourceHandle: 'false'`。

Common comparison operators:

```text
contains, not contains, start with, end with,
is, is not, empty, not empty, =, ≠, >, <, ≥, ≤,
in, not in, all of, exists, not exists
```

Outputs: none. Branches are expressed only by edges.

## 9. `code`

```yaml
data:
  type: code
  title: 代码执行
  desc: ''
  selected: false
  code_language: python3
  code: |
    def main(query: str) -> dict:
        return {"result": query.strip()}
  variables:
  - variable: query
    value_selector:
    - '1730000000001'
    - query
  outputs:
    result:
      type: string
      children: null
```

Rules:

- `code_language`: `python3` or `javascript`.
- Python signature: `def main(arg1, arg2) -> dict`; return a dict whose keys match `outputs`.
- JavaScript signature: `function main({arg1, arg2}) { return {result: ...}; }`.
- `variables` map node inputs into function arguments.
- `outputs` must be non-empty and match returned keys.

Outputs: keys declared in `outputs`.

## 10. `template-transform`

```yaml
data:
  type: template-transform
  title: 模板转换
  desc: ''
  selected: false
  template: |
    用户问题：{{ query }}
    检索结果：{{ context }}
  variables:
  - variable: query
    value_selector:
    - '1730000000001'
    - query
  - variable: context
    value_selector:
    - '1730000000002'
    - result
```

Rules:

- `template` uses Jinja variables declared in `variables`, for example `{{ query }}`.
- Do not use `{{#node.output#}}` in the template body; use selectors in `variables` instead.
- `variables` entries use `{variable, value_selector}`.

Outputs: `output`.

## 11. `http-request`

```yaml
data:
  type: http-request
  title: HTTP 请求
  desc: ''
  selected: false
  method: post
  url: '{{#env.API_BASE_URL#}}/v1/answer'
  headers: 'Content-Type:application/json'
  params: ''
  body:
    type: json
    data:
    - key: query
      type: text
      value: '{{#1730000000001.query#}}'
  authorization:
    type: no-auth
    config: null
  timeout:
    max_connect_timeout: 10
    max_read_timeout: 60
    max_write_timeout: 10
  variables: []
```

Rules:

- `method`: `get`, `post`, `put`, `patch`, `delete`, `head`, `options`.
- `url` must be non-empty and start with `http://` / `https://`, or contain a Dify template reference.
- `headers` and `params` are strings; Dify stores them in `key:value` line style.
- `body.type`: `none`, `json`, `form-data`, `x-www-form-urlencoded`, `raw-text`, `binary`.
- For JSON bodies, use `body.data[]` with `key`, `type`, `value`.
- `authorization.type`: `no-auth` or `api-key`.
- 青莲 Dify 0.3.1 还可能导出：
  ```yaml
  retry_config:
    max_retries: 3
    retry_interval: 100
    retry_enabled: true
  ssl_verify: true
  ```
  没有这些字段时也可以正常工作；生成时按目标导出的完整度决定。

Outputs: `body`, `status_code`, `headers`, `files`.

## 12. `variable-aggregator`

```yaml
data:
  type: variable-aggregator
  title: 变量聚合
  desc: ''
  selected: false
  output_type: string
  variables:
  - - '1730000000002'
    - text
  - - '1730000000003'
    - text
```

Rules:

- `variables` non-empty; each item is a selector.
- All branches must produce a compatible output type.
- `output_type` should match the selected outputs.

Outputs: `output`.

## 13. `parameter-extractor`

```yaml
data:
  type: parameter-extractor
  title: 参数提取
  desc: ''
  selected: false
  model:
    provider: openai
    name: gpt-4o-mini
    mode: chat
    completion_params:
      temperature: 0
  query:
  - '1730000000001'
  - query
  instruction: 从用户问题中提取结构化参数。
  reasoning_mode: prompt
  parameters:
  - name: name
    type: string
    description: 用户姓名
    required: true
```

Rules:

- `query` is `[nodeId, outputKey]`.
- `parameters` non-empty; names safe and unique.
- `reasoning_mode`: `prompt` or `function_call`.
- Parameter types: `string`, `number`, `boolean`, `object`, `array[string]`, `array[number]`, `array[boolean]`, `array[object]`.

Outputs: each parameter name, plus `__is_success` and `__reason`.

## 14. `document-extractor`

```yaml
data:
  type: document-extractor
  title: 文档提取器
  desc: ''
  selected: false
  variable_selector:
  - '1730000000001'
  - files
```

Rules:

- `variable_selector` must point to a `file` or `file-list` start variable.
- File upload must be enabled in `workflow.features.file_upload`.

Outputs: `text`.

## 15. `variable-assigner`

Newer DSL:

```yaml
data:
  type: variable-assigner
  title: 变量赋值
  desc: ''
  selected: false
  items:
  - variable_selector:
    - conversation
    - summary
    input_type: variable
    value:
    - '1730000000002'
    - text
    operation: overwrite
```

Rules:

- Target is usually `[conversation, name]`.
- `input_type`: `variable` or `constant`.
- `operation`: `overwrite`, `clear`, `append`, `extend`, `set`.
- Legacy DSL may use `variables`; verify against the target Dify export.

Outputs: none.

## 16. Restricted / Version-Sensitive Nodes

Do not hand-write these without a real contract:

- `iteration` — requires `iterator_selector`, `output_selector`, `start_node_id`, child `iteration-start`, and version-specific parent/child layout.
- `loop` — requires `start_node_id`, loop conditions, and version-specific child layout.
- `agent` — requires agent strategy plugin metadata and `agent_parameters`.
- `tool` — requires plugin provider, tool name, parameter schema, and `dependencies`.
- `datasource`, `trigger` — version-specific.

Correct approach:

1. Ask the user to export an app containing that node.
2. Copy the complete node object and its plugin dependency entry.
3. Change only scenario values and IDs.
4. Run the validator with `--allow-unknown-types` only if the exported type is not yet in the whitelist.
