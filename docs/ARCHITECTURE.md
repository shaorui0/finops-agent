# 架构

这份文档回答三个问题：模块怎么分层、每个目录负责什么、一次运行产出的文件长什么样。读者导览见 [`NARRATIVE.md`](NARRATIVE.md)（这个项目证明了什么）和 [`../reports/index.html`](../reports/index.html)（图、表、全部改动）。方法论见 [`METHOD.md`](METHOD.md)，SLO 的设计动机见 [`FINOPS_SLO.md`](FINOPS_SLO.md)，改动流程见 [`../CONTRIBUTING.md`](../CONTRIBUTING.md)。

## 全景

![架构：模块与分层](diagrams/architecture.svg)

上图画的是 main 上已有的模块，不画计划中的东西。从左到右：采集只读地拿到外部世界，冻结成快照；确定性检测器产出发现和线索；判断层（LLM，默认回放录制）回答线索；不变量拦下不可能成立的答案；五段式、处置计划、SLO 和报告是给人看的输出。评估和测试环境在外圈，三层只读护栏（hook、服务端拒绝写、AWS 侧 IAM）包住采集。

## 数据流

![数据流：产物谁写谁读](diagrams/dataflow.svg)

```
AWS API / Prometheus ──collect──> snapshot.json ──┬─ visibility ──> visibility.json
   （只读，经 Trace 留痕）          （冻结，分析只读它）  ├─ analyze ────> findings + leads ──judge──> 判断后的 findings
                                                    ├─ remediate ──> plans.json（dry-run）
                                                    ├─ fivepart ───> fivepart.json
                                                    └─ slo ────────> slo.json, finops_metrics.prom
                                                                      │
                          runs/state.json <── 跨运行状态 ─────────────┤
                                                                      └─ report.html, trace.jsonl
```

五条设计约束贯穿全流程：

- 采集和分析分开。`collect` 把外部世界冻结成 `snapshot.json`，`analyze` 只读快照，所以任何一次运行都能用 `--snapshot` 重放。
- 数字由确定性代码产生。检测器只做算术和关联，需要跨源判断的信号以 `Lead` 的形式交出去。判断层的取证器（`finops_agent/judge/gather.py`）同样由代码算出候选金额，模型只选，不算。
- 所有外部调用都进 `trace.jsonl`，可审计，也是「只读」的证据。LLM 调用也在里面，带 tokens、延迟、成本、模式（replay 或 record）、判断结论和是否被接受。
- 模型的输出不被信任。`finops_agent/judge/validate.py` 要求严格 JSON、数字取自证据、资源在允许范围内；叙述里未落地的数字按从句脱敏并留痕（c0022），结构化字段不落地则整条拒绝。
- 写操作做不到。处置计划只是数据，`remediate.py` 不 import 任何能起进程的东西，承诺折扣只给建议不给命令。

## 判断层与 LLM 调用

一条线索对应一次独立的 LLM 调用（FA11 上下文隔离），流程是：

```
lead ──gather（代码取证并算出候选金额）──> prompt（只含这条线索）──> llm.py（replay / record / live）
     ──> validate（严格 JSON、数字落地、资源白名单）──> Finding（金额来自所选候选，不来自模型的文字）
```

- `finops_agent/llm.py` 是唯一的模型出口。`FINOPS_LLM_MODE` 取 `replay`（默认）、`record`、`live`。回放读 `eval/cassettes/<sha256(模型 + prompt)>.json`，没有对应 cassette 就报 `CassetteMissing`；录制调用 `claude -p` 并把整条响应（文本、用量、成本、耗时）存成 cassette。所以 CI 不需要 API key，结果确定，改 prompt 会使对应 cassette 失效。
- `finops_agent/judge/` 的分工：`gather.py` 取证并算数（也含 idle_window 线索的确定性生成器），`brief.py` 定义模型可见的全部材料，`prompt.py` 拼出只含该线索的 prompt，`validate.py` 校验回复。`finops_agent/judge/__init__.py` 串起来并把每次判断（结论、是否接受、拒绝原因、脱敏记录）写进 `findings.json` 的 `judgments` 和 `trace.jsonl`。
- 判断的结论有 `waste`、`not_waste`、`insufficient_evidence`。`not_waste` 和 `insufficient_evidence` 不产生 finding。
- `--no-judge`（或 `FINOPS_NO_JUDGE=1`）只跑确定性层，`make rot-demo` 用它。

