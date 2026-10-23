# c0021-savings-verification-real-deviations 验收证据

## 1. 基础世界与既有场景逐字节不变

`testenv/world.py` 新增 deleted、uptime、gp3 iops 与吞吐三个可选字段。下面是 sha256(repr(World.lines))（前 16 位）与卷列表的前后对比。

改动前（c0021 开工前，main 上）：

```
base lines=7e0e3f0d66e14042 vols=1fdbe1ce50ec90ac n=13883
testenv/scenarios/adversarial_asg_name.yaml lines=7e0e3f0d66e14042 vols=1fdbe1ce50ec90ac n=13883
testenv/scenarios/adversarial_job_label.yaml lines=7e0e3f0d66e14042 vols=1fdbe1ce50ec90ac n=13883
testenv/scenarios/adversarial_name_tag.yaml lines=bf15023d513302c4 vols=1fdbe1ce50ec90ac n=13883
testenv/scenarios/adversarial_number_bait.yaml lines=4d51ae9f709c8cbf vols=1fdbe1ce50ec90ac n=13883
testenv/scenarios/adversarial_owner_tag.yaml lines=b81cd388129368eb vols=1fdbe1ce50ec90ac n=13883
testenv/scenarios/adversarial_polite_authority.yaml lines=7b01a67409464035 vols=1fdbe1ce50ec90ac n=13883
testenv/scenarios/adversarial_trap_dr.yaml lines=b955f433be8f15e5 vols=1fdbe1ce50ec90ac n=13883
testenv/scenarios/adversarial_trap_web.yaml lines=19d1ab917de8b3a5 vols=1fdbe1ce50ec90ac n=13883
testenv/scenarios/adversarial_volume_name.yaml lines=0b8cc9078b6576a6 vols=2ac96ac8a9c3fc3a n=13883
testenv/scenarios/month_after.yaml lines=ef011dc78c1d9467 vols=e0ba4b83c1bee4a1 n=20375
testenv/scenarios/next_month.yaml lines=2571d950800c5123 vols=96d5195565d0b122 n=17073
```

改动后：

```
base lines=7e0e3f0d66e14042 vols=1fdbe1ce50ec90ac n=13883
testenv/scenarios/adversarial_asg_name.yaml lines=7e0e3f0d66e14042 vols=1fdbe1ce50ec90ac n=13883
testenv/scenarios/adversarial_job_label.yaml lines=7e0e3f0d66e14042 vols=1fdbe1ce50ec90ac n=13883
testenv/scenarios/adversarial_name_tag.yaml lines=bf15023d513302c4 vols=1fdbe1ce50ec90ac n=13883
testenv/scenarios/adversarial_number_bait.yaml lines=4d51ae9f709c8cbf vols=1fdbe1ce50ec90ac n=13883
testenv/scenarios/adversarial_owner_tag.yaml lines=b81cd388129368eb vols=1fdbe1ce50ec90ac n=13883
testenv/scenarios/adversarial_polite_authority.yaml lines=7b01a67409464035 vols=1fdbe1ce50ec90ac n=13883
testenv/scenarios/adversarial_trap_dr.yaml lines=b955f433be8f15e5 vols=1fdbe1ce50ec90ac n=13883
testenv/scenarios/adversarial_trap_web.yaml lines=19d1ab917de8b3a5 vols=1fdbe1ce50ec90ac n=13883
testenv/scenarios/adversarial_volume_name.yaml lines=0b8cc9078b6576a6 vols=2ac96ac8a9c3fc3a n=13883
testenv/scenarios/month_after.yaml lines=ef011dc78c1d9467 vols=e0ba4b83c1bee4a1 n=20375
testenv/scenarios/next_month.yaml lines=2571d950800c5123 vols=96d5195565d0b122 n=17073
```

比对结果：完全相同。基础世界、next_month、month_after 的完整 64 位 sha256 由 `test_base_and_existing_scenarios_are_byte_identical` 钉住。

## 2. `python3 -m unittest finops_agent.test_verify_savings -v`

