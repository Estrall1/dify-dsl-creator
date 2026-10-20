# Dify Workflow Patterns

Use these patterns as starting points. Always adapt node IDs and variable references, then run the validator.

## 1. Minimal Chatflow

Mode: `advanced-chat`

```text
start -> llm -> answer
```

Node inventory:

| Node | Type | Purpose | Outputs |
|---|---|---|---|
| start | `start` | 接收聊天输入 | `sys.query` |
| llm | `llm` | 生成回答 | `text` |
| answer | `answer` | 流式输出 | none |

Key bindings:

- `llm.prompt_template[1].text`: `{{#sys.query#}}`
- `answer.answer`: `{{#llmId.text#}}`

## 2. RAG Chatflow

Mode: `advanced-chat`

```text
start -> knowledge-retrieval -> llm -> answer
```

Node inventory:

| Node | Type | Purpose | Outputs |
|---|---|---|---|
| start | `start` | 聊天输入 | `sys.query` |
| retrieval | `knowledge-retrieval` | 检索知识库 | `result` |
| llm | `llm` | 基于检索结果回答 | `text` |
| answer | `answer` | 输出 | none |

Key bindings:

```yaml
# knowledge-retrieval
query_variable_selector: [sys, query]
dataset_ids: [your-dataset-id]

# llm
context:
  enabled: true
  variable_selector: [retrievalId, result]
prompt_template:
- role: system
  text: 你是知识库助手。请只依据检索上下文回答；上下文不足时明确说明。
- role: user
  text: '{{#sys.query#}}'
```

Pitfalls:

- `dataset_ids` must be real IDs.
- `retriever_resource.enabled: true` if you want citation display.
- Do not reference `knowledge-retrieval.result` from a node that is not downstream of it.

## 3. Question Classifier Routing

Mode: `workflow`

```text
start -> classifier -> llm_a -> aggregator -> end
                   \-> llm_b -> aggregator
```

Node inventory:

| Node | Type | Purpose |
|---|---|---|
| start | `start` | 输入 `query` |
| classifier | `question-classifier` | 分类 |
| llm_a | `llm` | 类别 A 回答 |
| llm_b | `llm` | 类别 B 回答 |
| aggregator | `variable-aggregator` | 合并分支输出 |
| end | `end` | 输出 `result` |

Edges:

```text
start -> classifier                      (source)
classifier -'1'-> llm_a                  (class id)
classifier -'2'-> llm_b                  (class id)
llm_a -> aggregator                      (source)
llm_b -> aggregator                      (source)
aggregator -> end                        (source)
```

Bindings:

```yaml
# classifier
query_variable_selector: [startId, query]
classes:
- id: '1'
  name: 产品咨询
- id: '2'
  name: 售后服务

# aggregator
variables:
- [llm_a_id, text]
- [llm_b_id, text]
output_type: string

# end
outputs:
- variable: result
  value_selector: [aggregatorId, output]
```

Pitfalls:

- Every class must have an outgoing edge.
- Do not use `IF` / `ELSE` as classifier handles; use class IDs.
- Branch LLM outputs are both `text`.

## 4. If-Else Workflow

Mode: `workflow`

```text
start -> if-else -true-> llm_a -> end
                \-false-> llm_b -> end
```

Key bindings:

```yaml
# if-else
cases:
- case_id: 'true'
  logical_operator: and
  conditions:
  - id: '1'
    comparison_operator: contains
    value: 退款
    variable_selector: [startId, query]
```

Edges:

- true: `sourceHandle: 'true'`
- else: `sourceHandle: 'false'`

Pitfalls:

- Do not create `ifElseResult` outputs.
- Route with edges, not by referencing `if-else` as a variable.

## 5. HTTP API Workflow

Mode: `workflow`

```text
start -> http-request -> code -> end
```

Node inventory:

| Node | Type | Purpose |
|---|---|---|
| start | `start` | 输入 `query` |
| http | `http-request` | 调用外部 API |
| code | `code` | 解析/整理响应 |
| end | `end` | 输出 |

Key bindings:

```yaml
# http-request
method: post
url: '{{#env.API_BASE_URL#}}/v1/answer'
headers: 'Content-Type:application/json'
body:
  type: json
  data:
  - key: query
    type: text
    value: '{{#startId.query#}}'
authorization:
  type: no-auth
  config: null

# code
variables:
- variable: response
  value_selector: [httpId, body]
outputs:
  result:
    type: string
    children: null
```