## 发现之后

- `finops_agent/remediate.py`：每个有节省的 finding 生成一份 dry-run 计划（命令文本、前置检查、撤回成本、回滚、owner、证据）。顺序是先删、再降配、最后承诺。`apply` 子命令没有 `--approve` 不执行，且只打印或写脚本给人读。
- `finops_agent/fivepart.py`：每个 finding 一份五段式，现状、期望、差异、处置、预防，字段名与 `testenv/world.yaml` 的 `ground_truth` 一致，所以报告里的卡片读起来和标准答案一个样。status、spec、diff 由代码按 finding 类型与证据算出，LLM 文字不进数字。
- `finops_agent/prevention.py`：finding 类型到预防控制（生命周期策略、tag 策略、AWS Config 规则、模板改动）和对应告警规则名的映射，测试断言这些规则存在于 `config/alerts/finops.rules.yml`。
- `finops_agent/verify_savings.py`：省钱核实。对场景链里每条 `resolved` 的 finding，用 Cost Explorer 的前后两期数据算反事实基线、分层对照组和精确的账单分解，比较预测与实际；它自己起停测试服务。输出是 `docs/SAVINGS_VERIFICATION.md` 和 `reports/savings-verification.html`，两者都由代码生成，不手写。入口 `scripts/verify_savings.sh`。

## 可见性与 SLO 的细节

- 可见性链第 ② 环（`visibility.ring2`）不再信任第 ① 环的正则：`visibility.discover` 按信号的语义（`concept`、`terms`）在指标服务的 HELP、名字和 scope 里确定性地发现候选名字（c0020）。第 ④ 环按 need 级判定，可以给出 `covered`、`partial`、`missing` 的混合状态。
- 第 ① 环可以由 LLM 从成本目标推导：`finops_agent/visibility_llm.py` 读 `config/cost_goals.yaml`，只用文字描述需要的信号，不猜指标名；`eval/score_visibility.py` 对照人审版打分，`--samples N` 给出 N 次采样的均值、最小值、最大值。
- 腐烂状态（`finops_agent/slo.py` 的 `diff_state`）共五种：`new`、`persisting`、`resolved`、`regressed`、`not_redetected`。一条 finding 消失时，只有资源清单或近 14 天资源成本显示资源变了才算 `resolved`；资源还在、属性和成本都没变，记 `not_redetected`，这是漏检，不是修复（c0023）。语义和告警见 [`FINOPS_SLO.md`](FINOPS_SLO.md)。

![腐烂生命周期](diagrams/rot-lifecycle.svg)

## 模块地图

### `finops_agent/`：agent 本体

入口 `python3 -m finops_agent run`，参数见 `finops_agent/__main__.py`。

