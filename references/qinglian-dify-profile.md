# 青莲 Dify 适配说明

青莲 Dify 属于 Dify 的企业发行版/定制平台。核心 DSL 通常沿用 Dify 的 `kind: app` + `workflow.graph` 结构，但**不能默认它与上游 Dify 完全一致**。

## 0. 已验证样本（0.3.1 / advanced-chat）

已用一个真实的青莲 Chatflow 导出文件验证过本技能。确认到的结构如下：

- `version: 0.3.1`，`kind: app`，`app.mode: advanced-chat`。
- 根节点固定为 `app`、`dependencies`、`kind`、`version`、`workflow`。
- 节点 ID 可以是时间戳字符串（`'1792459508377'`），也可以是可读字符串（`llm`、`answer`）；同一文件可以混用。
- 插件依赖使用 marketplace 结构：
  ```yaml
  dependencies:
  - current_identifier: null
    type: marketplace
    value:
      marketplace_plugin_unique_identifier: langgenius/deepseek:0.0.6@<hash>
  ```
- `start.data.variables` 可以为 `[]`；用户输入通过 `sys.query` 提供。
- 知识检索的 `query_variable_selector` 使用 `[startNodeId, 'sys.query']`，而不是 `['sys', 'query']`：
  ```yaml
  query_variable_selector:
  - '1792459508377'
  - sys.query
  ```
- LLM 节点除 `model`、`prompt_template`、`context`、`vision`、`variables` 外，还可能包含 `memory`：
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
  第二个 LLM 节点可以完全省略 `memory`。
- `http-request` 可以包含 `retry_config`、`ssl_verify`。
- 连线 `data` 可以包含 `isInIteration`、`isInLoop`；有的连线没有 `zIndex`，有的有。两者都能被接受。
- `if-else` 只导出显式 case（如 `case_id: 'true'`），不导出 else case；else 分支直接用 `sourceHandle: 'false'` 连线。
- `if-else` 条件的 `variable_selector` 可以指向知识检索的 `result`，`varType` 为 `array[object]`。
- `features.file_upload` 内可以包含 `image` 子配置。
- 在 LLM prompt 中观察到按节点标题引用的模板写法，例如
  `{{#知识检索.result | map(attribute='content') | join('\n\n')}}`。
  生成时优先沿用目标文件已有的写法；如果需要最稳妥的引用，使用节点 ID 形式
  `{{#<nodeId>.result#}}`，并在青莲中实际运行验证。

可直接复制的青莲 Chatflow 底座见 `assets/base-qinglian-chatflow.yml`。

### 0.1 空白 Chatflow 导出验证

另一个青莲导出文件 `Test.yml` 被确认是**空白 Chatflow**，不是 `workflow` 模式：

- `app.mode: advanced-chat`
- `version: 0.3.1`
- 3 个节点：`start` → `llm` → `answer`
- 默认模型：`langgenius/volcengine_maas/volcengine_maas`，`name: 豆包`
- 默认依赖：
  ```yaml
  dependencies:
  - current_identifier: null
    type: marketplace
    value:
      marketplace_plugin_unique_identifier: langgenius/volcengine_maas:0.0.44@<hash>
  ```
- 默认节点间距为 300：`x: 80, 380, 680`
- 空白导出的连线只包含 `data.sourceType` / `data.targetType`，可以没有 `isInLoop`、`isInIteration`、`zIndex`
- `viewport.zoom: 1`
- LLM 的 `memory.query_prompt_template` 默认是 `{{#sys.query#}}\n\n{{#sys.files#}}`
- `answer.answer` 默认是 `{{#llm.text#}}`

`assets/base-qinglian-chatflow.yml` 已按这个空白导出重建。

### 0.2 空白 Workflow 导出验证

已拿到青莲真正的空白工作流导出：

- `app.mode: workflow`
- `version: 0.3.1`
- `dependencies: []`
- 图中只有 1 个 `start` 节点，没有 `end` 节点，`edges: []`
- `start.data.variables: []`，高度 `54`
- `features` 与空白 Chatflow 基本一致，包含：
  - `file_upload` 及 `fileUploadConfig`
  - `opening_statement: ''`
  - `retriever_resource.enabled: true`
  - `sensitive_word_avoidance`、`speech_to_text`、`text_to_speech`
