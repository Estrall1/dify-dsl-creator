# Dify App DSL Structure

Dify exports an app as a single YAML document. The root key `kind` is `app`; the graph lives under `workflow.graph`.

## 1. Root

```yaml
app:
  description: ''
  icon: 🤖
  icon_background: '#FFEAD5'
  mode: advanced-chat
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

| Key | Required | Meaning |
|---|---|---|
| `kind` | yes | Must be `app`. |
| `version` | yes | DSL semver, for example `0.3.0`. |
| `app` | yes | App metadata and mode. |
| `dependencies` | yes | Plugin/marketplace dependencies. Use `[]` when no plugin is used. |
| `workflow` | graph modes | Workflow/Chatflow definition. |

青莲 Dify 0.3.1 的 marketplace 依赖结构：

```yaml
dependencies:
- current_identifier: null
  type: marketplace
  value:
    marketplace_plugin_unique_identifier: langgenius/deepseek:0.0.6@<hash>
```

`version` 以目标实例导出为准：标准 Dify 模板默认 `0.3.0`，已验证的青莲 Chatflow 使用 `0.3.1`。

## 2. App

```yaml
app:
  description: 应用描述
  icon: 🤖
  icon_background: '#FFEAD5'
  mode: advanced-chat
  name: 客服助手
  use_icon_as_answer_icon: false
```

`app.mode` values:

- `workflow` — 工作流应用。`start` 定义输入，`end` 定义输出。
- `advanced-chat` — Chatflow / 对话流。`start` 使用 `sys.query`，`answer` 输出回复。
- `agent-chat` — Agent 应用。图结构通常也使用 `start` + `answer`，但 Agent 节点依赖插件合同。
- `chat` / `completion` — 简单对话/文本生成应用，不走本技能的图生成流程。

## 3. Workflow

```yaml
workflow:
  conversation_variables: []
  environment_variables: []
  features: {}
  graph: {}
```

### 3.1 Conversation Variables

仅 `advanced-chat` 常用。格式：

```yaml
conversation_variables:
- description: 记录对话摘要
  id: 22222222-2222-4222-8222-222222222222
  name: summary
  selector:
  - conversation
  - summary
  value: ''
  value_type: string
