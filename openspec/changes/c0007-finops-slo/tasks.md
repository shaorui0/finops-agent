## 1. SLO
- [x] 1.1 `config/finops_slo.yaml`（8 SLI、预算、燃烧）
- [x] 1.2 `finops_agent/slo.py`（计算、判定、跨运行状态、导出）+ 接入 CLI 与报告
- [x] 1.3 `finops_agent/test_slo.py`

## 2. 告警
- [x] 2.1 `config/alerts/finops.rules.yml`（11 条）
- [x] 2.2 `config/alerts/finops.rules.test.yml`（promtool 单测）

## 3. 运维接线
- [x] 3.1 `make inspect`、`make alerts-test`、`ops/crontab.example`、CI 增加 alerts-test

## 4. 文档
- [x] 4.1 `docs/FINOPS_SLO.md`；README、WORKSPACE、REQUIREMENTS 覆盖面矩阵

## 5. 验收
- [x] 5.1 `make test`、`make check`、`make alerts-test` 全绿
- [x] 5.2 两次运行演示 rot 检测；`promtool check metrics` 通过
- [x] 5.3 `make eval` 不回退
- [x] 5.4 `openspec validate c0007-finops-slo`；推送后 CI 绿
