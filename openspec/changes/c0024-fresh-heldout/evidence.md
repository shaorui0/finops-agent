# c0024 验收证据

所有输出为原样粘贴。端口只用 41566-41599（FINOPS_HELDOUT_PORTS）。

## E1 提交顺序（A 预注册 → B 录制并评估 → C 结果）

```
4b8523e c0024-fresh-heldout [5/6 impl C results]: 钉住预注册世界的数字；EXPERIMENTS §7 结果、逐条命中与漏检、勘误、比较
1ab746f c0024-fresh-heldout [4/6 impl B record+run]: 录制 8 次判断调用并评估一次；heldout.py 加入 fresh_world（preregistered）
e5d4689 c0024-fresh-heldout [3/6 impl A preregister]: 新世界、标准答案、评估命令、指标与决策规则；运行前冻结
ca3e489 c0024-fresh-heldout [2/5 spec+tasks]: 预注册、完整世界、只评估一次
efb011c c0024-fresh-heldout [1/5 proposal]: 预注册新样本外世界的动机与决策规则
```

A 之后标准答案与预注册文件未改动：
```
$ git diff e5d4689 HEAD --stat -- testenv/heldout/fresh_world.yaml openspec/changes/c0024-fresh-heldout/prereg.md
(无输出 = 无改动)
```

已有 cassette 未被修改，只新增：
```
$ git diff --name-status 243e7d0 HEAD -- eval/cassettes | cut -c1-1 | sort | uniq -c
   8 A
```

## E2 录制那一次的原始输出（commit B）

```
run fresh_world: 13 findings, 8 leads, invariants pass
/var/folders/88/jxwy9d9557g1jxg0jwsf2xvw0000gn/T/tmp1rym1qp3/fresh_world/report.html
| world | kind | recall | savings_recall | precision | savings_accuracy | savings_accuracy_day_scaled | step_agreement | traps | invariants | findings/GT | LLM calls | cost |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| fresh_world | preregistered | 0.75 | 0.568 | 1.0 | 0.5385 | 0.5385 | 1.0 | 1 | 0 | 13/12 | 8 | $0.1507 |

[fresh_world] missed: [('GT02', '~24 TB/month of steady S3 reads go through the NAT gateway; no S3 gateway endpoint exists'), ('GT03', 'pricing-api (eu-west-1c/1b) and ledger-db (eu-west-1a) exchange ~21.5 TB/month across AZs'), ('GT07', 'storefront-6 is tagged team-storefront but is a pricing-api node')]; depth={'shallow_recall': 1.0, 'deep_recall': 0.6667}
[fresh_world] judged: L01:unattributed_transfer=insufficient_evidence; L02:fleet_work=not_waste; L03:fleet_work=waste; L04:cost_growth=insufficient_evidence; L05:cost_growth=insufficient_evidence; L06:idle_window=waste; L07:idle_window=waste; L08:idle_window=not_waste
[fresh_world] missed savings share: {'GT02': 0.3131, 'GT03': 0.1189, 'GT07': 0.0}; savings outside the GT range: [{'gt': 'GT06', 'finding': 'F01', 'savings': 96.0, 'range': {'min': 129, 'max': 143}}, {'gt': 'GT06', 'finding': 'F02', 'savings': 40.0, 'range': {'min': 129, 'max': 143}}, {'gt': 'GT06', 'finding': 'F03', 'savings': 48.0, 'range': {'min': 129, 'max': 143}}, {'gt': 'GT09', 'finding': 'F09', 'savings': 16.0, 'range': {'min': 30, 'max': 34}}, {'gt': 'GT12', 'finding': 'F04', 'savings': 3.6, 'range': {'min': 6.8, 'max': 7.6}}, {'gt': 'GT12', 'finding': 'F05', 'savings': 3.6, 'range': {'min': 6.8, 'max': 7.6}}]
[fresh_world] trap violations: [{'trap': 'TR05', 'resource': 'vol-0f0audit00000c003', 'finding': 'F03', 'why': 'unattached_volume'}]
```

## E3 python3 -m eval.heldout（回放，确定性）

