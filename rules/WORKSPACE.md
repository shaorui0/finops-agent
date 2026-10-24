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
| 评估打分与基线 | `eval/`（`make eval`） |
| FinOps SLO 定义与告警规则 | `config/finops_slo.yaml`、`config/alerts/`（`make alerts-test`），说明见 `docs/FINOPS_SLO.md` |
| 巡检节奏（cron 示例） | `ops/crontab.example`（`make inspect`） |
| 跨运行状态（运行时生成，不进 git） | runs 目录下的 state.json |
| 判断层（LLM 回答线索） | `finops_agent/judge/`（取证、prompt、校验），模型出口 `finops_agent/llm.py` |
| LLM 录制回放 cassette | `eval/cassettes/`（只增不改，模式由环境变量 `FINOPS_LLM_MODE` 选） |
| 修复计划、五段式、预防控制 | `finops_agent/remediate.py`、`finops_agent/fivepart.py`、`finops_agent/prevention.py` |
| 省钱核实 | `finops_agent/verify_savings.py`、`scripts/verify_savings.sh`，生成 `docs/SAVINGS_VERIFICATION.md` |
| LLM 推导可见性第 ① 环 | `finops_agent/visibility_llm.py`、`config/cost_goals.yaml`、`eval/score_visibility.py` |
| 场景覆盖层（下个月、核实链、对抗变体） | `testenv/scenarios/` |
| 预注册的全新样本外世界 | `testenv/heldout/`（先提交后评估，一次） |
| 样本内、样本外、预注册评估 | `eval/heldout.py`，实验记录 `eval/EXPERIMENTS.md` |
| 对抗测试 | `eval/test_adversarial.py` |
| 测试账号目录页（五段式） | `testenv/catalog.py`，生成 `reports/testenv-catalog.html` |
| 架构图等六张图（mermaid 源 + SVG） | `docs/diagrams/`（说明与重新渲染见 `docs/diagrams/README.md`） |
| 导读页（生成，不手改） | `tools/build_index.py`，生成 `reports/index.html` |
| 规则同步工具（只出提议） | `tools/sync_rules.py` |
| 演示与核实脚本 | `scripts/`（`rot_demo.sh`、`verify_savings.sh`） |
| 面向读者的总览文档 | `docs/NARRATIVE.md`（这个项目证明了什么）、`docs/MATURITY.md`（完成标准）、`docs/BUILD_PROCESS.md`（构建过程）、`docs/ARCHITECTURE.md` |
| 贡献指南 | `CONTRIBUTING.md` |
| CI | `.github/workflows/ci.yml` |

## 命名

- change：`c<NNNN>-<slug>`，四位递增。
- 报告和笔记：`<NNNN>-<slug>.html` / `.md`。
- 文件和目录：小写，单词之间用 `-` 或 `_`，同一目录内保持一致。
