## Why

R10 要求本项目有自己的 context 层，以 context-infrastructure 的 `rules/` 为母版蒸馏。现在仓库里的 agent 每次会话都是空白的：不知道自己的边界、项目的公理、报告该怎么写。要在 M1 写分析 agent 之前把这一层立起来，后面的每个 change 都在它的约束下做。

## What Changes

- 新增 `rules/`，结构对齐母版：`SOUL.md`、`USER.md`、`COMMUNICATION.md`、`WORKSPACE.md`、`axioms/`、`skills/INDEX.md`。
- `axioms/`：从母版 50 条里选 11 条和本项目相关的，改写成 FinOps 语境，每条写明「在本仓库里怎么落地」；另加 2 条项目原生公理（以终为始、潮汐不是浪费）。
- 新增根目录 `CLAUDE.md` / `AGENTS.md`：每次会话先读 `rules/`。
- 新增 `tools/check_rules.py`：引用完整性 + 公开安全扫描，作为验收和以后 cron（D5）的回归检查。
- 新增 `docs/DISTILLATION.md`：母版 → 项目的映射，以及哪些内容刻意不带进来、为什么。

## Capabilities

### New Capabilities
- `project-rules`：项目级规则层的结构、加载方式与公开安全约束。

### Modified Capabilities
（无）

## Impact

只影响本仓库的 agent 会话行为与文档；不碰 AWS。