| 模块 | 输入 | 输出 | 说明 |
|---|---|---|---|
| `finops_agent/__main__.py` | 命令行参数 | `runs/<id>/` 下的全部产物 | 编排：collect、visibility 四环、analyze、slo、report。`--snapshot` 跳过采集，`--no-state` 不更新跨运行状态 |
| `finops_agent/collect.py` | `Config`（端点、区间） | `snapshot.json` 的内容、`Trace` | `Collector.aws()` 和 `Collector.prom()` 是仅有的两个外部出口，每次调用记入 `Trace`。`--aws-endpoint` 指向测试服务，省略则用真实 AWS 的环境凭据 |
| `finops_agent/analyze.py` | 快照、天数 | `Finding` 列表、`Lead` 列表、`ranking`、`attribution_summary` | 每个检测器是 `Analyzer` 的一个方法。`check_invariants` 检查节省不超过资源花费、金额有口径、证据非空 |
| `finops_agent/visibility.py` | `config/visibility_requirements.yaml`、快照、`Collector` | `visibility.json` 的四个段 | 四环：`ring1` 需求，`ring2` 计划（`discover` 按语义发现指标名），`ring3` 搜索（只查 Prometheus 的 series 接口），`ring4` 缺口（need 级混合状态） |
| `finops_agent/slo.py` | 结果、快照、`Collector`、上次状态、`config/finops_slo.yaml` | SLI 值、`slo.json`、`finops_metrics.prom`、新状态 | `compute_slis` 算值，`evaluate` 对目标，`diff_state` 标注 new、persisting、resolved、regressed、not_redetected，`to_prometheus` 导出 |
| `finops_agent/llm.py` | 模型、prompt、`FINOPS_LLM_MODE` | `LLMResult`（文本、tokens、成本、耗时） | record/replay/live 三种模式，cassette 键是 sha256(模型 + prompt) |
| `finops_agent/judge/` | `Lead`、快照、`Collector` | `Finding`、`judgments`、trace 里的 llm 记录 | 判断层：gather、brief、prompt、validate，见上文 |
| `finops_agent/visibility_llm.py` | `config/cost_goals.yaml` | 推导出的第 ① 环（yaml） | 只写词不写名，名字由第 ② 环发现 |
| `finops_agent/remediate.py` | `findings.json`、可选 owner 映射 | `plans.json` | dry-run 计划，`apply` 无 `--approve` 不执行 |
| `finops_agent/fivepart.py` | finding、计划、SLO 配置 | `fivepart.json` | 五段式，数字由代码算 |
| `finops_agent/prevention.py` | finding 类型 | 预防控制与告警规则名 | 测试断言规则存在 |
| `finops_agent/verify_savings.py` | 场景链的多期 Cost Explorer 数据 | `docs/SAVINGS_VERIFICATION.md`、`reports/savings-verification.html` | 反事实基线、对照组、账单分解，自带服务起停 |
| `finops_agent/report.py` | 一次运行的结果 dict | `report.html`（单文件，无外链） | 按 M0 到 M6 组织，另有 SLO 表、可见性链表、Agent 成本、五段式卡片、运行留痕 |
| `finops_agent/test_*.py` | 各自的夹具 | 断言 | `test_pipeline` 端到端一次完整运行；`test_slo` 发现生命周期与指标导出；`test_llm`、`test_judge`、`test_judge_grounding` 判断层与数字落地；`test_remediate`、`test_fivepart`、`test_analyze`、`test_visibility`、`test_visibility_llm`、`test_verify_savings` 各管一块 |

### `testenv/`：合成账号

详见 [`../testenv/README.md`](../testenv/README.md)。agent 只通过网络协议访问它，从不 import。

| 模块 | 输入 | 输出 | 说明 |
|---|---|---|---|
| `testenv/world.yaml` | 手写 | 账号事实 + `ground_truth` | 资源、价格、用量、标准答案（`findings`、`traps`、`visibility_gaps`） |
| `testenv/world.py` | `testenv/world.yaml` | 逐日成本行 `CostLine`、指标形状函数 | 两个服务和测试共用的推导层 |
| `testenv/aws_server.py` | HTTP 请求 | EC2、Auto Scaling、STS、Cost Explorer、Resource Groups Tagging、Savings Plans 响应 | 真实线上协议，由 botocore 的服务模型序列化。写操作返回 `UnauthorizedOperation`。`--log` 记录每次调用 |
| `testenv/metrics_server.py` | HTTP 请求 | Prometheus HTTP API 响应 | 支持 `query`、`query_range`、`series`、`labels`、`label/<name>/values`、`metadata` 和健康检查，PromQL 子集见文件头注释 |
| `testenv/scenarios/` | 覆盖层 yaml | 另一个月份或另一种扰动的世界 | `next_month`、`month_after`（腐烂演示）、`verify_*`（省钱核实场景链）、`adversarial_*`（12 个注入变体） |
| `testenv/heldout/fresh_world.yaml` | 手写 | 预注册的全新世界（c0024） | 标准答案先提交、之后只评估一次 |
| `testenv/catalog.py` | `testenv/world.yaml`、场景 | `reports/testenv-catalog.html` | 把标准答案的五段式渲染成可读页面，数字用占位符对着成本模型算 |
| `testenv/test_testenv.py`、`testenv/test_catalog.py` | 无 | 断言 | 校验节省区间与成本模型一致、陷阱形状、写操作被拒、目录页不含字面量金额 |

### `eval/`：打分与回归基线

