## 1. 规则层
- [x] 1.1 `rules/SOUL.md` `USER.md` `COMMUNICATION.md` `WORKSPACE.md` `skills/INDEX.md`
- [x] 1.2 `rules/axioms/`：11 条蒸馏 + 2 条原生 + INDEX

## 2. 检查工具
- [x] 2.1 `tools/check_rules.py`（结构、引用、公理四段、互相列出、泄漏扫描）
- [x] 2.2 `tools/test_check_rules.py`（每类失败各一个反例）

## 3. 接线与文档
- [x] 3.1 根目录 `CLAUDE.md` / `AGENTS.md`
- [x] 3.2 `docs/DISTILLATION.md`
- [x] 3.3 README 目录表、REQUIREMENTS §5「Context engineering」「记忆」两行更新

## 4. 验收
- [x] 4.1 `python3 tools/check_rules.py` 通过
- [x] 4.2 `python3 -m unittest discover -s tools` 与 hook 单测全绿
- [x] 4.3 `openspec validate c0003-project-rules` 通过
