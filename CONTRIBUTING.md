# 贡献指南

这个仓库是一个只读的 FinOps 巡检 agent，加一套能离线跑的合成 AWS 账号和打分器。改动前先读 [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md)（模块地图和产物契约）和 [`docs/METHOD.md`](docs/METHOD.md)（M0 到 M6 的方法）。

## 搭环境

- Python 3.12（CI 用的版本，见 [`.github/workflows/ci.yml`](.github/workflows/ci.yml)）。更高的 3.x 也能跑。
- `pip install -r requirements.txt`，依赖只有 `boto3` 和 `PyYAML`。
- `make alerts-test` 需要 docker（用 Prometheus 官方镜像里的 promtool）。其余目标不需要网络和 AWS 凭据。
- 不需要任何真实 AWS 账号。开发和评估都对着 `testenv/` 里的合成账号。

## 跑测试

| 命令 | 做什么 |
|---|---|
| `make test` | 全部单测和端到端测试：护栏 hook、`tools/`、`testenv`、`finops_agent`、`eval` |
| `make check` | 规则层完整性 + 泄漏扫描（`tools/check_rules.py`），提交前必跑 |
| `make eval` | 起两个测试服务，跑一遍 agent，用 `eval/score.py` 对照标准答案打分，结束后关服务。陷阱或不变量违反、指标低于基线时退出码为 1 |
| `make alerts-test` | 用 promtool 校验并单测 `config/alerts/` 下的告警规则 |
| `make demo` | 只起服务并跑一遍，产物在 `runs/local/`，不打分 |

端口冲突时用 `AWS_PORT`、`PROM_PORT`、`RUN` 覆盖，例如 `make eval AWS_PORT=14566 PROM_PORT=19090 RUN=ci`。`runs/` 已被 `.gitignore` 忽略。

## 改动闭环

每个改动是一个 OpenSpec change，按阶段提交。完整规则在 [`.claude/skills/finops-change-loop/SKILL.md`](.claude/skills/finops-change-loop/SKILL.md)，摘要如下。

1. 开 change：`openspec new change c<NNNN>-<slug>`。编号四位递增，取 `reports/` 里最大号加一。在 `openspec/changes/<id>/` 下写 proposal、specs、tasks，tasks 里必须有一条「验收」，写明用什么命令证明做完。
2. 实现：只改 tasks 里列出的东西。
3. 验收：跑验收命令，输出原样存进 `openspec/changes/<id>/evidence.md`。失败就回到实现。
4. HTML 报告：`reports/<NNNN-slug>.html`，内容是改了什么、为什么、验收证据、前后对比。可以先写 md，再用 `pandoc -s --metadata title=<slug> in.md -o reports/<NNNN-slug>.html` 生成。
5. 笔记：`notes/blog/<NNNN-slug>.md`，只记核心想法、踩的坑、反直觉的结论，bullet 即可，不润色。
6. 按阶段提交，每次只 `git add` 该阶段的文件。首行格式 `c<NNNN>-<slug> [k/n <阶段>]: <一句话>`，阶段依次是 `proposal`、`spec+tasks`、`impl`（可拆多个，每个能独立通过单测）、`docs`、`acceptance`。`acceptance` 提交包含 evidence、报告、笔记，并在 README 的 Progress 表追加一行。
7. 把验收结果（通过或失败、关键输出、报告路径）汇报给维护者。没汇报不算做完。
8. 完成后 `openspec archive <id>`。

## 硬规则

- **AWS 只读。** `hooks/aws_readonly_guard.py` 在 Bash 层拦写操作，被拦就报告，不绕过。涉及 AWS 写操作的 change，proposal 里要写明人工 gate 和回滚。IAM 侧的加固见 [`docs/aws_account_hardening.md`](docs/aws_account_hardening.md)。
- **不带雇主数据和私有数据。** 账单、账号号、资源 ID、内部代码都不进仓库。合成账号的账号号用全同数字占位（如 `000000000000`），资源 ID 都是虚构的。提交前跑 `git diff --cached` 看一遍。
- **泄漏扫描。** `make check` 会扫全仓库的 12 位账号号、`AKIA` 密钥、本机 home 路径。私有词表放在 `.leak_patterns.local`（每行一个正则，已被 gitignore），这样仓库里不出现要防的词。
- **数字来自代码，不来自 LLM。** 金额、比例、天数由确定性代码从快照里算出。判断层可以解释和排序，不能产生数字。报告里的每个数字要能指回 evidence 或数据行。
- **不针对标准答案写死 ID。** 检测器不得出现 `testenv/world.yaml` 里的资源 ID，也不得按陷阱资源做特判。陷阱靠检测逻辑本身绕开（比如 AMI 被启动模板引用就不算孤儿），不靠名单。
- **每条发现带证据，金额标口径。** `basis` 取 `billed`、`billed_14d_extrapolated`、`list_price`、`inferred`、`none` 之一。

