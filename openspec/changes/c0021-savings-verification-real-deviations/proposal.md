## Why

c0018 核实了 4 条 resolved，实现率全是 100%。原因不在方法：世界用同一张价格表同时生成预测依据的成本行和账单，预测必然对上。按天折算、承诺吸收、对照组校正只在合成单测里被验证，场景数据里一个真实偏差都没有。维护者要的是「实验数据，为什么对，怎么验证真的省钱了，对应的数据、分析、结论等，要有细节」。一个全是 100% 的结果回答不了「核实器遇到偏差会怎样」。

## What Changes

- 新增一条场景链 `testenv/scenarios/verify_base.yaml` -> `verify_month1.yaml` -> `verify_month2.yaml`（叠在基础世界上，不改 `next_month.yaml`、`month_after.yaml`、`adversarial_*`），刻意制造四类真实偏差：期中删除（按天折算）、dev 启停被 Savings Plan 吸收（承诺吸收）、gp2 改 gp3 同期用量增长 30%（对照组校正）、gp2 改 gp3 保留 IOPS 与吞吐（预测口径差），外加一个无偏差的对照项。
- `testenv/world.py` 新增三个可选字段：卷 `deleted`（期中删除日）、实例 `uptime`（启停比例）、gp3 卷 `iops`/`throughput`（超出免费额度另计）。基础世界与既有场景的 `World.lines` 逐字节不变（sha256 前后相同）。
- `finops_agent/verify_savings.py`：新增场景链采集（`chain=` 参数）；场景声明的 claim（C01，GT05 的按需价纸面节省）进入核实但不混入 agent 的成绩；对照组分层多一维（类别 x 是否浪费类）；偏差按因分类（承诺吸收、用量漂移、预测口径差、按天折算）并给出首月现金实现率、次月现金实现率、结论；账单分解新增「前期结转」项；list_price 预测同样带 N 期天数，换算标准月；设计值对账（不看账单，从世界规格算应有的节省）。
- 重新生成 `docs/SAVINGS_VERIFICATION.md` 与 `reports/savings-verification.html`：场景链作主证据（A 部分），原链保留为「零假设对照」（B 部分），解释为什么那里的 100% 是预期的。
- 端口改用 37566-37599（`scripts/verify_savings.sh` 与测试）。

## Capabilities

### Modified Capabilities
- `savings-verification`：偏差分类、首月现金与次月现金实现率、claim、场景链、设计值对账。

## Impact

改 `testenv/world.py`（可选字段，默认行为不变）、`finops_agent/verify_savings.py`、其测试、`scripts/verify_savings.sh`、生成的文档与报告。新增三个场景文件。不改 agent 的检测器、判断层、标准答案、Makefile、README。不涉及 AWS 写操作（测试服务器只读），不需要人工 gate，也不需要回滚。没有新增 LLM 调用（全部 `--no-judge`，0 条录制）。
