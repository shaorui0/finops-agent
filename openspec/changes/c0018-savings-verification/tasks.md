## 1. 采集
- [x] 1.1 每个周期起服务器、跑 agent（`--no-judge`，共用 state）、用 boto3 查资源级日度与用量类型级月度 Cost Explorer
## 2. 方法
- [x] 2.1 配对 resolved key 与 N 期 finding；日均成本基线；分层对照组漂移；反事实与实现率
- [x] 2.2 偏差分类：日历天数、按天折算、对照组校正、预测口径、承诺吸收、资源未对上
- [x] 2.3 N+2 期保持测量（gp3 兑现后丢失）
- [x] 2.4 账单精确分解（Fraction）
- [x] 2.5 独立价格复算与自检清单
## 3. 输出
- [x] 3.1 `docs/SAVINGS_VERIFICATION.md`（中文，生成）与 `reports/savings-verification.html`
- [x] 3.2 `scripts/verify_savings.sh`
## 4. 测试
- [x] 4.1 分解精确闭合；gp3 兑现后丢失；用量漂移校正（涨、跌两个方向）；按天折算；承诺吸收
- [x] 4.2 真实服务器端到端（端口 34590 起）：resolved 集合与 scenario.expect 一致，文档确定性
## 5. 验收
- [x] 5.1 `python3 -m unittest finops_agent.test_verify_savings -v` 全绿
- [x] 5.2 `bash scripts/verify_savings.sh` 生成文档，自检清单全部通过，两次生成逐字节相同
- [x] 5.3 `make test`、`make check` 全绿；`openspec validate c0018-savings-verification`