| 模块 | 输入 | 输出 | 说明 |
|---|---|---|---|
| `eval/score.py` | `findings.json`、`testenv/world.yaml` 的 `ground_truth`、`eval/baseline.json` | 同目录 `eval.json`、标准输出摘要、退出码 | 指标和闸门见 [`../CONTRIBUTING.md`](../CONTRIBUTING.md) 的 eval 一节。匹配规则：类型相同，或资源有交集且 `method_step` 相同 |
| `eval/baseline.json` | `--write-baseline` | `recall`、`savings_recall` 等基线值 | CI 用它卡回归 |
| `eval/heldout.py` | 世界名（base、next_month、month_after、fresh_world） | 各世界的全部指标 | 样本内、样本外（已污染）、预注册分开报；回放，约 10 秒 |
| `eval/score_visibility.py` | 推导的第 ① 环、人审版 | overlap、precision | `--samples N` 报均值与区间 |
| `eval/cassettes/` | `llm.py` 的 record 模式 | 每条判断一个 json | 只增不改，键是 sha256(模型 + prompt) |
| `eval/test_adversarial.py`、`eval/test_heldout.py` | 场景覆盖层 | 断言 | 12 个对抗变体的发现集不变；各世界数字被钉住 |
| `eval/EXPERIMENTS.md` | | | 实验记录：样本内、样本外、对抗、预注册 |
| `eval/test_score.py` | 无 | 断言 | 陷阱、注入目标、回归、金额区间、不变量各一条 |

### `config/`：声明式配置

| 文件 | 谁读 | 内容 |
|---|---|---|
| `config/visibility_requirements.yaml` | `visibility.ring1` | 每个 SLI 保护的决策，以及需要的信号（`signal`、`name` 正则、`scope`）。`scope` 取 `running_instances`、`nat_gateways`、`services:<a,b>` |
| `config/finops_slo.yaml` | `slo.evaluate` | 每个 SLO 的 `id`、`unit`、`what`、`op`、`target`、`cadence`，可选 `budget` |
| `config/alerts/finops.rules.yml` | Prometheus | 告警规则，消费 `finops_metrics.prom` 导出的指标 |
| `config/alerts/finops.rules.test.yml` | promtool（`make alerts-test`） | 告警规则的单元测试 |

### `hooks/`：护栏

| 文件 | 说明 |
|---|---|
| `hooks/aws_readonly_guard.py` | Claude Code 的 PreToolUse hook，注册在 `.claude/settings.json`。只放行只读 AWS CLI 调用，无法解析时拒绝（fail closed）。退出码 0 放行，2 拦截。只看 Bash 命令，SDK 调用和人工操作由 AWS 侧 IAM 兜底（[`aws_account_hardening.md`](aws_account_hardening.md)） |
| `hooks/test_aws_readonly_guard.py` | 对应单测 |

### `tools/`：仓库自检

| 文件 | 说明 |
|---|---|
| `tools/check_rules.py` | `make check` 的实现：必需规则文件存在，`CLAUDE.md`、`AGENTS.md`、`rules/WORKSPACE.md` 里的反引号路径存在，公理文件四个必需小节齐全且与索引互相列出，全仓库泄漏扫描 |
| `tools/test_check_rules.py` | 对应单测 |
| `tools/build_index.py` | 生成 `reports/index.html`：自包含导读页，内嵌图，列出全部改动与指标；`tools/test_build_index.py` 守住链接和新鲜度 |
| `tools/sync_rules.py` | 对比母版与蒸馏出的公理，只出中文提议，不落盘 |

## 运行产物契约

一次运行写入 `runs/<run_id>/`（`--out` 可改根目录，`--run-id` 默认取 UTC 时间戳）。下面的字段清单由代码和一次真实运行（run id `t6`，对着合成账号）核对得出。所有 JSON 用 `ensure_ascii=False`、缩进 2 空格写出。

### `snapshot.json`

采集阶段冻结的外部世界，是分析阶段的唯一输入。除标注外，值是 boto3 响应里对应列表的原样内容（已去掉 `ResponseMetadata`）。

