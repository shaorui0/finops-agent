# c0020 evidence

## 0 摘要
- 5 次采样 overlap 均值 **0.964**（min 0.91，max 1.00），目标 mean >= 0.8：**达标**。prompt 只迭代了 1 轮（v4），第 2 轮没有用。
- 对照 c0017（prompt v3，猜正则）：录制 0.91，重采样 0.82 / 0.64，均值约 0.79。
- LLM 调用共 10 次（5 次 N=5 官方 + 5 次额外 draw 6-10 做稳定性复核），合计 0.3105 USD（cassette 里的 cost_usd 之和）；预算 15 次。
- 评审路径：`visibility.json` 的 gaps 前后逐字节一致；`make eval` 指标前后一致。

口径变化要说清：c0017 的 overlap 是「LLM 写的正则」和评审正则在服务器指标名上有交集；c0020 的 overlap 是「ring 2 按 terms 发现的候选名」和评审正则有交集。两者衡量的东西不同（后者包含确定性发现这一步），0.79 到 0.96 不是同一把尺子上的提升。

## 1 prompt 迭代日志（上限 2 轮）
| 轮 | 改动 | 每次采样 overlap（draw 1-5） | 均值 | 调用 |
|---|---|---|---|---|
| 1 | v3 到 v4：去掉 `name`，改为 `signal` + `concept`（英文短语）+ `terms`（5-8 个小写单词）+ `scope`；`(draw #k)` 只用来区分 cassette | 0.91 0.91 1.00 1.00 1.00 | 0.964 | 5 |
| 2 | 未做（第 1 轮已达标） | - | - | 0 |

稳定性复核（不算 prompt 迭代，同一个 v4 prompt 的 draw 6-10）：0.91 1.00 0.91 1.00 1.00；N=10 均值 0.964，min 0.91，max 1.00；5 次调用。

没覆盖的评审 need 全是 `.*_client_bytes_total`（跨 AZ 数据传输）。看 draw 1、2 的派生文件：它们没有任何跨 AZ 的 need，G6 的第二条路径（跨 AZ 归因）被合并或漏掉了，这是 ring 1 本身的漏项，ring 2 发现帮不上。

## 2 N=5 采样（replay，可复现）
```
$ python3 -m eval.score_visibility --samples 5
sample  overlap         precision  cost_usd  missed reviewed needs
1       10/11 = 0.91   0.86       0.0283    .*_client_bytes_total
2       10/11 = 0.91   0.93       0.0308    .*_client_bytes_total
3       11/11 = 1.00   0.83       0.0327    -
4       11/11 = 1.00   0.88       0.0309    -
5       11/11 = 1.00   0.78       0.0318    -

overlap over 5 samples: mean 0.964  min 0.91  max 1.00   (target: mean >= 0.80)
precision mean 0.857
verdict: MET (mean 0.964)
```
replay 跑两次，输出逐字节一致，5 份派生 YAML 与录制时一致。5 份派生文件在 `reports/0020-ring1-samples/`。

## 3 缺口表：派生（ring 2 发现之后）对评审，测试指标服务器
命令：`python3 -m eval.score_visibility --samples 5 --prom http://127.0.0.1:36567 --snapshot runs/<run>/snapshot.json`（取 overlap 居中的采样，即 draw 3）。
```
rings 2-4 gap table (median sample 3):
ring-4 status reviewed SLI            derived SLI (status c/p/m needs)                              
covered       idle_detection          idle_resource_evidence (partial 2/0/1), rightsizing_headroom_slo (partial 2/0/1), tidal_idle_pattern (covered 2/0/0), nat_traffic_attribution (covered 2/0/0), cost_anomaly_early_signal (covered 2/0/0)
partial       useful_work_ratio       effective_work_ratio (partial 0/2/1), unit_cost_denominator (partial 1/0/1)
missing       rightsizing_headroom    idle_resource_evidence (partial 2/0/1), rightsizing_headroom_slo (partial 2/0/1), tidal_idle_pattern (covered 2/0/0)
covered       latency_slo_guard       rightsizing_headroom_slo (partial 2/0/1), tidal_idle_pattern (covered 2/0/0)
covered       schedule_detection      effective_work_ratio (partial 0/2/1), tidal_idle_pattern (covered 2/0/0)
missing       unit_cost_per_job       effective_work_ratio (partial 0/2/1), unit_cost_denominator (partial 1/0/1)
partial       cross_az_attribution    cross_az_traffic_attribution (partial 0/1/0)
covered       nat_attribution         nat_traffic_attribution (covered 2/0/0), cost_anomaly_early_signal (covered 2/0/0)

derived-only SLIs: (none)
reviewed ring-4 totals: {'covered': 4, 'partial': 2, 'missing': 2}
derived  ring-4 totals: {'covered': 3, 'partial': 5, 'missing': 0}

ring-2 discovery per derived need (candidate metric names found by meaning):
  idle_resource_evidence: cpu utilisation percent per instance [running_instances] -> aws_ec2_cpuutilization_average
  idle_resource_evidence: network bytes transferred per second per instance [running_instances] -> aws_ec2_network_out_bytes_sum
  idle_resource_evidence: disk io bytes per second per instance [running_instances] -> (no candidate)
  effective_work_ratio: successful requests or jobs completed per second per service [services:web,api,web-dev,ingest-worker,etl-runner] -> (no candidate)
  effective_work_ratio: attempted requests or jobs including retries per second per service [services:web,api,web-dev,ingest-worker,etl-runner] -> ingest_job_retries_total, http_requests_total, ingest_jobs_total
  effective_work_ratio: failed or error responses per second per service [services:web,api,web-dev,ingest-worker,etl-runner] -> ingest_downstream_errors_total
  rightsizing_headroom_slo: memory utilisation percent per instance [running_instances] -> (no candidate)
  rightsizing_headroom_slo: cpu utilisation percent per instance [running_instances] -> aws_ec2_cpuutilization_average
  rightsizing_headroom_slo: request latency distribution in seconds per service [services:web,api] -> http_request_duration_p99_seconds
  tidal_idle_pattern: incoming requests per second per service over time [services:web,api,web-dev] -> http_requests_total, http_request_duration_p99_seconds
  tidal_idle_pattern: cpu utilisation percent per instance [running_instances] -> aws_ec2_cpuutilization_average
  nat_traffic_attribution: bytes processed per NAT gateway [nat_gateways] -> aws_natgateway_bytes_out_to_destination_sum
  nat_traffic_attribution: network egress bytes per second per instance [running_instances] -> aws_ec2_network_out_bytes_sum
  cross_az_traffic_attribution: cross availability zone bytes transferred between services [services:web,api,web-dev,ingest-worker,etl-runner] -> db_client_bytes_total
  unit_cost_denominator: completed ingest jobs count per service [services:ingest-worker] -> ingest_jobs_total, ingest_job_retries_total, ingest_downstream_errors_total
  unit_cost_denominator: data units or bytes processed per service [services:ingest-worker,etl-runner] -> (no candidate)
  cost_anomaly_early_signal: bytes processed per second per NAT gateway [nat_gateways] -> aws_natgateway_bytes_out_to_destination_sum
  cost_anomaly_early_signal: network bytes per second per instance [running_instances] -> aws_ec2_network_out_bytes_sum

```

