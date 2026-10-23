# c0017 验收证据

实验：LLM 只看 `config/cost_goals.yaml`（业务语言），推出第 ① 环；对照人工评审版 `config/visibility_requirements.yaml` 打分。匹配规则见 `eval/score_visibility.py` 文件头：需求级，scope 重叠 且 name 正则在「服务器全部指标名 + 少量探针名」上有共同命中；通配正则（命中超过一半）不算。

## 调用与成本

| 轮 | prompt | 记录方式 | 调用 | 成本 USD |
|---|---|---|---|---|
| 1 | v1 | cassette 7e81725f7b79 | 1 | 0.0378 |
| 2 | v2 | cassette 5cb24a1ff34d + 2 次 live 重采样 | 3 | 0.0395 + 0.0286 + 0.0197 |
| 3 | v3 | cassette bc391572b38a + 2 次 live 重采样 | 3 | 0.0398 + 0.0272 + 0.0227 |

共 7 次调用（预算 10），合计约 0.215 USD。live 重采样不写 cassette，只用来量方差。

## prompt 迭代日志（对评审版最多 3 轮）

| 轮 | prompt 改动 | overlap（recall） | precision | 备注 |
|---|---|---|---|---|
| 1 | 初版：schema + scope 取值 + `not_metric_observable` | 0.73（8/11） | 0.64 | 漏 latency（猜了 `_seconds_bucket`）、cross-AZ（没单独给需求）、network_out 后缀猜错 |
| 2 | 加三句：名字末尾后缀不确定就 `.*`（示例里写了 `_bytes_sum`、`_seconds`、分位数）；scope 含义（基础设施指标用 running_instances，应用指标用 services:）；目标里列了多个对象时每个单独给信号 | 0.82（9/11）；重采样 0.64、0.73 | 0.71 | 示例后缀是看过服务器指标名之后写的，有后验泄漏嫌疑 |
| 3 | 去掉第 2 轮示例里的 `_bytes_sum`、`_seconds`、分位数，只留 `_sum`、`_total` | 0.91（10/11）；重采样 0.82、0.64 | 0.81 | 最终 cassette |

三轮每轮的 prompt 差异都能从 cassette 的 `prompt` 字段复原（`eval/cassettes/` 下三个文件）。

### 方差（同一 prompt，live 再采样）

```
v2: 0.82 (cassette)  0.64  0.73   均值 0.73
v3: 0.91 (cassette)  0.82  0.64   均值 0.79
```

重采样得分文件：
```
v2a: overlap 7/11 = 0.64, precision 0.75
v2b: overlap 8/11 = 0.73, precision 0.78
v3a: overlap 9/11 = 0.82, precision 0.69
v3b: overlap 7/11 = 0.64, precision 0.57
```
结论：录下来的 v3 cassette 恰好是较好的一次采样（0.91）；重复采样的期望在 0.75–0.8 附近，单次达标不等于稳定达标。

## 1 单测
```
test_replay_produces_valid_ring1_usable_by_rings_2_to_4 (finops_agent.test_visibility_llm.DeriveTest.test_replay_produces_valid_ring1_usable_by_rings_2_to_4) ... ok
test_validate_rejects_bad_scope_and_regex (finops_agent.test_visibility_llm.DeriveTest.test_validate_rejects_bad_scope_and_regex) ... ok
test_goals_file_has_no_metric_names_or_sli_ids (finops_agent.test_visibility_llm.PromptHygieneTest.test_goals_file_has_no_metric_names_or_sli_ids) ... ok
test_no_literal_from_the_reviewed_requirements (finops_agent.test_visibility_llm.PromptHygieneTest.test_no_literal_from_the_reviewed_requirements) ... ok
test_no_metric_name_from_the_server (finops_agent.test_visibility_llm.PromptHygieneTest.test_no_metric_name_from_the_server) ... ok
test_prompt_contains_the_goals (finops_agent.test_visibility_llm.PromptHygieneTest.test_prompt_contains_the_goals) ... ok
test_extra_derived_needs_are_split_by_whether_they_exist (finops_agent.test_visibility_llm.ScoreTest.test_extra_derived_needs_are_split_by_whether_they_exist) ... ok
test_probe_names_let_planted_gaps_be_compared (finops_agent.test_visibility_llm.ScoreTest.test_probe_names_let_planted_gaps_be_compared) ... ok
test_reviewed_against_itself_is_perfect (finops_agent.test_visibility_llm.ScoreTest.test_reviewed_against_itself_is_perfect) ... ok
test_scope_must_overlap (finops_agent.test_visibility_llm.ScoreTest.test_scope_must_overlap) ... ok
test_wildcard_regex_does_not_count (finops_agent.test_visibility_llm.ScoreTest.test_wildcard_regex_does_not_count) ... ok

----------------------------------------------------------------------
Ran 12 tests in 0.027s

OK
```

## 2 replay 确定性
```
$ python3 -m finops_agent.visibility_llm derive --out reports/0017-ring1-derived.yaml
7 SLIs, 16 needs -> reports/0017-ring1-derived.yaml  [replay sonnet tokens 74170/1692 $0.0398 key bc391572b38a]
$ python3 -m finops_agent.visibility_llm derive --out <另一路径> ; cmp  ->  REPLAY_IDENTICAL
```