| 字段 | 来源调用 |
|---|---|
| `period`、`resource_period` | `{Start, End}`。`resource_period` 是分析区间的最后 14 天，供按资源计费查询使用 |
| `identity` | `sts get_caller_identity` |
| `instances` | `ec2 describe_instances`（展平 Reservations） |
| `volumes`、`snapshots`（`OwnerIds=["self"]`）、`images`（`Owners=["self"]`）、`addresses`、`nat_gateways`、`vpc_endpoints` | `ec2 describe_*` |
| `launch_templates` | `ec2 describe_launch_template_versions`，对每个模板各取一次 |
| `asgs` | `autoscaling describe_auto_scaling_groups` |
| `savings_plans` | `savingsplans describe_savings_plans` |
| `cost_by_service`、`cost_by_usage_type`、`cost_by_owner` | `ce get_cost_and_usage`，MONTHLY，指标 `UnblendedCost`、`AmortizedCost`、`UsageQuantity` |
| `cost_daily_by_usage_type` | `ce get_cost_and_usage`，DAILY，按 `USAGE_TYPE` |
| `cost_by_resource_14d` | `ce get_cost_and_usage_with_resources`，过滤 EC2 和 VPC 相关服务，按 `RESOURCE_ID` |
| `sp_utilization` | `ce get_savings_plans_utilization`，从分析起点前推 92 天 |
| `metric_names`、`metric_metadata` | Prometheus 的 label 值接口（`__name__`）与 metadata 接口 |

### `findings.json`

主结果。顶层字段：

| 字段 | 类型 | 含义 |
|---|---|---|
| `run_id`、`account` | string | 运行标识、`identity.Account` |
| `period` | `{Start, End}` | 分析区间 |
| `findings` | list | 见下表 |
| `leads` | list | 见下表 |
| `ranking` | object | `total`（amortized 总花费）、`by_service`（`[服务, 金额]` 降序）、`top_usage_types`（前 10）、`surprises`（意外大项的文字说明） |
| `attribution` | object | `untagged_usd`、`total_usd`、`untagged_share`、`instances_without_owner` |
| `invariants` | list of string | 不变量违反，空列表表示通过 |
| `visibility` | `{gaps}` | 同 `visibility.json` 的 `gaps` |
| `judgments` | list | 判断层每次判断：`lead`、`kind`、`verdict`、`accepted`、`reject_reason`、`finding`、`reasoning`、`redactions` 等 |
| `slo` | object | 同 `slo.json` |

`findings[]`（`Finding`）：

| 字段 | 含义 |
|---|---|
| `id` | 运行内序号，如 `F01` |
| `type` | 稳定类型名，跨运行 diff 和 eval 匹配都靠它 |
| `method_step` | `M1_visibility_attribution`、`M2_ranking`、`M3_delete`、`M4_downsize_schedule`、`M5_commitment`、`M6_architecture` 之一 |
| `title`、`hops` | 中文标题；推理跳列表 |
| `resources` | 涉及的资源 ID 列表 |
| `evidence` | `[{source, what, ref}]`，`source` 取 `cost_explorer`、`ec2`、`metrics`、`savingsplans`，`ref` 是产生它的调用 |
| `monthly_savings_usd` | 月节省金额，由代码算出 |
| `basis` | 金额口径：`billed`、`billed_14d_extrapolated`、`list_price`、`inferred`、`none` |
| `resource_spend_usd` | 资源本身的花费，用于不变量检查，可为 `null` |
| `detector` | 产出它的 `Analyzer` 方法名 |

`leads[]`（`Lead`）：`id`（如 `L01`）、`signal`、`method_step`、`evidence`（同上）、`questions`（待判断的问题列表）、`since`（异常起始日，无则为 `null`）。

### `plans.json`

`run_id`、`dry_run`（恒为 true）、`executed`（恒为 false）、`order`（delete -> downsize -> commit）、`plans`、`skipped`。`plans[]` 的字段：`plan_id`、`finding_id`、`type`、`method_step`、`order`、`title`、`resources`、`monthly_savings_usd`、`basis`、`mode`、`reversal_cost`、`reversal_reason`、`preconditions`、`steps`、`rollback`、`owner`、`evidence`、`advice`、`executable`。

### `fivepart.json`

每个 finding 一项：`finding_id`、`type`、`owner`、`status`、`spec`、`diff`、`runbook`（列表）、`plan_id`、`prevention`、`prevention_alerts`。

### `visibility.json`

可见性链四环，各占一个顶层字段：