读法：
1. 评审版 ring 4：4 covered / 2 partial / 2 missing。派生版（mix 模式）：3 covered / 5 partial / 0 missing。c0017 里同样的派生版是 2 covered / 0 partial / 5 missing。合并 SLI 里有一个 need 没找到，不再让整个 SLI 变 missing。
2. 派生版没有 missing，不等于比评审版好：partial 里的 need 级 partial（例如 `0/2/1`）是指标找到了，但 scope 没覆盖全（service 列表里有的服务没有这个指标），这是真实的覆盖缺口。
3. 评审版里 planted gap 的内存和「处理字节数」，ring 2 都没有候选（`(no candidate)`），ring 3 照实记 missing，没有被 CPU 指标或 `db_client_bytes_total` 顶替（泛词规则挡掉了这类误配）。
4. ring 2 的发现不完美：「successful requests or jobs completed」没有候选；「completed ingest jobs count」把 `ingest_job_retries_total`、`ingest_downstream_errors_total` 也带进来了。候选宁多勿漏，之后由 ring 3/4 检查。
5. 评审版 `rightsizing_headroom` 在 ring 4 是 missing，是因为内存本来就没有（planted gap），不是派生版的问题。

## 4 评审路径不变
```
$ # main 上跑 pipeline，取 visibility.json 的 gaps（sort_keys 写出）；本分支同样跑一遍
$ cmp gaps_before.json gaps_after.json && echo GAPS_IDENTICAL
GAPS_IDENTICAL

$ make eval   # main
{"recall": 1.0, "savings_recall": 1.0, "precision": 1.0, "savings_accuracy": 0.9167, "step_agreement": 1.0, "depth": {"shallow_recall": 1.0, "deep_recall": 1.0}, "leads": 7}
missed: 
gates: pass
$ make eval   # 本分支
{"recall": 1.0, "savings_recall": 1.0, "precision": 1.0, "savings_accuracy": 0.9167, "step_agreement": 1.0, "depth": {"shallow_recall": 1.0, "deep_recall": 1.0}, "leads": 7}
missed: 
gates: pass
```
`ring4` 默认 `mix=False`，评审路径输出不带 `mix` 字段；`ring2` 对带 `name` 的 need 不走发现。`test_visibility.ReviewedPathUnchangedTest` 固化了这一点。

## 5 测试
```
$ python3 -W ignore -m unittest finops_agent.test_visibility finops_agent.test_visibility_llm
Ran 24 tests ... OK
$ make test        # 108 tests, OK
$ make check
check_rules: OK
```
Makefile 不在本 change 范围，`make test` 不含两个新测试文件，上面单独跑。

## 6 局限与事故
- 均值达标是「ring 1 说词 + 一个确定性 `discover`」合起来的结果。`discover` 的规则（至少 2 个 term、泛词不能单独撑、scope 标签、3 个字符以上做子串匹配）是看过测试服务器目录之后定的，换一个命名风格不同的服务器，召回可能下降。这个 overlap 不能外推到真实环境。
- `GENERIC` 泛词表和子串规则是代码里的词表，不在 prompt 里，不违反 FA12，但它是调参点。
- precision 0.78 到 0.93（5 次均值 0.857）：LLM 多写的 need 有些在服务器上没有对应指标（磁盘 IO 等），属于「我需要但看不到」，不算错。
- 评审版只有 11 个 need，漏 1 个就是 0.09，所以 min 0.91 对应漏 1 个。
- 事故：写本文件时 shell 误把 Markdown 里的反引号 `make eval` 当命令执行了一次，在默认端口 4566/9090 起过测试服务器，跑完由 `make stop` 关掉，之后确认没有监听残留。其余所有运行都用 36566-36571。
