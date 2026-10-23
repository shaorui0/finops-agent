## Why

`rules/` 是从私有母版蒸馏来的（见 `docs/DISTILLATION.md`）。母版会继续演化，本仓库原生的公理（FA12、FA13）也该回流。现在没有机制发现差异，只能靠人记。

## What Changes

- 新增 `tools/sync_rules.py`：对比母版 `axioms/` 与本仓库，生成中文提议 markdown，只读、不自动应用。
- 新增 `tools/rules_sync_manifest.json`：蒸馏时母版公理文件的文件名 + sha256（不含内容），用来判断"蒸馏后是否变更"。
- 提议分三类：母版已变更且已映射（建议更新）、母版新增未映射（候选，需人工决定）、项目原生（建议回提母版）。
- 母版内容命中泄漏模式（公开模式 + `.leak_patterns.local`）时只标记，不输出任何原文。

## Capabilities

### New Capabilities
- `rules-sync`：母版与蒸馏规则的单向对比与人工审阅提议。

### Modified Capabilities
（无）

## Impact

只新增工具、测试、清单；不写 `rules/`，不写母版。人工 gate：提议由维护者审阅后自己改 `rules/`，工具不提供应用入口。回滚：删除这几个新文件即可。
