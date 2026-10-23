# 架构

这份文档回答两个问题：每个目录负责什么、一次运行产出的文件长什么样。方法论见 [`METHOD.md`](METHOD.md)，SLO 的设计动机见 [`FINOPS_SLO.md`](FINOPS_SLO.md)，改动流程见 [`../CONTRIBUTING.md`](../CONTRIBUTING.md)。

## 数据流

```
AWS API / Prometheus ──collect──> snapshot.json ──┬─ visibility ──> visibility.json
   （只读，经 Trace 留痕）          （冻结，分析只读它）  ├─ analyze ────> findings + leads
                                                    └─ slo ────────> slo.json, finops_metrics.prom
                                                                      │
                          runs/state.json <── 跨运行状态 ─────────────┤
                                                                      └─ report.html, trace.jsonl
```

三条设计约束贯穿全流程：

- 采集和分析分开。`collect` 把外部世界冻结成 `snapshot.json`，`analyze` 只读快照，所以任何一次运行都能用 `--snapshot` 重放。
- 数字由确定性代码产生。检测器只做算术和关联，需要跨源判断的信号以 `Lead` 的形式交出去。
- 所有外部调用都进 `trace.jsonl`，可审计，也是「只读」的证据。

## 进行中的部分

下面两块在并行的 change 里开发，尚未合入，本文档不描述它们的接口：

- 判断层（LLM）：接收 `Lead`，做跨源判断（change c0009，进行中）。
- 处置方案（remediation plans）：从发现生成可执行的处置计划（change c0011，进行中）。

## 模块地图

### `finops_agent/`：agent 本体

入口 `python3 -m finops_agent run`，参数见 `finops_agent/__main__.py`。

| 模块 | 输入 | 输出 | 说明 |
|---|---|---|---|
| `finops_agent/__main__.py` | 命令行参数 | `runs/<id>/` 下的全部产物 | 编排：collect、visibility 四环、analyze、slo、report。`--snapshot` 跳过采集，`--no-state` 不更新跨运行状态 |
| `finops_agent/collect.py` | `Config`（端点、区间） | `snapshot.json` 的内容、`Trace` | `Collector.aws()` 和 `Collector.prom()` 是仅有的两个外部出口，每次调用记入 `Trace`。`--aws-endpoint` 指向测试服务，省略则用真实 AWS 的环境凭据 |
| `finops_agent/analyze.py` | 快照、天数 | `Finding` 列表、`Lead` 列表、`ranking`、`attribution_summary` | 每个检测器是 `Analyzer` 的一个方法。`check_invariants` 检查节省不超过资源花费、金额有口径、证据非空 |
| `finops_agent/visibility.py` | `config/visibility_requirements.yaml`、快照、`Collector` | `visibility.json` 的四个段 | 四环：`ring1` 需求，`ring2` 计划，`ring3` 搜索（只查 Prometheus `/api/v1/series`），`ring4` 缺口 |
| `finops_agent/slo.py` | 结果、快照、`Collector`、上次状态、`config/finops_slo.yaml` | SLI 值、`slo.json`、`finops_metrics.prom`、新状态 | `compute_slis` 算值，`evaluate` 对目标，`diff_state` 标注 new、persisting、resolved、regressed，`to_prometheus` 导出 |
| `finops_agent/report.py` | 一次运行的结果 dict | `report.html`（单文件，无外链） | 按 M0 到 M6 组织，另有 SLO 表、可见性链表、运行留痕 |
| `finops_agent/test_pipeline.py` | 进程内起两个测试服务 | 断言 | 端到端一次完整运行 |
| `finops_agent/test_slo.py` | 构造的发现列表 | 断言 | 发现生命周期（新增、持续、解决、复发）和指标导出，不依赖测试服务 |

### `testenv/`：合成账号

详见 [`../testenv/README.md`](../testenv/README.md)。agent 只通过网络协议访问它，从不 import。

