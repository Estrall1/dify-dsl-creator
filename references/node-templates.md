# Copyable Dify Node Templates

Copy a node object into `workflow.graph.nodes`, then replace `id`, `position`, `title`, and scenario values. Keep wrapper keys.

## `start` — Workflow

```yaml
- data:
    desc: ''
    selected: false
    title: 开始
    type: start
    variables:
    - label: 用户输入
      max_length: 48
      options: []
      required: true
      type: text-input
      variable: query
  height: 90
  id: '1730000000001'
  position:
    x: 80
    y: 282
  positionAbsolute:
    x: 80
    y: 282
  selected: false
  sourcePosition: right
  targetPosition: left
  type: custom
  width: 244
```

## `start` — Chatflow

```yaml
- data:
    desc: ''
    selected: false
    title: 开始
    type: start
    variables: []
  height: 54
  id: '1730000000001'
  position:
    x: 80
    y: 282
  positionAbsolute:
    x: 80
    y: 282
  selected: false
  sourcePosition: right
  targetPosition: left
  type: custom
  width: 244
```

## `end`

```yaml
- data:
    desc: ''
    outputs:
    - value_selector:
      - '1730000000002'
      - text
      variable: result
    selected: false
    title: 结束
    type: end
  height: 107
  id: '1730000000003'
  position:
    x: 780
    y: 282
  positionAbsolute:
    x: 780
    y: 282
  selected: false
  sourcePosition: right
  targetPosition: left
  type: custom
  width: 244
```

## `answer`

```yaml
- data:
    answer: '{{#1730000000002.text#}}'
    desc: ''
    selected: false
    title: 直接回复
    type: answer
    variables: []
  height: 103
  id: '1730000000003'
  position:
    x: 780
    y: 282
  positionAbsolute:
    x: 780
    y: 282
  selected: false
  sourcePosition: right
  targetPosition: left
  type: custom
  width: 244
```

## `llm`

```yaml
- data:
    context:
      enabled: false
      variable_selector: []
    desc: ''
    model:
      completion_params:
        temperature: 0.7
      mode: chat
      name: gpt-4o-mini
      provider: openai
    prompt_template:
    - role: system
      text: 你是一个专业的中文助手。
    - role: user
      text: '{{#sys.query#}}'
    selected: false
    title: LLM
    type: llm
    variables: []
    vision:
      enabled: false
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

RAG variant:

```yaml
    context:
      enabled: true
      variable_selector:
      - '1730000000102'
      - result
```

## `knowledge-retrieval`

```yaml
- data:
    dataset_ids:
    - dataset-id-placeholder
    desc: ''
    multiple_retrieval_config:
      reranking_enable: false
      reranking_mode: weighted_score
      reranking_model:
        model: ''
        provider: ''
      score_threshold: null
      top_k: 4
      weights:
        keyword_setting:
          keyword_weight: 0.3
        vector_setting:
          embedding_model_name: ''
          embedding_provider_name: ''
          vector_weight: 0.7
    query_variable_selector:
    - sys
    - query
    retrieval_mode: multiple
    selected: false
    title: 知识检索
    type: knowledge-retrieval
  height: 91
  id: '1730000000102'
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

## `question-classifier`

```yaml
- data:
    classes:
    - id: '1'
      name: 产品咨询
    - id: '2'
      name: 售后服务
    desc: ''
    instruction: 请根据用户问题判断它属于哪个类别。
    model:
      completion_params:
        temperature: 0
      mode: chat
      name: gpt-4o-mini
      provider: openai
    query_variable_selector:
    - '1730000000001'
    - query
    selected: false
    title: 问题分类
    type: question-classifier
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

Branch edges use `sourceHandle: '1'` and `sourceHandle: '2'`.

## `if-else`

```yaml
- data:
    cases:
    - case_id: 'true'
      conditions:
      - comparison_operator: contains
        id: '1'
        value: 退款
        variable_selector:
        - '1730000000001'
        - query
      id: 'true'
      logical_operator: and
    desc: ''
    selected: false
    title: 条件分支
    type: if-else
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

