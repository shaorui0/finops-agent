## Why

发现（findings）只说"哪里在浪费"，不说"怎么安全地处理"。从发现到动手之间缺一层：每个动作的前置检查、撤回成本、回滚办法、该通知谁。FA06 要求每个修复动作标注撤回成本，高撤回成本的动作只给建议。本仓库 AWS 只读，所以这一层只能产出可审阅的 dry-run 计划，不能执行。

## What Changes

- 新增独立模块 `finops_agent/remediate.py`：`findings.json` -> `plans.json`；`apply` 子命令只在 `--approve <plan_id>` 下打印（或写出）供人手动运行的脚本。
- 计划按 docs/METHOD.md 顺序（删 -> 降配 -> 承诺）排列；承诺类计划只有建议，没有命令。
- 本 change 不改 `__main__.py`、报告、Makefile；集成留给后续 change。

## Capabilities

### New Capabilities
- `remediation-plans`：把 finding 变成带撤回成本和回滚的 dry-run 计划，且任何路径都不执行。

### Modified Capabilities
（无）

## Impact

新增文件，不改现有行为。

## 人工 gate 与回滚

- gate：`apply` 无 `--approve` 直接拒绝；有 `--approve` 也只输出脚本文本，脚本由人审阅后自己运行。
- 回滚：每个计划自带 rollback 步骤；本 change 本身只新增文件，回滚即删除这些文件。