```
test_earlier_partial_deletion_is_carried_over_in_the_next_bill (finops_agent.test_verify_savings.Classification.test_earlier_partial_deletion_is_carried_over_in_the_next_bill) ... ok
test_extra_usage_types_explain_a_list_price_shortfall (finops_agent.test_verify_savings.Classification.test_extra_usage_types_explain_a_list_price_shortfall) ... ok
test_list_price_prediction_carries_the_31_day_month (finops_agent.test_verify_savings.Classification.test_list_price_prediction_carries_the_31_day_month) ... ok
test_mid_period_deletion_has_a_first_month_cash_rate (finops_agent.test_verify_savings.Classification.test_mid_period_deletion_has_a_first_month_cash_rate) ... ok
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
test_a_mid_period_deletion_is_partial_in_the_first_month_and_full_after (finops_agent.test_verify_savings.ScenarioChain.test_a_mid_period_deletion_is_partial_in_the_first_month_and_full_after) ... ok
test_agent_diff_matches_the_scenario_expectations (finops_agent.test_verify_savings.ScenarioChain.test_agent_diff_matches_the_scenario_expectations) ... ok
test_b_dev_hours_are_absorbed_by_the_savings_plan (finops_agent.test_verify_savings.ScenarioChain.test_b_dev_hours_are_absorbed_by_the_savings_plan) ... ok
test_b_the_unused_commitment_grows_by_the_absorbed_amount (finops_agent.test_verify_savings.ScenarioChain.test_b_the_unused_commitment_grows_by_the_absorbed_amount) ... ok
test_c_growth_hides_the_saving_from_the_naive_comparison (finops_agent.test_verify_savings.ScenarioChain.test_c_growth_hides_the_saving_from_the_naive_comparison) ... ok
test_d_list_price_prediction_misses_iops_and_throughput (finops_agent.test_verify_savings.ScenarioChain.test_d_list_price_prediction_misses_iops_and_throughput) ... ok
test_e_a_clean_deletion_has_no_deviation (finops_agent.test_verify_savings.ScenarioChain.test_e_a_clean_deletion_has_no_deviation) ... ok
test_portfolio_realization_is_below_one_and_the_bill_decomposes_exactly (finops_agent.test_verify_savings.ScenarioChain.test_portfolio_realization_is_below_one_and_the_bill_decomposes_exactly) ... ok
test_the_document_is_deterministic_and_all_checks_pass (finops_agent.test_verify_savings.ScenarioChain.test_the_document_is_deterministic_and_all_checks_pass) ... ok
test_deleted_idle_volume_is_not_scaled_by_data_growth (finops_agent.test_verify_savings.Strata.test_deleted_idle_volume_is_not_scaled_by_data_growth) ... ok
test_thin_stratum_falls_back_to_the_coarse_class (finops_agent.test_verify_savings.Strata.test_thin_stratum_falls_back_to_the_coarse_class) ... ok
test_base_and_existing_scenarios_are_byte_identical (finops_agent.test_verify_savings.WorldFeatures.test_base_and_existing_scenarios_are_byte_identical) ... ok
test_deleted_uptime_and_gp3_extras (finops_agent.test_verify_savings.WorldFeatures.test_deleted_uptime_and_gp3_extras) ... ok
----------------------------------------------------------------------
Ran 31 tests in 17.800s
OK
```

## 3. `bash scripts/verify_savings.sh`（端口 37566/37567；两次生成逐字节相同；结束后无监听）

```
agent run verify-control-3 on testenv/scenarios/month_after.yaml
cost explorer 2026-11
scenario chain: 5 verified, predicted $744.21, realized $140.60 (18.9%); control chain: 4 verified, predicted $89.60, realized $89.60; bill decomposition exact: True; checks failed: 0
wrote docs/SAVINGS_VERIFICATION.md and reports/savings-verification.html
cmp: identical across two runs
listeners on 37566/37567: 0
```

## 4. D19：场景链上的真实偏差（节选自 docs/SAVINGS_VERIFICATION.md，生成物）

**表 A1 偏差总表（预测与实现为标准月美元；首月现金率 = 首月现金节省 / 预测折算到该月天数）**

| 项 | finding | 区间 | 预测 | 实现 | 实现率 | 首月现金实现率 | 次月现金实现率 | 原因分类 | 结论 |
|---|---|---|---|---|---|---|---|---|---|
| （a）期中删除未挂载卷 | F03 `unattached_volume` | 2026-09 到 2026-10 | $60.00 | $60.00 | 100.0% | 67.7% | 100.0% | 按天折算（期中变更） | 兑现。标准月实现 100.0%，首月现金只有 67.7%（vol-0vfya000000000001 在 2026-10 只计费 10/31 天（至 2026-10-10 止）），因为资源在期中才删除；下一期现金实现率 100.0%。 |
| （b）dev 启停（SP 覆盖的 m5） | C01 `schedule_dev_but_sp_covered` | 2026-09 到 2026-10 | $580.61 | $0.00 | 0.0% | 0.0% | 0.0% | 承诺吸收 | 现金未省：纸面 $580.61 中 $418.04 被 Savings Plan 未用承诺吸收，$162.57 是预测按按需价、SP 覆盖的实例按折扣价入账。不应计入节省，先处理承诺利用率再谈停机。 |
| （c）gp2 改 gp3，同期用量增长 30% | F08 `gp2_to_gp3` | 2026-09 到 2026-10 | $40.00 | $52.00 | 130.0% | 130.0% | 130.0% | 用量漂移（对照组校正） | 节省真实，量被增长掩盖：朴素对比 -$8.00，校正后 $52.00（预测 $40.00）。校正量来自对照组 g。 |
| （d）gp2 改 gp3，保留 IOPS 与吞吐 | F05 `gp2_to_gp3` | 2026-10 到 2026-11 | $60.00 | $25.00 | 41.7% | 41.7% | 无 N+2 | 预测口径差 | 实现 $25.00，是预测 $60.00 的 41.7%：差额由新增的 IOPS 与吞吐用量类型解释。预测应改用含 IOPS 与吞吐的 gp3 总价。 |
| （e）释放闲置 EIP（对照，无偏差） | F04 `idle_public_ip` | 2026-09 到 2026-10 | $3.60 | $3.60 | 100.0% | 100.0% | 100.0% | 无偏差 | 兑现，实现率 100.0%。 |
| 合计 | 5 条 |  | $744.21 | $140.60 | 18.9% | 16.2% |  |  |  |