- True branch edge: `sourceHandle: 'true'`.
- Else branch edge: `sourceHandle: 'false'`.
- Additional cases: `case_id: '2'`, `'3'`, etc.

## `code`

```yaml
- data:
    code: |
      def main(query: str) -> dict:
          return {"result": query.strip()}
    code_language: python3
    desc: ''
    outputs:
      result:
        children: null
        type: string
    selected: false
    title: 代码执行
    type: code
    variables:
    - value_selector:
      - '1730000000001'
      - query
      variable: query
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

## `template-transform`

```yaml
- data:
    desc: ''
    selected: false
    template: |
      用户问题：{{ query }}
      检索结果：{{ context }}
    title: 模板转换
    type: template-transform
    variables:
    - value_selector:
      - '1730000000001'
      - query
      variable: query
    - value_selector:
      - '1730000000002'
      - result
      variable: context
  height: 98
  id: '1730000000003'
  position:
    x: 780
    y: 282
  positionAbsolute:
    x: 780
    y: 282
  selected: false
  sourcePosition: right
  targetPosition: left
  type: custom
  width: 244
```

## `http-request`

```yaml
- data:
    authorization:
      config: null
      type: no-auth
    body:
      data:
      - key: query
        type: text
        value: '{{#1730000000001.query#}}'
      type: json
    desc: ''
    headers: 'Content-Type:application/json'
    method: post
    params: ''
    selected: false
    timeout:
      max_connect_timeout: 10
      max_read_timeout: 60
      max_write_timeout: 10
    title: HTTP 请求
    type: http-request
    url: '{{#env.API_BASE_URL#}}/v1/answer'
    variables: []
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

## `variable-aggregator`

```yaml
- data:
    desc: ''
    output_type: string
    selected: false
    title: 变量聚合
    type: variable-aggregator
    variables:
    - - '1730000000002'
      - text
    - - '1730000000003'
      - text
  height: 98
  id: '1730000000004'
  position:
    x: 1130
    y: 282
  positionAbsolute:
    x: 1130
    y: 282
  selected: false
  sourcePosition: right
  targetPosition: left
  type: custom
  width: 244
```

## `parameter-extractor`

```yaml
- data:
    desc: ''
    instruction: 从用户问题中提取结构化参数。
    model:
      completion_params:
        temperature: 0
      mode: chat
      name: gpt-4o-mini
      provider: openai
    parameters:
    - description: 用户姓名
      name: name
      required: true
      type: string
    query:
    - '1730000000001'
    - query
    reasoning_mode: prompt
    selected: false
    title: 参数提取
    type: parameter-extractor
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

## `document-extractor`

```yaml
- data:
    desc: ''
    selected: false
    title: 文档提取器
    type: document-extractor
    variable_selector:
    - '1730000000001'
    - files
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

## `variable-assigner`

```yaml
- data:
    desc: ''
    items:
    - input_type: variable
      operation: overwrite
      value:
      - '1730000000002'
      - text
      variable_selector:
      - conversation
      - summary
    selected: false
    title: 变量赋值
    type: variable-assigner
  height: 98
  id: '1730000000003'
  position:
    x: 780
    y: 282
  positionAbsolute:
    x: 780
    y: 282
  selected: false
  sourcePosition: right
  targetPosition: left
  type: custom
  width: 244
```

## Edge Templates

Normal:

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

Classifier branch:

```yaml
- data:
    isInIteration: false
    sourceType: question-classifier
    targetType: llm
  id: edge-classifier-1
  source: '1730000000002'
  sourceHandle: '1'
  target: '1730000000003'
  targetHandle: target
  type: custom
  zIndex: 0
```

If-else branch:

```yaml
- data:
    isInIteration: false
    sourceType: if-else
    targetType: llm
  id: edge-if-else-true
  source: '1730000000002'
  sourceHandle: 'true'
  target: '1730000000003'
  targetHandle: target
  type: custom
  zIndex: 0
```
