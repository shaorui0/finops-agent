## 1. owner 与预防
- [x] 1.1 `analyze.py`：`Finding.owner`、`owners_by_resource`、`assign_owners`
- [x] 1.2 `prevention.py`：类型 -> 控制、告警、节奏

## 2. 五段式与计划
- [x] 2.1 `fivepart.py`：status/spec/diff/runbook/prevention，判断层类型的处置处理器
- [x] 2.2 `__main__.py`：每次运行写 `plans.json`、`fivepart.json`，`FINOPS_NO_JUDGE`
- [x] 2.3 `report.py`：五段式卡片、处置计划总览

## 3. 测试与 Makefile
- [x] 3.1 `test_fivepart.py`、`test_pipeline.py` 增补
- [x] 3.2 `Makefile`：`rot-demo`，`make test` 追加三个套件

## 4. 验收
- [x] 4.1 `make eval AWS_PORT=32566 PROM_PORT=32990 RUN=t7`：recall 与 savings_recall 为 1.0，gates pass，全部 llm 调用 mode=replay
- [x] 4.2 python 检查 `runs/t7/plans.json`：每个节省大于 0 的 finding 有带 reversal_cost 与 rollback 的计划
- [x] 4.3 `make rot-demo`：三次运行里 resolved、regressed、new 都至少 1 个
- [x] 4.4 `make test`、`make check` 全绿
- [x] 4.5 `reports/0016-demo-run.html` 浏览器检查五段式
