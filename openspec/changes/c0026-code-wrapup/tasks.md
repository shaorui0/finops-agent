## 1. 实现
- [x] 1.1 `slo.py` / `__main__.py`：显式传快照，删除模块级暂存；`test_slo.py` 覆盖
- [x] 1.2 `report.py` 显示 not_redetected；`test_pipeline.py` 覆盖
- [x] 1.3 `eval/heldout.py` 默认端口 47500-47599
- [x] 1.4 `check_rules.py` D11 / D16（`--docs`），`test_check_rules.py` 通过/失败各一个 fixture
- [x] 1.5 Makefile：`test` 发现全部测试，`check-docs`，`check` 受 `DOCS_CHECK` 控制；ci.yml 同

## 2. 验收
- [x] 2.1 `make test`、`make check`、`make check-docs`（在 main 上记录失败清单）
- [x] 2.2 `make eval AWS_PORT=44566 PROM_PORT=44567 RUN=t22` 前后一致；`python3 -m eval.heldout` 前后一致；rot_demo 前后一致
- [x] 2.3 evidence.md、HTML 报告、博客笔记