## 3 打分（第 3 轮 cassette，最终）
```
overlap (recall of reviewed needs): 10/11 = 0.91   (target >= 0.80)
name-only recall (scope ignored):   0.91
precision: 13/16 = 0.81
reviewed SLIs fully covered: 7/8

reviewed SLI            needs  status   covered by (derived SLI ids)
idle_detection          2/2    covered  cost_anomaly_early_signal, idle_resource_evidence, rightsizing_headroom_slo, tidal_idle_pattern
useful_work_ratio       1/1    covered  unit_cost_denominator
rightsizing_headroom    2/2    covered  idle_resource_evidence, rightsizing_headroom_slo, tidal_idle_pattern
latency_slo_guard       1/1    covered  rightsizing_headroom_slo
schedule_detection      1/1    covered  tidal_idle_pattern, useful_work_ratio
unit_cost_per_job       2/2    covered  unit_cost_denominator
cross_az_attribution    0/1    missed   -   missed: .*_client_bytes_total
nat_attribution         1/1    covered  cost_anomaly_early_signal, shared_cost_attribution_traffic

derived needs that cover no reviewed need:
  idle_resource_evidence: aws_ec2_network_in.* [running_instances] -> matches no metric on the server
  useful_work_ratio: .*(success|succeeded|completed|ok).*_total.* [services:web,api,ingest-worker,etl-runner] -> matches no metric on the server
  shared_cost_attribution_traffic: .*(network_transmit_bytes|bytes_sent|egress_bytes|tx_bytes).* [services:web,api,web-dev,ingest-worker,etl-runner] -> matches no metric on the server

```

### 第 1 轮（对照）
```
overlap (recall of reviewed needs): 8/11 = 0.73   (target >= 0.80)
name-only recall (scope ignored):   0.73
precision: 9/14 = 0.64
reviewed SLIs fully covered: 5/8

reviewed SLI            needs  status   covered by (derived SLI ids)
idle_detection          1/2    partial  early_cost_anomaly_signal, idle_resource_evidence   missed: aws_ec2_network_out_.*
useful_work_ratio       1/1    covered  useful_work_ratio
rightsizing_headroom    2/2    covered  early_cost_anomaly_signal, idle_resource_evidence
latency_slo_guard       0/1    missed   -   missed: http_request_duration.*
schedule_detection      1/1    covered  tidal_vs_idle_pattern, useful_work_ratio
unit_cost_per_job       2/2    covered  unit_cost_denominator, useful_work_ratio
cross_az_attribution    0/1    missed   -   missed: .*_client_bytes_total
nat_attribution         1/1    covered  early_cost_anomaly_signal, shared_cost_attribution

derived needs that cover no reviewed need:
```

### 自测：评审版对评审版
```
overlap (recall of reviewed needs): 11/11 = 1.00   (target >= 0.80)
name-only recall (scope ignored):   1.00
precision: 11/11 = 1.00
reviewed SLIs fully covered: 8/8
```

## 4 ②–④ 环：派生版 vs 评审版（测试指标服务器，端口 33566）
```
rings 2-4 gap table:
ring-4 status reviewed SLI            derived SLI (status)                                          
covered       idle_detection          idle_resource_evidence (missing), rightsizing_headroom_slo (missing), tidal_idle_pattern (covered), cost_anomaly_early_signal (covered)
partial       useful_work_ratio       unit_cost_denominator (missing)
missing       rightsizing_headroom    idle_resource_evidence (missing), rightsizing_headroom_slo (missing), tidal_idle_pattern (covered)
covered       latency_slo_guard       rightsizing_headroom_slo (missing)
covered       schedule_detection      useful_work_ratio (missing), tidal_idle_pattern (covered)
missing       unit_cost_per_job       unit_cost_denominator (missing)
partial       cross_az_attribution    -
covered       nat_attribution         shared_cost_attribution_traffic (missing), cost_anomaly_early_signal (covered)

derived-only SLIs: (none)
reviewed ring-4 totals: {'covered': 4, 'partial': 2, 'missing': 2}
derived  ring-4 totals: {'covered': 2, 'partial': 0, 'missing': 5}
```

读法：评审版 ring 4 是 4 covered / 2 partial / 2 missing；派生版 2 covered / 0 partial / 5 missing。overlap 高但缺口表差很多，原因有三：

1. 派生版把需求合并成更粗的 SLI（例如 `rightsizing_headroom_slo` 把 CPU、内存、延迟放在一起），其中一个 need 找不到整个 SLI 就是 missing；评审版把它们拆成两个 SLI。
2. LLM 凭惯例写的名字（`aws_ec2_network_in.*`、按服务的 `network_transmit_bytes`）在服务器上不存在，被 ring 3 记成缺口。这类缺口是「名字猜错」而不是「真的没数据」。
3. 评审版里本来就是 planted gap 的（内存、处理字节数、跨 AZ 部分覆盖），派生版也都找出来了（内存 missing，job 处理量 missing），这是它真正有用的部分。

## 5 make test / make check
```
Ran 3 tests in 0.074s
OK
Ran 14 tests in 1.974s
OK
Ran 68 tests in 6.084s
OK
$ make check
check_rules: OK
```
注：Makefile 不在本 change 范围，`make test` 不含 `finops_agent.test_visibility_llm`，该文件在第 1 节单独跑。
