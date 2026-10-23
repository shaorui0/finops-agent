## 取舍

- **处理器放哪**：`remediate.py` 只认检测器类型，判断层的类型（nat_path_cost 等）会落进 `skipped`。该文件不在本 change 范围内，所以在 `fivepart.py` 定义 `EXTRA_HANDLERS`，`register_handlers()` 用 `setdefault` 注入 `remediate.HANDLERS`，`build_plans` 仍是 remediate 的同一个函数。
- **status 只用非 LLM 证据**：判断层 finding 的 `hops` 是模型写的文本，不进 status；evidence 里 source 不是 `llm` 的行是代码算的，status 用观察类、diff 用 `computed` 类。
- **不碰判断 prompt**：`owner` 只加在 `Finding`，`Lead` 与 `judge/` 不动，cassette 的 sha256(model+prompt) 不变。
- **rot-demo 为什么 `FINOPS_NO_JUDGE=1`**：`scripts/rot_demo.sh`（不在本 change 的范围）跑 next_month、month_after 两个世界，判断层的 prompt 在那两个世界里没有 cassette，回放会 `CassetteMissing`；录制 cassette 是另一个有意识的动作。腐烂检测本来就只靠确定性检测器，关掉判断层演示结果不变。
- **finding 的 owner 是 tag 所写**：misattributed_tags 的 owner 是 tag 里写的 team-web，实际使用方是启动模板所属团队；建议文本里写明两边都要通知。
