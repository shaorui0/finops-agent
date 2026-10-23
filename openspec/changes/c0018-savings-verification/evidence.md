# c0018-savings-verification 验收证据

## 1. `python3 -m unittest finops_agent.test_verify_savings -v`

```
test_amortized_saving_absorbed_by_unused_commitment (finops_agent.test_verify_savings.Commitment.test_amortized_saving_absorbed_by_unused_commitment) ... ok
test_no_drift_leaves_naive_and_adjusted_equal (finops_agent.test_verify_savings.Confounders.test_no_drift_leaves_naive_and_adjusted_equal) ... ok
test_usage_decline_does_not_inflate_the_saving (finops_agent.test_verify_savings.Confounders.test_usage_decline_does_not_inflate_the_saving) ... ok
test_usage_growth_is_separated_from_the_saving (finops_agent.test_verify_savings.Confounders.test_usage_growth_is_separated_from_the_saving) ... ok
test_sums_exactly_to_the_bill_delta (finops_agent.test_verify_savings.Decomposition.test_sums_exactly_to_the_bill_delta) ... ok
test_bills_decompose_exactly (finops_agent.test_verify_savings.EndToEnd.test_bills_decompose_exactly) ... ok
test_deletions_realize_the_predicted_amount (finops_agent.test_verify_savings.EndToEnd.test_deletions_realize_the_predicted_amount) ... ok
test_document_is_deterministic (finops_agent.test_verify_savings.EndToEnd.test_document_is_deterministic) ... ok
test_gp3_realized_in_october_lost_in_november (finops_agent.test_verify_savings.EndToEnd.test_gp3_realized_in_october_lost_in_november) ... ok
test_resolved_sets_match_scenario_expectations (finops_agent.test_verify_savings.EndToEnd.test_resolved_sets_match_scenario_expectations) ... ok
test_realized_then_lost (finops_agent.test_verify_savings.GP3.test_realized_then_lost) ... ok
test_regression_is_priced_in_the_bill (finops_agent.test_verify_savings.GP3.test_regression_is_priced_in_the_bill) ... ok
test_created_mid_period_then_deleted (finops_agent.test_verify_savings.Proration.test_created_mid_period_then_deleted) ... ok
test_deleted_mid_period_counts_the_steady_state (finops_agent.test_verify_savings.Proration.test_deleted_mid_period_counts_the_steady_state) ... ok

----------------------------------------------------------------------
Ran 14 tests in 5.913s

OK
```

## 2. `bash scripts/verify_savings.sh`（两次生成逐字节相同，结束后 34566/34567 无监听）

```
agent run verify-1 on base world
cost explorer 2026-09
agent run verify-2 on testenv/scenarios/next_month.yaml
cost explorer 2026-10
agent run verify-3 on testenv/scenarios/month_after.yaml
cost explorer 2026-11
4 verified, predicted $89.60, realized $89.60; bill decomposition exact: True; checks failed: 0
wrote docs/SAVINGS_VERIFICATION.md and reports/savings-verification.html
cmp: identical across two runs
listeners on 34566/34567:        0
```

## 3. 核心表（节选自 docs/SAVINGS_VERIFICATION.md，生成物）

**表 6 逐条核实：数字（标准月美元，除最后两列）**

| 行 | finding | 区间 | 预测 | 预测口径 | N 期成本 | 反事实 | N+1 实际 | 朴素节省 | 实现节省 | 实现率 | 首月现金 | 两张发票之差 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| V1 | F06 gp2 改 gp3 | 2026-09 到 2026-10 | $20.00 | list_price | $100.00 | $100.00 | $80.00 | $20.00 | $20.00 | 100.0% | $20.67 | $17.33 |
| V2 | F03 闲置 EIP | 2026-09 到 2026-10 | $3.60 | billed_14d_extrapolated | $3.60 | $3.60 | $0.00 | $3.60 | $3.60 | 100.0% | $3.72 | $3.60 |
| V3 | F02 未挂载卷 | 2026-09 到 2026-10 | $50.00 | billed_14d_extrapolated | $50.00 | $50.00 | $0.00 | $50.00 | $50.00 | 100.0% | $51.67 | $50.00 |
| V4 | F02 未挂载卷 | 2026-10 到 2026-11 | $16.00 | billed_14d_extrapolated | $16.00 | $16.00 | $0.00 | $16.00 | $16.00 | 100.0% | $16.00 | $12.80 |

**表 7 逐条核实：偏差原因与结论**

| 行 | 偏差原因 | 本期结论 | 下一期保持 | 最终结论 |
|---|---|---|---|---|
| V1 | 日历月天数：2026-10 有 31 天，首月现金与标准月不同；比较用 30 天标准月；预测口径：预测按牌价估算；账单实测与牌价一致 | 兑现 | 2026-11 保持 $0.00，丢失 $20.00 | 兑现后丢失 |
| V2 | 日历月天数：2026-10 有 31 天，首月现金与标准月不同；比较用 30 天标准月；预测口径：预测按近 14 天账单外推；与 N 期账单的标准月成本一致 | 兑现 | 2026-11 保持 $3.60，丢失 $0.00 | 兑现，后续保持 |
| V3 | 日历月天数：2026-10 有 31 天，首月现金与标准月不同；比较用 30 天标准月；预测口径：预测按近 14 天账单外推；与 N 期账单的标准月成本一致 | 兑现 | 2026-11 保持 $50.00，丢失 $0.00 | 兑现，后续保持 |
| V4 | 按天折算：vol-0new000000000e001 在 2026-10 只计费 24/31 天（自 2026-10-08）；预测口径：预测按近 14 天账单外推到 31 天，换算标准月 x30/31；与 N 期账单的标准月成本一致 | 兑现 | N+2 期无数据 | 兑现 |