- `viewport.zoom: 1`
- 节点默认位置 `x: 80, y: 282`

注意：空白 workflow 导出本身**不能通过最终完整性校验**，因为它没有 `end` 节点。校验器会报：

```text
ERROR: graph has no terminal end/answer node
ERROR: workflow graph must contain exactly one end node, found 0
```

这是预期行为。空白导出只作为结构底座；生成时必须补上 `end` 节点和连线。

- `assets/qinglian-blank-workflow.yml` 保存了这个原始空白结构。
- `assets/base-qinglian-workflow.yml` 是可用最小模板：`start(query) → llm → end`，根结构和 `features` 已按空白 workflow 校准，并补上火山引擎 `豆包` 依赖。

## 1. 不要直接假设的点

- DSL 版本号（`version`）是否与上游一致。
- 导入/导出格式是 YAML 还是 JSON。
- 模型 provider / model name 是否使用平台自定义名称。
- 插件、工具、Agent 策略的 marketplace 标识和 `dependencies` 格式。
- 知识库 `dataset_ids` 的获取方式。
- 文件上传配置（`file_upload` / `fileUploadConfig`）字段是否一致。
- 是否存在青莲自定义节点类型或禁用节点。
- 系统变量、环境变量、会话变量的可用范围。

## 2. 最稳妥的适配流程

1. 在青莲 Dify 中新建一个空白应用：
   - 一个空白 `workflow` 应用
   - 一个空白 `advanced-chat` 应用
2. 分别导出 DSL，保存为：
   - `qinglian-blank-workflow.yml` 或 `.json`
   - `qinglian-blank-chatflow.yml` 或 `.json`
3. 先确认导出文件的 `app.mode`。如果名为 “工作流” 但导出是 `advanced-chat`，说明它仍是 Chatflow，不能当作 workflow 底座。
4. 用本技能校验：
   ```bash
   python scripts/validate_dify_dsl.py qinglian-blank-workflow.yml
   ```
5. 如果通过，直接把该文件作为生成底座，复制它的 `version`、`app`、`workflow.features` 和空图结构。
6. 如果不通过，记录报错字段，按青莲导出的真实结构扩展本技能。

## 3. 需要向用户确认的信息

- 青莲 Dify 的版本号或产品版本。
- DSL 导入页面接受 `.yml/.yaml` 还是 `.json`。
- 一个空白 workflow 导出文件。
- 一个空白 Chatflow 导出文件。
- 模型中实际可选的 `provider` 和 `name`。
- 如果需要知识库：实际 dataset ID 或获取路径。
- 如果需要工具/插件/Agent：导出一个包含该节点的应用，并保留 `dependencies`。
- 是否需要使用青莲自定义的环境变量、模型网关或 API 地址。

## 4. 生成时的默认策略

- 青莲 `advanced-chat` 优先使用 `assets/base-qinglian-chatflow.yml`（已按真实空白导出重建）。
- 青莲 `workflow` 优先使用 `assets/base-qinglian-workflow.yml`（根结构和 `features` 已按真实空白 workflow 导出校准）。
- 如果需要查看原始空白结构，使用 `assets/qinglian-blank-workflow.yml`；它只有 `start`，不能直接作为完成应用导入使用。
- 一旦拿到青莲空白导出，立即替换为青莲骨架。
- 不生成青莲未确认的插件、工具、Agent 节点。
- 不把上游 Dify Marketplace 的插件标识直接写入青莲 DSL。
- 生成后必须运行校验，并在青莲 Dify 中做一次测试导入。

## 5. 兼容性判断

| 现象 | 判断 |
|---|---|
| 青莲导出的 YAML 能被本技能解析并通过 `VALIDATION_OK` | 结构高度兼容，可直接复用本技能 |
| 仅 `version` 不同 | 复制青莲的 `version` 即可 |
| `features` / `fileUploadConfig` 字段不同 | 以青莲空白导出为准，更新模板 |
| 节点 `data` 字段不同 | 以青莲同类节点导出为准，扩展 `node-contracts.md` |
| 导出为 JSON | 需要为技能增加 JSON 适配层，不能直接套用 YAML 规则 |
| 插件/Agent 节点缺少 `dependencies` | 从青莲导出的应用复制完整依赖 |