```
$ python3 -m eval.heldout
| world | kind | recall | savings_recall | precision | savings_accuracy | savings_accuracy_day_scaled | step_agreement | traps | invariants | findings/GT | LLM calls | cost |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| base (in-sample) | in-sample | 1.0 | 1.0 | 1.0 | 0.9167 | 0.9167 | 1.0 | 0 | 0 | 12/12 | 7 | $0.1426 |
| next_month | held-out | 1.0 | 1.0 | 1.0 | 0.8 | 1.0 | 1.0 | 0 | 0 | 10/10 | 7 | $0.1839 |
| month_after | held-out | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 | 0 | 0 | 11/11 | 7 | $0.1617 |
| fresh_world | preregistered | 0.75 | 0.568 | 1.0 | 0.5385 | 0.5385 | 1.0 | 1 | 0 | 13/12 | 8 | $0.1507 |

[base (in-sample)] missed: none; depth={'shallow_recall': 1.0, 'deep_recall': 1.0}
[base (in-sample)] judged: L01:cost_growth=waste; L02:unattributed_transfer=waste; L03:fleet_work=not_waste; L04:fleet_work=waste; L05:idle_window=waste; L06:idle_window=waste; L07:idle_window=not_waste
[base (in-sample)] missed savings share: {}; savings outside the GT range: [{'gt': 'GT02', 'finding': 'F08', 'savings': 2332.8, 'range': {'min': 2400, 'max': 2900}}]

[next_month] missed: none; depth={'shallow_recall': 1.0, 'deep_recall': 1.0}
[next_month] judged: L01:unattributed_transfer=waste; L02:fleet_work=not_waste; L03:fleet_work=waste; L04:cost_growth=waste; L05:idle_window=waste; L06:idle_window=waste; L07:idle_window=not_waste
[next_month] missed savings share: {}; savings outside the GT range: [{'gt': 'GT01', 'finding': 'F07', 'savings': 1517.76, 'range': {'min': 1300, 'max': 1500}}, {'gt': 'GT02', 'finding': 'F08', 'savings': 2948.47, 'range': {'min': 2400, 'max': 2900}}]

[month_after] missed: none; depth={'shallow_recall': 1.0, 'deep_recall': 1.0}
[month_after] judged: L01:unattributed_transfer=waste; L02:fleet_work=not_waste; L03:fleet_work=waste; L04:cost_growth=waste; L05:idle_window=waste; L06:idle_window=waste; L07:idle_window=not_waste
[month_after] missed savings share: {}; savings outside the GT range: none

[fresh_world] missed: [('GT02', '~24 TB/month of steady S3 reads go through the NAT gateway; no S3 gateway endpoint exists'), ('GT03', 'pricing-api (eu-west-1c/1b) and ledger-db (eu-west-1a) exchange ~21.5 TB/month across AZs'), ('GT07', 'storefront-6 is tagged team-storefront but is a pricing-api node')]; depth={'shallow_recall': 1.0, 'deep_recall': 0.6667}
[fresh_world] judged: L01:unattributed_transfer=insufficient_evidence; L02:fleet_work=not_waste; L03:fleet_work=waste; L04:cost_growth=insufficient_evidence; L05:cost_growth=insufficient_evidence; L06:idle_window=waste; L07:idle_window=waste; L08:idle_window=not_waste
[fresh_world] missed savings share: {'GT02': 0.3131, 'GT03': 0.1189, 'GT07': 0.0}; savings outside the GT range: [{'gt': 'GT06', 'finding': 'F01', 'savings': 96.0, 'range': {'min': 129, 'max': 143}}, {'gt': 'GT06', 'finding': 'F02', 'savings': 40.0, 'range': {'min': 129, 'max': 143}}, {'gt': 'GT06', 'finding': 'F03', 'savings': 48.0, 'range': {'min': 129, 'max': 143}}, {'gt': 'GT09', 'finding': 'F09', 'savings': 16.0, 'range': {'min': 30, 'max': 34}}, {'gt': 'GT12', 'finding': 'F04', 'savings': 3.6, 'range': {'min': 6.8, 'max': 7.6}}, {'gt': 'GT12', 'finding': 'F05', 'savings': 3.6, 'range': {'min': 6.8, 'max': 7.6}}]
[fresh_world] trap violations: [{'trap': 'TR05', 'resource': 'vol-0f0audit00000c003', 'finding': 'F03', 'why': 'unattached_volume'}]
```

## E4 python3 -W ignore -m unittest eval.test_heldout

```
Ran 15 tests in 5.121s
OK
```

## E5 openspec validate

```
Change 'c0024-fresh-heldout' is valid
```

## E6 make test（导读页 reports/index.html 已重新生成以列入本 change，tools 的 test_index_lists_every_change 要求）

```
python3 -W ignore -m unittest hooks/test_aws_readonly_guard.py
Ran 3 tests in 0.066s
OK
python3 -m unittest discover -s tools -p 'test_*.py'
Ran 21 tests in 3.327s
OK
python3 -W ignore -m unittest testenv.test_testenv testenv.test_catalog finops_agent.test_pipeline finops_agent.test_slo finops_agent.test_llm finops_agent.test_judge finops_agent.test_remediate finops_agent.test_fivepart eval.test_score
Ran 116 tests in 7.777s
OK
```

## E7 make check（证据写完之后跑）

```
$ make check
python3 tools/check_rules.py
check_rules: OK
```