**表 8 保持台账：N 期、N+1 期、N+2 期的标准月成本**

| 行 | finding | N 期成本 | N+1 实际 | N+2 实际 | N+1 实现 | N+2 仍实现 | 丢失 | N+2 期 diff 为 regressed |
|---|---|---|---|---|---|---|---|---|
**表 8 保持台账：N 期、N+1 期、N+2 期的标准月成本**

| 行 | finding | N 期成本 | N+1 实际 | N+2 实际 | N+1 实现 | N+2 仍实现 | 丢失 | N+2 期 diff 为 regressed |
|---|---|---|---|---|---|---|---|---|
| V1 | F06 gp2 改 gp3 | $100.00 | $80.00 | $100.00 | $20.00 | $0.00 | $20.00 | 是 |
| V2 | F03 闲置 EIP | $3.60 | $0.00 | $0.00 | $3.60 | $3.60 | $0.00 | 否 |
| V3 | F02 未挂载卷 | $50.00 | $0.00 | $0.00 | $50.00 | $50.00 | $0.00 | 否 |

V1（F06 gp2 改 gp3，`vol-0db0000000000a001`）：预测 $20.00，实现 $20.00，实现率 100.0%，朴素差 $20.00。首月现金 $20.67（31 天），两张发票之差 $17.33。下一期 2026-11：兑现后丢失。
**表 11 账单分解：账单差 = 已核实节省 + 回归损失 + 新增浪费 + 其他**

| 项目 | 2026-09 到 2026-10 | 2026-10 到 2026-11 | 含义 |
|---|---|---|---|
| 已核实节省 | -$76.05 | -$16.00 | resolved finding 的资源：反事实成本减实际成本（正数，账单上以负号进入） |
| 回归损失 | $0.00 | +$20.00 | regressed finding 的资源：实际成本减反事实成本 |
| 新增浪费 | +$12.80 | +$3.12 | 本期 new finding 的新资源，按本期实际成本计 |
| 日历天数与计费天数 | +$290.43 | -$292.77 | 全部资源：N 期日均成本乘 N+1 期天数，减 N 期实际成本（天数不同、半个月的资源补满整月） |
| 用量漂移 | +$247.75 | $0.00 | 全部资源：N+1 期实际成本减 N 期日均成本乘天数，对被处理的资源则是对照组漂移项 |
| 其他移除 | $0.00 | $0.00 | 没有对应 finding 的消失资源 |
| 其他新增 | $0.00 | $0.00 | 没有对应 finding 的新增资源 |
| 合计（各项之和） | +$474.93 | -$285.65 |  |
| 实际账单差（Cost Explorer） | +$474.93 | -$285.65 |  |
| 差（必须为 0） | $0.000000 | $0.000000 | 精确有理数运算，不是舍入后相等 |

2026-09 到 2026-10：账单从 $8,712.90 变到 $9,187.83，差 +$474.93。已核实节省 $76.05（F06、F03、F02），回归损失 $0.00（无），新增浪费 $12.80（F02），日历天数 +$290.43，用量漂移 +$247.75。各项相加与实际账单差的差值为 $0.000000。
**表 14 自检清单**

| 检查 | 结果 |
|---|---|
| 用量类型级合计与资源级合计相差不超过 $0.01（舍入） | 通过 |
| 账单分解各项之和与实际账单差精确相等（有理数） | 通过 |
| 每条核实的预测不超过该资源 N 期花费（FA04 不变量） | 通过 |
| 每条核实的实现节省不超过反事实成本（实际成本非负） | 通过 |
| 每条核实所用的层都有对照资源，没有退回全体平均 | 通过 |
| 资源 ID 全部在账单里有行 | 通过 |
| 各期 diff 与 scenario.expect 的 resolved / new / regressed 逐项一致 | 通过 |
| 价格表复算与账单一致（表 13 全部一致） | 通过 |

- 两条互相独立的路径对上了账。路径一：把 Cost Explorer 的日度成本行按资源汇总再取日均。路径二：用世界文件里的单价乘资源规格。两者在表 13 一致，说明汇总、日均和折算的代码没有算错。

## 4. `make test`

```
----------------------------------------------------------------------
Ran 3 tests in 0.073s

OK
python3 -m unittest discover -s tools -p 'test_*.py'
..............
----------------------------------------------------------------------
Ran 14 tests in 1.703s

OK
proposal written: /var/folders/88/jxwy9d9557g1jxg0jwsf2xvw0000gn/T/tmp6tf3etcr/proposal.md
python3 -W ignore -m unittest testenv.test_testenv finops_agent.test_pipeline finops_agent.test_slo finops_agent.test_llm finops_agent.test_judge eval.test_score
........run r1: 7 findings, 4 leads, invariants pass
run r2: 5 findings, 3 leads, invariants pass
run r3: 6 findings, 3 leads, invariants pass
.............run t: 12 findings, 7 leads, invariants pass
...............................................
----------------------------------------------------------------------
Ran 68 tests in 6.072s

OK
```

## 5. `openspec validate c0018-savings-verification`

```
Change 'c0018-savings-verification' is valid
```

## 6. `make check`（写完证据之后运行）

```
python3 tools/check_rules.py
check_rules: OK
```
