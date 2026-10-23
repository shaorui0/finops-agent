## 1. 持续异常线索
- [x] 1.1 `collect.py`：快照加 `cost_history_daily_by_usage_type`（窗口前 92 天）
- [x] 1.2 `analyze.py`：`_persistent_cost_leads`（P25 基线，排在其他线索之后）
- [x] 1.3 `finops_agent/test_analyze.py`
- [x] 1.4 基础世界线索与 cassette 键前后逐字节相同

## 2. resolved 与 not_redetected
- [x] 2.1 `slo.py::diff_state` 查成本侧证据，state 记 evidence 与 not_redetected
- [x] 2.2 `finops_agent/test_slo.py`
- [x] 2.3 `scripts/rot_demo.sh` 链路不变；`config/alerts/finops.rules.yml` 只读检查

## 3. 样本外
- [x] 3.1 录制两个样本外世界新线索所需的 cassette（预算 ≤ 10 次）
- [x] 3.2 `python3 -m eval.heldout`，更新 `eval/test_heldout.py`
- [x] 3.3 `eval/EXPERIMENTS.md` 新节：样本外已被污染的声明

## 4. 文档
- [x] 4.1 `docs/FINOPS_SLO.md` Rot 一节

## 5. 验收
- [x] 5.1 `make eval AWS_PORT=39566 PROM_PORT=39567 RUN=t20`：recall 1.0、savings_recall 1.0、gate 通过
- [x] 5.2 `python3 -m unittest finops_agent.test_analyze finops_agent.test_slo eval.test_heldout`
- [x] 5.3 `make test`、`make check`；`openspec validate c0023-persistent-anomaly-and-resolution`
- [x] 5.4 evidence.md、HTML 报告、博客笔记
