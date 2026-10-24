## 1. 预注册（commit A）
- [x] 1.1 `testenv/heldout/fresh_world.yaml`：完整世界 + ground_truth（五段式）
- [x] 1.2 `openspec/changes/c0024-fresh-heldout/prereg.md`：评估命令、指标、决策规则
- [x] 1.3 提交 A，之后才允许对该世界运行 agent 或 judge

## 2. 录制与评估（commit B）
- [x] 2.1 `eval/heldout.py` 加入该世界（kind=preregistered）；`FINOPS_LLM_MODE=record`，预算 ≤ 12 次调用，只新增 cassette
- [x] 2.2 运行一次评估，结果落盘（原始 JSON 与输出）

## 3. 结果与分析（commit C）
- [x] 3.1 `eval/test_heldout.py` 钉住新数字
- [x] 3.2 `eval/EXPERIMENTS.md` 追加「§7 预注册的新样本外世界」

## 4. 验收
- [x] 4.1 `python3 -m eval.heldout` 打印新世界一行；`python3 -W ignore -m unittest eval.test_heldout` OK
- [x] 4.2 `make test`、`make check`、`openspec validate c0024-fresh-heldout`
- [x] 4.3 evidence.md、HTML 报告、博客笔记
