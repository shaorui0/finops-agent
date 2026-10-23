# CLAUDE.md

每次会话开始，做任何事之前，按顺序读：

1. `rules/SOUL.md`：你是谁、边界在哪
2. `rules/USER.md`：你在帮谁、他的偏好
3. `rules/WORKSPACE.md`：东西放在哪
4. `rules/COMMUNICATION.md`：怎么写回复和报告
5. `rules/axioms/INDEX.md`：判断依据
6. `rules/skills/INDEX.md`：可用 skill

然后看 `docs/REQUIREMENTS.md` 确认当前里程碑。

## 硬规则

- 任何改动都走 `finops-change-loop` skill：OpenSpec change，按阶段 commit，验收结果汇报给维护者。
- AWS 只读。`hooks/aws_readonly_guard.py` 拦截写操作，被拦就报告，不绕过。
- 提交前跑 `python3 tools/check_rules.py`。
