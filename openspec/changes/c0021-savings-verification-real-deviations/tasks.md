## 1. 世界特性
- [x] 1.1 `testenv/world.py`：卷 `deleted`、实例 `uptime`、gp3 `iops`/`throughput`；缺省路径不变
- [x] 1.2 基础世界与既有场景的 `World.lines` sha256 前后相同
## 2. 场景链
- [x] 2.1 `verify_base.yaml`、`verify_month1.yaml`、`verify_month2.yaml`，含 scenario.expect 与 claim C01
## 3. 核实器
- [x] 3.1 场景链采集、claim、端口 37566-37599
- [x] 3.2 分层多一维（类别 x 浪费/在用），细层退回粗类别
- [x] 3.3 偏差分类、首月现金与次月现金实现率、结论；list_price 带 N 期天数；账单分解加前期结转
- [x] 3.4 设计值对账与自检清单
## 4. 文档
- [x] 4.1 重新生成 `docs/SAVINGS_VERIFICATION.md` 与 `reports/savings-verification.html`：场景链主证据 + 原链零假设对照
## 5. 测试
- [x] 5.1 合成单测：浪费/在用分层、细层退回、31 天牌价、IOPS 吞吐对账、首月现金率、前期结转
- [x] 5.2 端到端（端口 37570 起）：(a)(b)(c)(d)(e) 的分类与数值，组合实现率 < 100%，分解精确，文档确定性
## 6. 验收
- [x] 6.1 `python3 -m unittest finops_agent.test_verify_savings -v` 全绿
- [x] 6.2 `bash scripts/verify_savings.sh` 自检全部通过，两次生成逐字节相同
- [x] 6.3 `make test`、`make check` 全绿；`openspec validate c0021-savings-verification-real-deviations`