Pitfalls:

- `http-request.url` must not be empty.
- Use `body.data` for JSON fields.
- Output key is `body`, not `response` or `system_httpResult`.
- Declare environment variables in `workflow.environment_variables`.

## 6. Parameter Extraction Workflow

Mode: `workflow`

```text
start -> parameter-extractor -> llm -> end
```

Key bindings:

```yaml
# parameter-extractor
query: [startId, query]
reasoning_mode: prompt
parameters:
- name: city
  type: string
  description: 城市名称
  required: true
```

Downstream prompt can use `{{#extractorId.city#}}`. If extraction may fail, check `{{#extractorId.__is_success#}}` or route with an if-else node.

Pitfalls:

- Outputs are parameter names, not `fields`.
- `parameter-extractor.query` is a selector array, not `query_variable_selector`.
- Do not add per-parameter custom input keys to the LLM node.

## 7. File Analysis Workflow

Mode: `advanced-chat`

```text
start -> document-extractor -> llm -> answer
```

Requirements:

```yaml
# start
variables:
- variable: files
  label: 上传文件
  type: file-list
  required: true
  options: []

# workflow.features.file_upload
enabled: true
allowed_file_types: [document]
allowed_file_upload_methods: [local_file, remote_url]
number_limits: 3

# document-extractor
variable_selector: [startId, files]

# llm
prompt_template:
- role: user
  text: |
    请阅读以下文档内容并回答问题：
    {{#extractorId.text#}}

    问题：{{#sys.query#}}
```

Pitfalls:

- File upload must be enabled.
- Downstream nodes use `document-extractor.text`, not the raw file list.
- For chatflow, chat input is `sys.query`.

## 8. Template Transform Assembly

Use `template-transform` when a prompt needs deterministic multi-source text assembly.

```text
start -> knowledge-retrieval -> template-transform -> llm -> answer
```

```yaml
# template-transform
template: |
  用户问题：{{ query }}
  知识库内容：{{ context }}
  请给出带引用的回答。
variables:
- variable: query
  value_selector: [sys, query]
- variable: context
  value_selector: [retrievalId, result]

# llm prompt
- role: user
  text: '{{#transformId.output#}}'
```

Pitfalls:

- `template` uses `{{ query }}` local variables.
- `variables` maps each local name to a Dify selector.
- Do not put FastGPT syntax in the template.

## 9. Conversation Variable Memory

Mode: `advanced-chat`

```text
start -> llm -> variable-assigner -> answer
```

```yaml
# workflow.conversation_variables
- name: last_answer
  description: 上一轮回答
  id: 22222222-2222-4222-8222-222222222222
  selector:
  - conversation
  - last_answer
  value: ''
  value_type: string

# variable-assigner
items:
- variable_selector: [conversation, last_answer]
  input_type: variable
  value: [llmId, text]
  operation: overwrite
```

Reference later with `{{#conversation.last_answer#}}`.

Pitfalls:

- Declare the conversation variable first.
- Variable assigner has no output; the answer node should reference the LLM output directly.

## 10. Multi-Platform Content Factory With QA Loop

Mode: `advanced-chat`

```text
start
  -> parameter-extractor
  -> question-classifier
      -> branch A: llm -> code check -> if-else
          -> revise llm -> aggregator
          -> pass -> aggregator
      -> branch B: llm -> llm -> code check -> if-else
          -> revise llm -> aggregator
          -> pass -> aggregator
      -> branch C: llm -> code check -> if-else
          -> revise llm -> aggregator
          -> pass -> aggregator
      -> fallback: llm
  -> variable-aggregator
  -> template-transform
  -> answer
```

Use this when the same request can produce different formats, and each format needs its own quality gate.

Pitfalls:

- Every `question-classifier` class needs an outgoing edge.
- Every `if-else` needs both the `case_id` edge and the `false` edge.
- Put each branch's pass and revise paths into a branch-level `variable-aggregator` before the final aggregator.
- Code QA nodes should output a string `status` (`ok` / `revise`) plus a `reason`; use `comparison_operator: is` in the if-else.
- All aggregator inputs must be the same type, normally `string`.
- See `examples/qinglian-content-factory-chatflow.yml` for a 23-node working example.