| 字段 | 内容 |
|---|---|
| `requirements` | ① 需求，即 `config/visibility_requirements.yaml` 的 `slis` |
| `plan` | ② 计划，每个信号一项：`id`（`<sli>#<序号>`）、`sli`、`signal`、`source`、`query`（`path`、`match[]`）、`found_if`、`scope_label`、`expected`（应被覆盖的取值） |
| `search` | ③ 搜索，对应每项计划：`id`、`metric_names`、`series_count`、`covered`、`query` |
| `gaps` | ④ 缺口，每个 SLI 一项：`sli`、`decision`、`status`（`covered`、`partial`、`missing`），`needs[]`（`signal`、`status`、`metrics`、`covered`、`expected`、`missing_scope`、`query`） |

### `slo.json`

| 字段 | 含义 |
|---|---|
| `rows` | 每个 SLO 一行：`id`、`what`、`unit`、`op`、`target`、`value`、`status`（`ok`、`violated`、`no_data`）、`cadence`、`evidence`。带 `budget` 的行另有 `budget_usd`、`budget_used` |
| `diff` | 与上次状态比较：`new`、`persisting`、`resolved`、`regressed`、`not_redetected` 五个列表，元素含 `key`，`persisting` 带 `since`，`regressed` 带 `resolved_in`，`not_redetected` 带 `since` 与 `why` |
| `previous_runs` | 状态里记录的此前运行数 |

`value` 为 `null` 时 `status` 是 `no_data`，例如首次运行没有跨运行状态，`remediation_age_days` 就没有值。发现的 key 是 `<type>|<按字典序排序的资源 ID，逗号连接>`。

### `finops_metrics.prom`

Prometheus 文本格式，给 node_exporter 的 textfile collector 或 pushgateway 用。

| 指标 | 标签 | 含义 |
|---|---|---|
| `finops_last_run_timestamp_seconds` | 无 | 本次运行结束时间 |
| `finops_sli` | `sli`、`run` | 各 SLI 的值，`no_data` 的不导出 |
| `finops_slo_target` | `sli`、`op` | 各 SLO 目标 |
| `finops_findings` | `state` | 各生命周期状态的发现数（new、persisting、resolved、regressed、not_redetected） |
| `finops_waste_budget_usd`、`finops_waste_budget_used`、`finops_waste_usd` | 无 | 月浪费预算、已用比例、未处理浪费金额（有 `budget` 的 SLO 存在时导出） |

告警规则消费这些指标，见 `config/alerts/finops.rules.yml`。

### `trace.jsonl`

每行一次外部调用：`source`（`aws:<service>`、`prometheus` 或 `llm`）、`op`（boto3 方法名或 Prometheus 路径）、`params`、`ms`、`ok`、`error`。`source` 为 `llm` 的行另有 `mode`、`tokens_in`、`tokens_out`、`latency_ms`、`cost_usd`、`key`、`verdict`、`accepted`、`reject_reason`。`findings.json` 不含 trace，`report.html` 的运行留痕按 `source op` 聚合计数，「Agent 成本」一节汇总 llm 行。

### `report.html`

自包含的单文件中文报告，无外部资源，支持深浅色。分区依次为：KPI 卡片、FinOps SLO 表、不变量违反（如有）、M0 到 M6 各步（发现卡片带五段式，和线索卡片）、可见性链表、Agent 成本、运行留痕。

### `runs/state.json`

跨运行状态，位置由 `--state` 决定（默认 `runs/state.json`，不在单次运行目录里），`--no-state` 时不写。字段：

| 字段 | 含义 |
|---|---|
| `runs` | 已记录的 run id 列表，按时间追加 |
| `open` | 上次运行仍未关闭的发现 key（排序） |
| `first_seen` | key 到首次出现日期（`--end` 的日期）的映射，用于 `remediation_age_days` |
| `resolved` | key 到「在哪次运行被判定为已解决」的映射。已解决的发现再次出现，就记为 `regressed` |
| `not_redetected` | key 到「从哪次运行起没被检出」的映射。资源还在、属性和成本没变，所以不算 resolved；再次检出时回到 persisting |
| `evidence` | key 到检出时的资源指纹，用于区分 resolved 与 not_redetected |

## 如何自己跑一遍

```bash
python3 -m testenv.aws_server --port 18566 &
python3 -m testenv.metrics_server --port 18990 &
python3 -m finops_agent run --aws-endpoint http://127.0.0.1:18566 --prom http://127.0.0.1:18990 --run-id demo --no-state
```

跑完后 `kill` 两个后台服务。日常用 `make demo` 或 `make eval`，它们自己管理服务进程。
