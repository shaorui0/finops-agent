# FinOps SLO：清理之后怎么办

一次成本优化做完，账单降下来，三个月后又涨回去。原因不是当时没做好，而是系统一直在产生新的浪费：新服务不打 tag，临时卷忘了删，fleet 迁了架构承诺没跟上，一次下游故障让重试把 NAT 账单放大五倍。成本健康和可用性一样会腐烂，所以要用同一套方法管：SLI、SLO、错误预算、告警、巡检节奏。

## 腐烂从哪来

| 来源 | 例子（测试账号里都有） | 哪个 SLI 先变 |
|---|---|---|
| 归因腐烂 | 新资源不打 owner；tag 与实际用途对不上 | attribution_coverage |
| 孤儿堆积 | 卷、快照、IP 在资源删掉后留下 | orphan_max_age_days |
| 承诺漂移 | 架构迁移后 Savings Plan 覆盖不到新机型 | commitment_utilization |
| 运行时异常放大成本 | 重试风暴、下游被删，计算和 NAT 一起涨 | useful_work_ratio、anomaly_time_to_detect_days |
| 可见性腐烂 | 依赖的 metric 改名或消失 | visibility_coverage |
| 修复不落地 | finding 报了没人处理 | remediation_age_days、waste_ratio |

## SLIs

定义在 `config/finops_slo.yaml`，每次运行由 `finops_agent/slo.py` 计算，导出为 Prometheus 指标 `finops_sli{sli=...}`。

| SLI | 含义 | SLO | 节奏 |
|---|---|---|---|
| waste_ratio | 已有证据、尚未处理的浪费（按已对账口径）/ 总花费 | ≤ 5% | 每日 |
| attribution_coverage | 带 owner 的花费占比 | ≥ 90% | 每周 |
| commitment_utilization | Savings Plan 利用率 | ≥ 90% | 每月 |
| orphan_max_age_days | 最老的孤儿资源存在天数 | ≤ 14 天 | 每周 |
| anomaly_time_to_detect_days | 成本异常开始到第一次被报出的天数 | ≤ 1 天 | 每日 |
| useful_work_ratio | 成功的工作 / 尝试的工作（对上报 job 结果的 fleet） | ≥ 95% | 每日 |
| visibility_coverage | 可见性需求中完全覆盖的比例 | 100% | 每周 |
| remediation_age_days | 跨运行仍未关闭的最老 finding | ≤ 30 天 | 每周 |

几条取舍：

- **为什么 useful_work_ratio 是成本 SLI。** CPU 60% 的 fleet 看起来很健康，但成功 job 为 0 时，它的全部计算都是浪费。只看利用率的成本监控会漏掉最贵的那种浪费。
- **为什么 anomaly_time_to_detect 单独算。** 测试账号里 NAT 异常从 09-04 开始，月底才被报出来：27 天。按月看账单的团队，最快也要一个账期才发现。这个 SLI 直接决定了巡检必须是每日的。
- **为什么 attribution_coverage 在测试账号里只有 25%。** 大部分未归因的花费是共享成本（NAT、跨 AZ、承诺费用），本来就不挂在资源上。这个数字逼出一个决定：共享成本按什么规则分摊。

## Waste budget

错误预算的对应物。每月浪费预算 = SLO 目标 × 花费（测试账号：5% × $8,713 ≈ $436）。当前未处理的浪费是 $1,144，预算用掉 262%。

预算的作用和可用性里一样：预算用完时，优化工作优先于新功能的扩容；预算充足时，不必为几美元的闲置 IP 打断别人。告警看的是燃烧速度：

| 告警 | 条件 | 意义 |
|---|---|---|
| 快烧 | 一天新增浪费 > 2 × 日预算 | 有东西刚出问题（重试风暴、误开大机器） |
| 慢烧 | 一周新增浪费 > 周预算 | 腐烂在累积（孤儿、tag 缺失） |
| 预算耗尽 | `finops_waste_budget_used > 1` 持续 1 小时 | 本月优化工作优先 |

## Rot

每次运行都和上一次比，`runs/state.json` 记录每条 finding 第一次出现的日期和被关闭的运行：

| 状态 | 含义 |
|---|---|
| new | 这次第一次出现 |
| persisting | 上次就有，还没处理（计入 remediation_age_days） |
| resolved | 上次有，这次没了，**并且**有成本侧证据说明资源或用量变了：资源已不在清单里，或属性变了（卷类型、状态、大小、关联），或近 14 天日均成本掉了 10% 以上 |
| not_redetected | 上次有，这次没了，但资源还在清单里、属性和成本都没变。这是漏检，不是修复，不计入 resolved |
| **regressed** | 曾经被关闭（resolved），又回来了 |

resolved 和 not_redetected 的区分靠 `state.json` 里每条 finding 检出时的资源指纹（`evidence`）：消失时拿当前快照对比。not_redetected 不进 resolved 记录，所以它之后重新出现算 persisting，不会被误报成 regressed；它会一直报 not_redetected，直到资源真的变了（转成 resolved）或 finding 又被检出（回到 persisting）。没有检出时指纹的旧 state 无法比较，资源还在就记 not_redetected。`finops_findings{state="not_redetected"}` 也会导出，目前没有告警挂在它上面：它多是检测器或判断层的问题，应在每周评审里看，而不是当作成本事故。

regressed 是腐烂最直接的信号：修过的东西没有防住复发，说明缺的是机制（生命周期策略、tag 强制、删除资源时的级联清理），而不是又一次手工清理。`FinOpsRegression` 告警在它出现时立即触发。

## Cadence

| 节奏 | 跑什么 | 看哪些 SLI | 谁处理 |
|---|---|---|---|
| 每日 01:15 | `make inspect`（cron，见 `ops/crontab.example`） | waste_ratio、anomaly_time_to_detect、useful_work_ratio；燃烧速度 | 值班 SRE 看告警 |
| 每周 | 同一份数据的周视图 | attribution、orphan age、visibility、remediation age；regressed 列表 | 各 owner 团队 |
| 每月 | 账单关账后 | commitment_utilization；架构级 finding；SLO 目标本身是否合理 | FinOps + 架构负责人 |

`FinOpsInspectionStale` 盯着巡检本身：超过两天没有新的运行，说明 cron 或 agent 坏了。监控系统自己也要被监控。

## 运行之间的早期信号

SLI 每天才算一次。两次运行之间，原始指标上的规则先报警（`config/alerts/finops.rules.yml` 的 `finops-signals` 组）：

### Busy but useless

`BusyButUselessFleet`：job 有尝试、没有成功，持续 30 分钟。这是成本告警里少有的 page 级别：每多一小时都是纯浪费，而且通常同时是一个可用性事故。

### Path cost

`NatBytesSurge`：NAT 字节超过 7 天均值的两倍。`RetryStorm`：每个 job 重试超过一次。两者一起出现时，先找共同原因再分别算钱。

### Visibility

`CostVisibilityMetricMissing`：SLI 依赖的指标消失。指标没了，SLI 不会报错，只会安静地变成 no_data，所以要单独告警。

## 验证

- `make alerts-test`：promtool 检查规则语法并跑单元测试（busy-but-useless 触发而健康 fleet 不触发；SLO 违反要持续一天才告警；regression 立即告警；巡检超过两天未运行告警）。
- `finops_agent/test_slo.py`：跨运行状态的完整生命周期（new → persisting → resolved → regressed）。
- `promtool check metrics` 校验导出的 `finops_metrics.prom`。