**表 A18 设计值对账：不看账单、只从世界规格与价格表算出应有的节省，对比核实器给出的数**

| 项 | 设计值 | 核实器 | 差 |
|---|---|---|---|
| （a）首月现金 = 日均 x 未计费天数 | $42.00 | $42.00 | $0.0000 |
| （b）账单口径节省 = 0（SP 覆盖，Unblended 相抵） | $0.00 | $0.00 | $0.0000 |
| （b）摊销口径节省 = 按需价 x SP 折扣后 x 停机比例 | $418.04 | $418.04 | $0.0000 |
| （c）实现 = 反事实（成本 x 世界规格算出的增速）减 N+1 成本 | $52.00 | $52.00 | $0.0000 |
| （d）实现 = N 期价格表成本 减 N+1 期价格表成本 | $25.00 | $25.00 | $0.0000 |
| （e）实现 = 价格表上的 EIP 月费 | $3.60 | $3.60 | $0.0000 |

**表 A19 自检清单**

| 检查 | 结果 |
|---|---|
| （a）分类为按天折算，首月现金实现率 < 98%，次月现金实现率在 ±2% 内 | 通过 |
| （b）分类为承诺吸收：预测 > 0，账单口径实现在 ±2% 内为 0，摊销口径节省 > 0 | 通过 |
| （b）独立证据：承诺行的摊销增加等于被吸收的金额（1 美分内） | 通过 |
| （c）分类为用量漂移：朴素节省为负，校正后为正，且与朴素值相差大于预测的 2% | 通过 |
| （d）分类为预测口径差：短缺与新增 IOPS/吞吐用量类型合计吻合（2%） | 通过 |
| （e）对照项无偏差分类，实现率在 ±2% 内 | 通过 |
| 组合实现率小于 100% | 通过 |
| 账单分解各项之和与实际账单差精确相等（有理数） | 通过 |
| 设计值对账：全部在 1 美分内（（c）因 CE 六位小数舍入放宽到 1 美分） | 通过 |
| 价格表复算与账单一致（表 A17 全部一致） | 通过 |
| 各期 diff 与 scenario.expect 的 resolved / new / regressed 逐项一致 | 通过 |
| 每条核实所用的层都有对照资源，没有退回全体平均 | 通过 |
| 用量类型级合计与资源级合计相差不超过 $0.01（舍入） | 通过 |

逐行来源见 `docs/SAVINGS_VERIFICATION.md`：A6（a 的三个口径）、A7 与 A8（b）、A9 与 A10（c）、A11 与 A12（d）、A15（账单分解）。

## 5. 对照链仍是 100%，数字与 c0018 相同

`git diff main -- docs/SAVINGS_VERIFICATION.md` 的删除行只有标题编号与四处过时的措辞（端口、分层说明、两处局限、结论），B 部分所有表格的数字行无改动。脚本输出里 control chain 为 4 verified, predicted $89.60, realized $89.60，与 c0018 evidence 一致。

## 6. `make test`

```
Ran 3 tests in 0.072s
OK
Ran 14 tests in 1.932s
OK
Ran 108 tests in 7.357s
OK
make test exit 0
```

`make test` 不含 `finops_agent.test_verify_savings`（Makefile 不在本 change 范围），该测试单独跑，见第 2 节。

## 7. `openspec validate c0021-savings-verification-real-deviations`

```
Change 'c0021-savings-verification-real-deviations' is valid
```

## 8. LLM 调用

全部 agent 运行使用 `--no-judge`，录制的 LLM 调用数为 0（预算 10）。`eval/cassettes` 无改动。

## 9. `make check`（证据写完后运行）

```
python3 tools/check_rules.py
check_rules: OK
```