```

引用：`{{#conversation.summary#}}` 或 `[conversation, summary]`。

### 3.2 Environment Variables

```yaml
environment_variables:
- description: 外部接口地址
  id: 11111111-1111-4111-8111-111111111111
  name: API_BASE_URL
  selector:
  - env
  - API_BASE_URL
  value: https://api.example.com
  value_type: string
```

`value_type`: `string`、`number`、`secret`。

引用：`{{#env.API_BASE_URL#}}` 或 `[env, API_BASE_URL]`。

### 3.3 Features

```yaml
features:
  file_upload:
    allowed_file_extensions:
    - .JPG
    - .PNG
    allowed_file_types:
    - image
    allowed_file_upload_methods:
    - local_file
    - remote_url
    enabled: false
    fileUploadConfig:
      audio_file_size_limit: 50
      batch_count_limit: 5
      file_size_limit: 15
      image_file_size_limit: 10
      video_file_size_limit: 100
      workflow_file_upload_limit: 10
    number_limits: 3
  opening_statement: 你好，我是智能助手。
  retriever_resource:
    enabled: true
  sensitive_word_avoidance:
    enabled: false
  speech_to_text:
    enabled: false
  suggested_questions:
  - 你能做什么？
  suggested_questions_after_answer:
    enabled: false
  text_to_speech:
    enabled: false
    language: ''
    voice: ''
```

Rules:

- 文件输入必须同时设置 `start.variables[].type: file` 或 `file-list` 和 `file_upload.enabled: true`。
- `retriever_resource.enabled: true` 通常用于知识库/引用展示。
- `opening_statement` 可以为 `''` 或 `null`；Chatflow 常用中文开场白。

## 4. Graph

```yaml
graph:
  edges: []
  nodes: []
  viewport:
    x: 0
    y: 0
    zoom: 0.7
```

### 4.1 Node Wrapper

Each graph node follows the Dify/ReactFlow wrapper:

```yaml
- data:
    type: llm
    title: LLM
    desc: ''
    selected: false
    # 节点专属字段
  height: 98
  id: '1730000000002'
  position:
    x: 430
    y: 282
  positionAbsolute:
    x: 430
    y: 282
  selected: false
  sourcePosition: right
  targetPosition: left
  type: custom
  width: 244
```

Required wrapper keys:

- `id` — unique string.
- `type` — `custom`.
- `data.type` — runtime node type.
- `data.title` — canvas title.
- `position` and `positionAbsolute` — `{x, y}`.
- `width`, `height` — canvas size numbers.
- `selected` — boolean.
- `sourcePosition: right`, `targetPosition: left`.

Do not put runtime configuration in `props`; Dify node configuration is inside `data`.

### 4.2 Edge Wrapper

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

- Normal `sourceHandle`: `source`.
- Normal `targetHandle`: `target`.
- Branch nodes override `sourceHandle` with the branch identifier.
- `data.sourceType` and `data.targetType` must match node `data.type`.
- `data.isInIteration` should be boolean; use `false` outside iteration.
- 青莲 Dify 0.3.1 的连线还可能包含 `data.isInLoop`，同样使用布尔值：
  ```yaml
  data:
    isInIteration: false
    isInLoop: false
    sourceType: llm
    targetType: answer
  ```
- `zIndex` 在青莲导出中可能省略，也可能为 `0`。

## 5. Mode Topology

### 5.1 Workflow

```text
start -> ... -> end
```

- Exactly one `start`.
- Exactly one `end`.
- `end.outputs` defines the app output.
- Do not use `answer` as the final workflow output.
- 青莲的空白 workflow 导出默认只有 `start`、没有 `end`；这是底座，不是完成应用。生成时必须补 `end` 和连线。

### 5.2 Advanced Chat / Chatflow

```text
start -> ... -> answer
```

- Exactly one `start`.
- At least one `answer`.
- `start.variables` may be `[]`; the user's chat input is available as `sys.query`.
- Multiple answer nodes are allowed for different branches.

## 6. Branch Handles

### if-else

```yaml
cases:
- case_id: 'true'
  logical_operator: and
  conditions:
  - comparison_operator: contains
    id: '1'
    value: 退款
    variable_selector:
    - '1730000000001'
    - query
```

- First condition branch: `case_id: 'true'`.
- Additional branches: stable string IDs such as `'2'`, `'3'`.
- Else branch: edge `sourceHandle: 'false'`.
- `sourceHandle` uses `case_id`, not display labels `IF` / `ELSE`.

### question-classifier

```yaml
classes:
- id: '1'
  name: 产品咨询
- id: '2'
  name: 售后服务
```

- Edge `sourceHandle` uses the class `id`.
- Class IDs must be unique and stable.
- Every class should have an outgoing edge; otherwise that branch is dead.

## 7. Layout

Recommended:

- Standard Dify main chain x: `80, 430, 780, 1130, 1480...` (350 step).
- 青莲 Dify 空白导出默认 main chain x: `80, 380, 680, 980, 1280...` (300 step).
- Branch sibling y: `282, 162, 402...` (180 step around center).
- Keep `position` and `positionAbsolute` identical.
- Do not stack connected nodes at the same position.

## 8. Import Checklist

1. Save as UTF-8 `.yml` or `.yaml`.
2. In Dify: Studio -> Import DSL -> upload the file.
3. If version is rejected, export a blank app from the same Dify instance and align `version` and root shape.
4. Replace placeholders:
   - `dataset-id-placeholder`
   - model provider/name
   - API URLs
   - plugin dependencies
5. Test one run and inspect each node's input/output panel.
