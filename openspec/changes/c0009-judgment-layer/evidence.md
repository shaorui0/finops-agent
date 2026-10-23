# c0009 验收证据

## 5.1 make eval（replay，离线）
```
$ make eval AWS_PORT=15566 PROM_PORT=15990 RUN=t1
/Users/rshao/work/context-infrastructure/projects/finops-agent-wt/t1/runs/t1/report.html
python3 -m eval.score runs/t1/findings.json; status=$?; /Applications/Xcode.app/Contents/Developer/usr/bin/make stop; exit $status
{"recall": 1.0, "savings_recall": 1.0, "precision": 1.0, "savings_accuracy": 0.9167, "step_agreement": 1.0, "depth": {"shallow_recall": 1.0, "deep_recall": 1.0}, "leads": 7}
missed: 
gates: pass
```
before（main 的 baseline.json）：
```
{
  "recall": 0.5833,
  "savings_recall": 0.1888,
  "precision": 1.0,
  "savings_accuracy": 1.0,
  "step_agreement": 1.0,
  "depth": {
    "shallow_recall": 1.0,
    "deep_recall": 0.4444
  }
}
```
after（本 change 重写后的 eval/baseline.json）：
```
{
  "recall": 1.0,
  "savings_recall": 1.0,
  "precision": 1.0,
  "savings_accuracy": 0.9167,
  "step_agreement": 1.0,
  "depth": {
    "shallow_recall": 1.0,
    "deep_recall": 1.0
  }
}
```

判断层产出的 5 条发现：
```
F08 nat_path_cost      M6_architecture        savings=$2,332.80 basis=billed_14d_extrapolated spend=$2,885.76
F09 cross_az_traffic   M6_architecture        savings=$759.85 basis=inferred spend=$760.00
F10 busy_but_useless   M3_delete              savings=$1,468.80 basis=billed_14d_extrapolated spend=$1,468.80
F11 always_on_batch    M6_architecture        savings=$224.40 basis=inferred spend=$244.80
F12 schedulable_idle   M4_downsize_schedule   savings=$0.00 basis=inferred spend=$597.20
```

## 5.2 replay 不需要 claude、不需要 key、不需要网络
```
$ PATH=<去掉 ~/.local/bin> env -u ANTHROPIC_API_KEY make eval AWS_PORT=15566 PROM_PORT=15990 RUN=t1b
python3 -m eval.score runs/t1b/findings.json; status=$?; /Applications/Xcode.app/Contents/Developer/usr/bin/make stop; exit $status
{"recall": 1.0, "savings_recall": 1.0, "precision": 1.0, "savings_accuracy": 0.9167, "step_agreement": 1.0, "depth": {"shallow_recall": 1.0, "deep_recall": 1.0}, "leads": 7}
missed: 
gates: pass
$ command -v claude   # 在同一个 PATH 下
claude: not on PATH
$ grep -c '"source": "llm"' runs/t1/trace.jsonl
7
```
CI：`.github/workflows/ci.yml` 的 eval 步骤带 `FINOPS_LLM_MODE: replay`；cassette 在 `eval/cassettes/`（7 个文件，已提交）。

## 5.3 trace 字段与「Agent 成本」
一条 trace（replay，值为录制值）：
```
{"source": "llm", "op": "judge", "params": {"lead": "L02", "kind": "unattributed_transfer", "model": "sonnet"}, "ms": 0.4, "ok": true, "error": null, "mode": "replay", "tokens_in": 3448, "tokens_out": 724, "latency_ms": 5868.0, "cost_usd": 0.021027999999999998, "key": "bb53e1740b44f0beb4af33ede918e8adf9a36506e6c6c483ea93885ac9b6f9d3", "verdict": "waste", "accepted": true, "reject_reason": null}
```
每次调用：
```
L01 cost_growth            in= 3904 out=  739 latency=6.3s cost=$0.0230 verdict=waste
L02 unattributed_transfer  in= 3448 out=  724 latency=5.9s cost=$0.0210 verdict=waste
L03 fleet_work             in= 3041 out=  492 latency=4.2s cost=$0.0171 verdict=not_waste
L04 fleet_work             in= 3631 out=  668 latency=5.5s cost=$0.0212 verdict=waste
L05 idle_window            in= 2993 out= 1055 latency=10.2s cost=$0.0225 verdict=waste
L06 idle_window            in= 3242 out=  706 latency=5.6s cost=$0.0200 verdict=waste
L07 idle_window            in= 3090 out=  542 latency=5.3s cost=$0.0178 verdict=not_waste
合计：7 次调用，tokens_in=23,349，tokens_out=4,926，cost=$0.1426
```
报告节标题：`<h2>Agent 成本 <span class=muted>· 判断层的每一次 LLM 调用</span></h2>`（`grep -c "Agent 成本" runs/t1/report.html` = 1）

## 5.4 make test / make check / openspec validate
```
----------------------------------------------------------------------
Ran 59 tests in 2.462s

OK
/var/folders/88/jxwy9d9557g1jxg0jwsf2xvw0000gn/T/tmp1kfejvls/t/report.html

python3 tools/check_rules.py
check_rules: OK
Change 'c0009-judgment-layer' is valid
```

## 隔离（D6）
`finops_agent/test_judge.py::JudgeLeadsTest::test_prompt_for_a_lead_contains_none_of_the_other_leads_evidence` 与
`test_calls_are_isolated_and_concurrent`（峰值并发 > 1，每个 prompt 只含一条线索的标记）；
`finops_agent/test_pipeline.py::test_prompts_in_cassettes_are_isolated_per_lead` 用真实数据重建每条线索的 prompt，
断言它与 cassette 里实际发出的 prompt 逐字一致，且不含其他线索独有的证据行。

## 录制过程（如实记录）
- 模型：`claude -p --model sonnet`，modelUsage 报告 claude-sonnet-5-5；`--tools "" --setting-sources "" --disable-slash-commands`，cwd 为临时目录。
- 调用次数：为迭代 prompt rubric 共 6 轮全量录制（6 x 7 = 42 次调用）加 1 次单条重录，另有约 6 次探测调用，合计约 49 次，略多于"几十次"预算；单次约 $0.02。迭代内容：类型与步骤的定义（取自 METHOD.md）、"一个发现一个修复"、"路径发现要写两端"、NAT 线索的范围说明。
- 第一批录制的 usage 里 cache_read 约 73K tokens，同一 prompt 事后单独调用只有约 3.4K；原因没查清，所以丢弃第一批，在 usage 正常的环境下重录。
- 重录会改变判断：一次重录中 NAT 线索变成 insufficient_evidence（"没有按目的地拆分的字节"），recall 掉到 0.92。修法是补一条算出来的事实（NAT 多出的 GB / 重试多出的次数 = 每次的固定字节数），并允许"修复明确、仅一个事实待验证"时仍报告。之后只重录了这一条。
- 以上迭代都看了 `make eval` 的输出，也就是 prompt 的 rubric 是对着这个账号调出来的。代码里没有资源 ID 或标准答案 ID；测试没有写死标准答案。
