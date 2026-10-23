# WORKSPACE.md：东西放在哪

找文件前先查这里。

| 内容 | 位置 |
|---|---|
| 规则层（每次会话先读） | `rules/` |
| 项目公理 | `rules/axioms/`（入口 `INDEX.md`） |
| 项目 skill | `.claude/skills/`（入口 `rules/skills/INDEX.md`） |
| 需求、交付物、里程碑 | `docs/REQUIREMENTS.md` |
| AWS 侧加固需求 | `docs/aws_account_hardening.md` |
| 规则层的来源与取舍 | `docs/DISTILLATION.md` |
| 规格与 change 历史 | `openspec/specs/`、`openspec/changes/` |
| 每个 change 的验收证据 | `openspec/changes/<id>/evidence.md` |
| HTML 报告 | `reports/` |
| 博客笔记 | `notes/blog/` |
| 安全护栏（hook） | `hooks/`，注册在 `.claude/settings.json` |
| 仓库自检工具 | `tools/` |
| 合成测试账号与两个测试服务器 | `testenv/`（入口 `testenv/README.md`） |
| 成本优化方法（agent 的作业顺序） | `docs/METHOD.md` |
| 分析流水线代码 | `finops_agent/`（入口 `python3 -m finops_agent run`） |
| 可见性需求（第 ① 环） | `config/visibility_requirements.yaml` |
| 运行产物（不进 git） | `runs/<run_id>/` |

## 命名

- change：`c<NNNN>-<slug>`，四位递增。
- 报告和笔记：`<NNNN>-<slug>.html` / `.md`。
- 文件和目录：小写，单词之间用 `-` 或 `_`，同一目录内保持一致。
