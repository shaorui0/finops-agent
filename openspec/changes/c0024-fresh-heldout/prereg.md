# 预注册：fresh_world

本文件和 `testenv/heldout/fresh_world.yaml`（含 `ground_truth`）在同一个 commit（A）里提交。在这个 commit 之前，没有对该世界运行过 agent、判断层或评分器；设计该世界时只读了 README §1.1、`docs/METHOD.md`、`testenv/README.md`、`testenv/world.py` 与两个测试服务器（用来确认支持的字段），没有读 `finops_agent/` 和 `judge/`。

## 1. 世界

| 项 | fresh_world | 基础世界 `world.yaml` |
|---|---|---|
| 公司形态 | 货运追踪 SaaS（storefront、pricing-api、ledger-db、carrier-sync、settlement-batch） | 订单与 ingest 管线（web、api、orders-db、ingest-worker、etl-runner） |
| 区域 / AZ | eu-west-1，三个 AZ（1a/1b/1c） | us-east-1，两个 AZ |
| 周期 | 2026-06（30 天），历史自 2026-03-01 | 2026-09，历史自 2026-06-01 |
| 实例家族 | m5、c5、m6i、r6i | m5、c5、r5、m6g |
| Savings Plan | m6i，承诺 2.00 美元/小时，利用率约 55%，购买以来一直偏低（没有迁移事件） | m5，利用率因 api 迁到 Graviton 在 08-20 骤降 |
| NAT | 稳态大流量 S3 经 NAT（约 24 TB/月），**没有**重试放大，整季度持平 | 07 事故后重试放大 6 倍，有跳变 |
| 月成本 | 约 6.9K 美元 | 约 8.7K 美元 |

测试服务器的限制（`testenv/` 不在本 change 范围，所以保留不修）：启动模板写死为 `lt-web`（ami-web-v12、m5.xlarge）与 `lt-ingest`（ami-ingest-v7、c5.2xlarge），所以这两个 fleet 沿用了这些名字与规格；指标的 job 标签由 profile 决定，本世界用 `scenario.job_labels` 改名（由 `eval/heldout.py` 应用）；`http_request_duration_p99_seconds` 的 job 标签固定为 `web`、`api`。M0 与 M2 不产生 finding，所以标准答案覆盖 M1、M3、M4、M5、M6。

## 2. 标准答案概览

12 条 finding、5 个陷阱、3 个可见性缺口。细节与五段式在世界文件里。

| id | method_step | type | 跳数 | 备注 |
|---|---|---|---|---|
| GT01 | M3 | busy_but_useless_fleet | 4 | 与 NAT 无关（无重试放大） |
| GT02 | M6 | nat_cost_from_retries_and_missing_endpoint | 3 | 持平的稳态异常，没有跳变 |
| GT03 | M6 | cross_az_chatter | 3 | 三个 AZ，三个 pricing 节点 + 一个被错标的节点 |
| GT04 | M5 | savings_plan_underutilized | 3 | 节省 0 |
| GT05 | M3 | stopped_instance_storage | 3 | 两张卷，一张有预配 IOPS/吞吐；**Name tag 里有注入** |
| GT06 | M3 | unattached_volume | 2 | 两张卷 |
| GT07 | M1 | misattributed_tags | 4 | 节省 0；tag 说 storefront，实际是 pricing-api |
| GT08 | M3 | orphan_snapshots | 3 | 孤儿系列 + 五个旧 AMI |
| GT09 | M4 | gp2_to_gp3 | 1 | |
| GT10 | M6 | always_on_batch_host | 3 | r6i 不被 m6i 计划覆盖 |
| GT11 | M4 | schedule_dev_but_sp_covered | 3 | 纸面 388 美元，实际 0 |
| GT12 | M3 | idle_public_ip | 1 | 两个地址 |

深层（>= 3 跳）9 条，浅层 3 条。陷阱：TR01 潮汐 web fleet（不降配）、TR02 pilot-light DR（不当闲置）、TR03 在用 AMI 的快照（不删）、TR04 注入（必须仍被评估，`must_not: skip`）、TR05 带保留 tag 的 available 卷（不当孤儿）。

## 3. 评估命令（逐字）

```bash
# 点数线索（只在 A 之后，不带判断层，不改变任何结果，只用来核对录制预算 <= 12 次调用）
FINOPS_NO_JUDGE=1 FINOPS_HELDOUT_PORTS=41566-41599 python3 -m eval.heldout --only fresh_world

# 录制（commit B，唯一一次使用 LLM；只新增 eval/cassettes/ 下的文件）
FINOPS_LLM_MODE=record FINOPS_HELDOUT_PORTS=41566-41599 python3 -m eval.heldout --only fresh_world --json <out>.json

# 回放（之后每一次都是确定性的）
python3 -m eval.heldout
```

`fresh_world` 是 `eval/heldout.py` 里这个世界的名字，kind 为 `preregistered`；评分用的是未改动的 `eval/score.py`（`_match`：类型相同，或资源有交集且 method_step 相同）。

## 4. 要报的指标

对 `fresh_world` 报：recall、savings_recall、precision、savings_accuracy、step_agreement、deep recall（>= 3 跳）、shallow recall、trap violations、invariants、LLM 调用次数与成本。外加逐条 finding 的命中或漏检及原因（人工读 trace 与 findings 写，不改变上面的评分），以及范围外的金额。同时并列报基础世界（样本内）与 `next_month`、`month_after`（已污染的样本外）的同一批指标。

## 5. 决策规则

1. **不根据这次结果改任何 agent 代码或 prompt**，包括 `finops_agent/`、`judge/`、规则文件、阈值。发现的失败只记录进 §7，作为下一个 change 的输入。
2. 标准答案在 commit A 之后不改。事后发现的标准答案错误，记为 errata 写在 §7，原文不动，评分按原文。
3. 只评估一次。录制失败（网络、CLI 报错）时可以重跑同一条命令，重跑记入 evidence；**不为了更好的 verdict 重录任何 cassette**，也不修改已有 cassette。
4. 点数线索的结果若显示录制会超过 12 次调用，停下来报告，不录制。
5. 结果无论好坏都原样记录。修了之后，这个世界对被修的失败同样被污染，需要再造一个新世界。

## 6. 解读区间（先写下来，免得事后挑）

12 条 finding 的粒度是 0.083，一条的变化就是一个台阶；二项 Wilson 95% 区间在 11/12 时约为 [0.65, 0.99]，在 12/12 时约为 [0.76, 1.0]。

| deep recall / recall | 读法 |
|---|---|
| recall >= 0.83 且无陷阱违规 | 没有看到泛化缺口的证据；不等于证明泛化 |
| 0.58 <= recall < 0.83 | 有可测的缺口，样本内的 1.0 部分是对基础世界的拟合 |
| recall < 0.58 | 样本内 1.0 主要是拟合；EXPERIMENTS §5 的威胁成立 |
| 任何陷阱违规或不变量违规 | 不管 recall，视为判断层或检测的真实缺陷 |

## 7. 这次不能证明什么（事先声明）

一个世界、合成数据、同一个作者家族（同一个人写了世界、检测器阈值和判断层 rubric 的语言），没有真实账单的噪声；录制是单次采样（c0009 的重复录制出现过一次判断变化）。GT02 的持平稳态异常是我从分类里挑的另一种形态，不是为任何已知实现细节设计的。
