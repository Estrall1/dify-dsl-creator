# Dify DSL Version Compatibility

Dify evolves its DSL schema. A file that imports into one Dify version may be rejected by another if `version` or node fields do not match.

## 0. 青莲 Dify

青莲 Dify 是 Dify 的发行版/定制平台，版本号与字段可能和上游不同。使用前请先阅读 `qinglian-dify-profile.md`，并以青莲导出的空白应用为版本基准。

已验证的青莲 `advanced-chat` 导出使用 `version: 0.3.1`。青莲 Chatflow 可直接从 `assets/base-qinglian-chatflow.yml` 起稿；该底座已按青莲空白 Chatflow 导出重建，默认模型为 `langgenius/volcengine_maas/volcengine_maas` / `豆包`。

青莲空白 `workflow` 导出同样使用 `version: 0.3.1`、`mode: workflow`，默认只有 `start`、没有 `end`，`dependencies: []`。`assets/base-qinglian-workflow.yml` 已按该导出的根结构和 `features` 校准，并补上 `llm`、`end` 与所需模型依赖。原始空白结构保存在 `assets/qinglian-blank-workflow.yml`。

## 1. Safest Workflow

1. In the target Dify instance, create a blank app in the desired mode.
2. Export it as DSL YAML.
3. Use that export as the base skeleton: copy `version`, `app`, `workflow.features`, and the empty graph wrapper.
4. Add nodes and edges.
5. Run `scripts/validate_dify_dsl.py`.
6. Import the result into the same instance.

This avoids guessing the version.

## 2. Default And Fallbacks

- The bundled templates use `version: 0.3.0`.
- If the target instance rejects `0.3.0`, replace `version` with the exact value from a blank export.
- If you only need basic nodes and the target is older, `0.1.5` is a common compatibility fallback.
- Do not put newer fields into an older version:
  - newer `variable-assigner.items`
  - newer `http-request.retry_config`
  - newer LLM structured-output fields
  - newer iteration/loop child-node layout

## 3. Approximate Version Map

Use this only as a starting hint; the blank export is authoritative.

| Dify era | Common DSL version | Notes |
|---|---|---|
| Dify 0.15.x | `0.1.5` | Basic workflow/Chatflow nodes. |
| Dify 1.0–1.2 | `0.2.x` | Plugin dependencies introduced. |
| Dify 1.3–1.6 | `0.3.x` | Common templates in this skill. |
| Dify 1.7–1.8 | `0.4.x` | Newer node fields; verify against export. |
| Dify 1.9+ | `0.5.x` | Newer iteration/loop/agent schemas; verify against export. |

If the exact version is unknown, ask the user to export a blank app first.

## 4. Version-Related Symptoms

| Symptom | Likely cause | Fix |
|---|---|---|
| `DSL version is not supported` | `version` newer than target | Use target blank export version. |
| Import succeeds but node data is empty | fields from a newer schema | Copy the node from a target export. |
| Variable reference unresolved | selector syntax or output key mismatch | Check `variable-reference-rules.md`. |
| Plugin node missing | `dependencies` entry absent | Copy dependency from a target export. |
| Iteration/loop layout broken | missing child-node wrapper fields | Copy the complete iteration/loop subtree. |

## 5. What Not To Do

- Do not blindly change only the version string while keeping newer fields.
- Do not mix node shapes from different Dify versions in one file.
- Do not invent plugin dependency identifiers.
- Do not claim import success without a test import.