| 模块 | 输入 | 输出 | 说明 |
|---|---|---|---|
| `testenv/world.yaml` | 手写 | 账号事实 + `ground_truth` | 资源、价格、用量、标准答案（`findings`、`traps`、`visibility_gaps`） |
| `testenv/world.py` | `testenv/world.yaml` | 逐日成本行 `CostLine`、指标形状函数 | 两个服务和测试共用的推导层 |
| `testenv/aws_server.py` | HTTP 请求 | EC2、Auto Scaling、STS、Cost Explorer、Resource Groups Tagging、Savings Plans 响应 | 真实线上协议，由 botocore 的服务模型序列化。写操作返回 `UnauthorizedOperation`。`--log` 记录每次调用 |
| `testenv/metrics_server.py` | HTTP 请求 | Prometheus HTTP API 响应 | 支持 `query`、`query_range`、`series`、`labels`、`label/<name>/values`、`metadata`、`/-/healthy`，PromQL 子集见文件头注释 |
| `testenv/test_testenv.py` | 无 | 断言 | 校验节省区间与成本模型一致、陷阱形状、写操作被拒 |

### `eval/`：打分与回归基线

| 模块 | 输入 | 输出 | 说明 |
|---|---|---|---|
| `eval/score.py` | `findings.json`、`testenv/world.yaml` 的 `ground_truth`、`eval/baseline.json` | 同目录 `eval.json`、标准输出摘要、退出码 | 指标和闸门见 [`../CONTRIBUTING.md`](../CONTRIBUTING.md) 的 eval 一节。匹配规则：类型相同，或资源有交集且 `method_step` 相同 |
| `eval/baseline.json` | `--write-baseline` | `recall`、`savings_recall` 等基线值 | CI 用它卡回归 |
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
| `metric_names`、`metric_metadata` | Prometheus `/api/v1/label/__name__/values`、`/api/v1/metadata` |

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
| `diff` | 与上次状态比较：`new`、`persisting`、`resolved`、`regressed` 四个列表，元素含 `key`，`persisting` 带 `since`，`regressed` 带 `resolved_in` |
| `previous_runs` | 状态里记录的此前运行数 |

`value` 为 `null` 时 `status` 是 `no_data`，例如首次运行没有跨运行状态，`remediation_age_days` 就没有值。发现的 key 是 `<type>|<按字典序排序的资源 ID，逗号连接>`。

### `finops_metrics.prom`

Prometheus 文本格式，给 node_exporter 的 textfile collector 或 pushgateway 用。

| 指标 | 标签 | 含义 |
|---|---|---|
| `finops_last_run_timestamp_seconds` | 无 | 本次运行结束时间 |
| `finops_sli` | `sli`、`run` | 各 SLI 的值，`no_data` 的不导出 |
| `finops_slo_target` | `sli`、`op` | 各 SLO 目标 |
| `finops_findings` | `state` | 各生命周期状态的发现数（new、persisting、resolved、regressed） |
| `finops_waste_budget_usd`、`finops_waste_budget_used`、`finops_waste_usd` | 无 | 月浪费预算、已用比例、未处理浪费金额（有 `budget` 的 SLO 存在时导出） |

告警规则消费这些指标，见 `config/alerts/finops.rules.yml`。

### `trace.jsonl`

每行一次外部调用：`source`（`aws:<service>` 或 `prometheus`）、`op`（boto3 方法名或 Prometheus 路径）、`params`、`ms`、`ok`、`error`。`findings.json` 不含 trace，`report.html` 的运行留痕按 `source op` 聚合计数。

### `report.html`

自包含的单文件中文报告，无外部资源，支持深浅色。分区依次为：KPI 卡片、FinOps SLO 表、不变量违反（如有）、M0 到 M6 各步（发现卡片和线索卡片）、可见性链表、运行留痕。

### `runs/state.json`

跨运行状态，位置由 `--state` 决定（默认 `runs/state.json`，不在单次运行目录里），`--no-state` 时不写。字段：

| 字段 | 含义 |
|---|---|
| `runs` | 已记录的 run id 列表，按时间追加 |
| `open` | 上次运行仍未关闭的发现 key（排序） |
| `first_seen` | key 到首次出现日期（`--end` 的日期）的映射，用于 `remediation_age_days` |
| `resolved` | key 到「在哪次运行被判定为已解决」的映射。已解决的发现再次出现，就记为 `regressed` |

## 如何自己跑一遍

```bash
python3 -m testenv.aws_server --port 18566 &
python3 -m testenv.metrics_server --port 18990 &
python3 -m finops_agent run --aws-endpoint http://127.0.0.1:18566 --prom http://127.0.0.1:18990 --run-id demo --no-state
```

跑完后 `kill` 两个后台服务。日常用 `make demo` 或 `make eval`，它们自己管理服务进程。
