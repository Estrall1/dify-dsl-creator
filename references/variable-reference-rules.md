# Dify Variable Reference Rules

Dify has two reference syntaxes. Using the wrong one is the most common cause of empty variables or failed imports.

## 1. Structured Selectors

Use arrays in configuration fields:

```yaml
value_selector:
- '1730000000002'
- text
```

```yaml
query_variable_selector:
- sys
- query
```

The first element is a node ID or a pseudo-scope; the second is an output key.

Allowed pseudo-scopes:

| Scope | Meaning | Example |
|---|---|---|
| `sys` | System variables | `[sys, query]`, `[sys, files]` |
| `env` | Environment variables | `[env, API_BASE_URL]` |
| `conversation` | Conversation variables | `[conversation, summary]` |

青莲 Dify 0.3.1 的导出可能把系统变量写成“起始节点 ID + `sys.*`”：

```yaml
query_variable_selector:
- '1792459508377'
- sys.query
```

这等价于 `[sys, query]`；校验器已兼容这种写法。生成新文件时两种写法都可，但优先保持目标实例导出的风格一致。

## 2. Template References

Use inside prompts, answer text, URLs, headers, and string body values:

```text
{{#1730000000002.text#}}
{{#sys.query#}}
{{#sys.files#}}
{{#env.API_BASE_URL#}}
{{#conversation.summary#}}
```

Rules:

- Node reference: `{{#nodeId.outputKey#}}`.
- No spaces inside the delimiters.
- The referenced node must exist and be upstream of the consuming node.
- Prefer node IDs over display titles in newly generated files.
- 青莲 Dify 0.3.1 的真实导出中，LLM prompt 里出现过按节点标题引用的写法，例如
  `{{#知识检索.result | map(attribute='content') | join('\n\n')}}`。
  修复已有青莲文件时不要盲目把标题改成 ID；如果原文件能正常运行，保持原写法，并在导入后做一次运行测试。
- Do not use dotted subpaths such as `{{#node.result.name#}}`; pass the whole output or transform it first.

## 3. System Variables

Common values:

| Variable | Meaning |
|---|---|
| `sys.query` | Current user chat/query input |
| `sys.files` | Uploaded files |
| `sys.conversation_id` | Conversation ID |
| `sys.user_id` | User ID |
| `sys.dialogue_count` | Dialogue turn count |
| `sys.app_id` | App ID |
| `sys.workflow_id` | Workflow ID |
| `sys.workflow_run_id` | Workflow run ID |

In `workflow` mode, prefer the explicit start variable, for example `{{#1730000000001.query#}}`.
In `advanced-chat`, `{{#sys.query#}}` is the normal chat input.

## 4. Environment Variables

Declare first:

```yaml
environment_variables:
- name: API_BASE_URL
  value: https://api.example.com
  value_type: string
```

Then use:

```text
{{#env.API_BASE_URL#}}
```

or:

```yaml
value_selector:
- env
- API_BASE_URL
```

Do not reference an undeclared environment variable.

## 5. Conversation Variables

Declare first:

```yaml
conversation_variables:
- name: summary
  value: ''
  value_type: string
```

Use:

```text
{{#conversation.summary#}}
```

or:

```yaml
value_selector:
- conversation
- summary
```

Conversation variables are normally written by `variable-assigner`.

## 6. Template Transform Is Different

`template-transform.template` uses local Jinja variables declared in `variables`:

```yaml
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

- `{{ query }}` is a local variable.
- `{{#node.output#}}` is a Dify reference and is not the normal template-transform style.
- Do not mix the two styles in the same template.

## 7. Output Keys

| Node type | Valid outputs |
|---|---|
| `start` | Declared `variables[].variable` |
| `end` | none |
| `answer` | none |
| `llm` | `text`, `reasoning_content`, `usage`, `finish_reason`, `structured_output` |
| `knowledge-retrieval` | `result` |
| `question-classifier` | `class_name`, `class_id` |
| `if-else` | none |
| `code` | Keys declared in `outputs` |
| `template-transform` | `output` |
| `http-request` | `body`, `status_code`, `headers`, `files` |
| `variable-aggregator` | `output` |
| `variable-assigner` | none |
| `parameter-extractor` | Parameter names plus `__is_success`, `__reason` |
| `document-extractor` | `text` |
| `iteration` | `output` |
| `loop` | `output` |
| `agent` | `text`, `files`, `json` |
| `tool` | `text`, `files`, `json` |

Do not invent `result` on `llm`, `text` on `knowledge-retrieval`, or field-level outputs on `parameter-extractor`.

## 8. Upstream Rule

A referenced node must be reachable upstream through visible edges.

Valid:

```text
start -> knowledge-retrieval -> llm -> answer
```

`llm` may reference `knowledge-retrieval.result` because it is upstream.

Invalid:

```text
start -> llm -> answer
knowledge-retrieval (isolated)
```

`llm` cannot reference an isolated `knowledge-retrieval`.

A direct edge from the referenced node to the consuming node is not required when both are on the same chain. Edges express execution order, not each data binding.

## 9. Invalid Syntax

Reject:

```text
{{$nodeId.outputKey$}}          # FastGPT syntax
{{nodeId.outputKey}}            # legacy syntax
["nodeId", "outputKey"]         # inside prompt/answer text
{{#node.title#}}                # display title instead of ID
{{#node.result.name#}}          # unsupported subpath
{{#userGuide.variables.x#}}     # userGuide is not a runtime output
```

## 10. Branch Variables

- `question-classifier` result: use `{{#classifierId.class_name#}}` or a selector.
- `if-else` has no output variable; route with edges.
- After branch-specific LLMs, merge with `variable-aggregator` and reference `{{#aggregatorId.output#}}`.
