## Why

这是一个中文仓库，但 README、testenv 说明和报告界面是英文的，和 `rules/COMMUNICATION.md` 里"README 用英文"的旧规则一致。维护者要求改为中文。

## What Changes

- `rules/COMMUNICATION.md`：语言规则改为"文档和报告界面用中文；代码标识符、代码注释、指标名、告警名、API 字段保持英文"。
- README、`testenv/README.md` 译为中文。
- 报告界面、检测器生成的标题 / 推理跳 / 证据 / 线索、SLO 说明与证据、可见性需求描述译为中文。
- 线索增加结构化字段 `since`（异常起始日），SLO 不再从显示文本里解析日期。

## Capabilities

### New Capabilities
- `language`：仓库的语言约定。

### Modified Capabilities
（无）

## Impact

只改显示文本与一个内部字段；检测逻辑、评估结果不变。
