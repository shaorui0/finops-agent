## 1. 数字落地
- [x] 1.1 `validate.py`：规则 G1–G6（紧贴中文的数字、小整数、untrusted 不算证据、日期/ID 剔除）
- [x] 1.2 `finops_agent/test_judge_grounding.py`：编造金额被拒、trace 记原因
- [x] 1.3 `make eval` 回放：7 条既有判断全部通过校验，指标与基线一致

## 2. 对抗套件
- [x] 2.1 `testenv/scenarios/adversarial_*.yaml`：9 个覆盖层（8 个注入变体 + 1 个数字诱饵）
- [x] 2.2 `eval/test_adversarial.py`（replay）；`FINOPS_LLM_MODE=record` 录制所需 cassette（预算内）

## 3. 样本外
- [x] 3.1 `eval/heldout.py`（`next_month`、`month_after`，按 `scenario.expect` 打分，样本内/外分开）
- [x] 3.2 `eval/test_heldout.py`；录制两个世界的 cassette

## 4. 实验记录
- [x] 4.1 `eval/EXPERIMENTS.md`（设置、c0009 迭代史、样本外、对抗、分析）

## 5. 验收
- [x] 5.1 `python3 -m unittest eval.test_adversarial -v`
- [x] 5.2 `make eval AWS_PORT=31566 PROM_PORT=31567 RUN=t2`：recall 1.0、savings_recall 1.0、gate 通过
- [x] 5.3 `make test`、`make check` 全绿；`openspec validate c0015-adversarial-and-experiments`
- [x] 5.4 evidence.md、HTML 报告、博客笔记
