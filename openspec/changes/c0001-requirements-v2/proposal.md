## Why

23:44–23:45 语音回答了 Q1–Q4：接个人 AWS 账号、必须只读、只读要在项目层用 hook 实现。在任何 AWS 调用发生之前，先把这道闸装上。

## What Changes

- REQUIREMENTS 升到 v2：新增 R16（只读 hook + AWS 侧需求）、R17（本地 Grafana + metric 两步法）、R18（主页 FinOps Agent 页）；新增 D1b、D8、D9；Q1–Q4 记为已确认，新增 Q5。
- 新增项目级 PreToolUse hook `hooks/aws_readonly_guard.py`，注册在 `.claude/settings.json`。
- 新增 `docs/aws_account_hardening.md`（只列需求，不改 AWS）。
- 新增 MIT LICENSE。

## Capabilities

### New Capabilities
- `aws-readonly-guard`：agent 通过 Bash 发出的 AWS CLI 只能是读操作。

### Modified Capabilities
（无）

## Impact

只影响本仓库的 Claude Code 会话；不碰任何 AWS 资源。
