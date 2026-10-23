## 1. Requirements v2
- [x] 1.1 REQUIREMENTS 加 R16–R18、D1b/D8/D9、已确认表、Q5
- [x] 1.2 `docs/aws_account_hardening.md`
- [x] 1.3 MIT LICENSE，README 更新

## 2. Read-only guard
- [x] 2.1 `hooks/aws_readonly_guard.py`
- [x] 2.2 `.claude/settings.json` 注册 PreToolUse/Bash
- [x] 2.3 单元测试 `hooks/test_aws_readonly_guard.py`（12 allow / 17 block / hook 协议）

## 3. 验收
- [x] 3.1 `python3 -m unittest hooks/test_aws_readonly_guard.py` 全绿
- [x] 3.2 按注册的命令行原样调用 hook：写操作 exit 2，读操作 exit 0
- [x] 3.3 `openspec validate c0001-requirements-v2` 通过
- [x] 3.4 敏感信息扫描为 0