## 语言规则

遵循 [`rules/COMMUNICATION.md`](rules/COMMUNICATION.md)：

- 文档、OpenSpec、博客笔记、报告界面用中文。
- 代码标识符、代码注释、指标名、告警名、API 字段保持英文，它们是协议的一部分。
- 不用破折号造插入句，尽量用正向陈述。
- 逻辑不依赖显示文本：后续阶段要用的值放结构化字段（如线索的 `since`），不从人读的字符串里解析。

## 加一个检测器

检测器是 `finops_agent/analyze.py` 里 `Analyzer` 的一个方法，对冻结的快照做算术和关联，返回带证据的 `Finding`。

1. 在 `Analyzer` 里加方法，并把它加进 `run()` 的方法元组。
2. 选 `method_step`，取值是 `M1_visibility_attribution`、`M2_ranking`、`M3_delete`、`M4_downsize_schedule`、`M5_commitment`、`M6_architecture` 之一，含义见 [`docs/METHOD.md`](docs/METHOD.md)。报告按这个字段分组，写错会让发现落到不存在的小节。
3. 每个 `Finding` 填齐：`type`（稳定的小写下划线名，跨运行 diff 靠它）、`title`、`resources`、`hops`（推理跳，一跳一句）、`evidence`（`Evidence(source, what, ref)`，`ref` 写产生它的 API 调用）、`monthly_savings_usd`、`basis`、`resource_spend_usd`、`detector`（方法名）。
4. 守住不变量，`check_invariants` 会检查：节省不超过资源花费，节省大于 0 时 `basis` 不能是 `none`，证据不能为空。
5. 需要跨数据源判断才能成立的信号，不要硬判成 Finding，发成 `Lead`（带 `questions`，有起始日就填 `since`），交给判断层。
6. 需要新的 AWS 或 Prometheus 数据时，改 `finops_agent/collect.py` 的 `snapshot()`，只用只读 API（`describe_*`、`get_*`、`list_*`）。`test_trace_is_read_only` 会拦写操作。
7. 测试：在 `finops_agent/test_pipeline.py` 加断言（类型存在、资源在内、金额在范围内、陷阱资源不在被标记集合里），再跑 `make test`。
8. 评估：见下一节。检测器的新发现要能在 `ground_truth` 里找到对应项，否则会拉低 precision。

## 加一个测试场景和标准答案

合成账号的全部事实在 `testenv/world.yaml`，两个测试服务和打分器都从它推导，agent 不读它。

1. 在 `testenv/world.yaml` 里加资源、用量或指标 profile（profile 的形状函数在 `testenv/world.py` 的 `cpu` 等处）。
2. 在 `testenv/world.yaml` 的 `ground_truth.findings` 加一项：`id`（`GT` 加两位序号）、`method_step`、`type`、`title`、`resources`、`hops`、`evidence_sources`、`monthly_savings_usd`（`min` 和 `max` 区间）。区间要和成本模型一致，`testenv/test_testenv.py` 的 `test_savings_ranges` 会校验。
3. 陷阱写进 `ground_truth.traps`：`id`、`resources`、`must_not`（如 `rightsize`、`idle`、`delete_snapshots`）、`why`。`must_not: skip` 表示该资源必须被分析，用于 prompt 注入这类场景。
4. 可见性缺口写进 `ground_truth.visibility_gaps`。
5. 对应更新 `testenv/test_testenv.py`、`finops_agent/test_pipeline.py`（场景存在、被发现或被正确放过）。
6. 跑 `make eval`，看新场景在 `runs/<id>/eval.json` 的 `matched` 和 `missed` 里的位置。

## eval 基线怎么卡 CI

`eval/score.py` 对一次运行的 `findings.json` 打分，指标有 `recall`、`savings_recall`、`precision`、`savings_accuracy`、`step_agreement`、`depth`。CI 里 `make eval` 触发以下闸门，任一失败退出码为 1：

- 任何陷阱违反（碰了陷阱资源，或该分析的资源没被标记）。
- 任何不变量违反。
- `recall` 或 `savings_recall` 低于 `eval/baseline.json`。

只有这两个指标和基线比较，其余指标只展示。基线只应上调：改进后用 `python3 -m eval.score runs/<id>/findings.json --write-baseline` 更新，并把新旧数字写进该 change 的 evidence 和报告。不能为了让 CI 变绿而调低基线。

## 提交前清单

- [ ] `make check` 和 `make test` 全绿
- [ ] 动了检测逻辑或测试账号：`make eval` 通过，指标对比写进 evidence
- [ ] 动了告警规则：`make alerts-test` 通过
- [ ] `git diff --cached` 没有账号号、密钥、本机路径、雇主数据
- [ ] evidence、HTML 报告、笔记、README Progress 行齐全
