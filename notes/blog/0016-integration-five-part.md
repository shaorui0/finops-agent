- 五段式的 status/spec/diff 在 agent 运行时要「代码算」，不能抄 LLM 的话。办法是按 evidence 的 source 分流：观察类（cost_explorer、ec2、metrics）进 status，`computed` 进 diff，`llm` 一律不进。判断层 finding 的 hops 也是模型写的，所以 status 只用 evidence。
- 判断层产出的 finding 在 remediate 里没有处理器，会静默进 `skipped`。不改 remediate.py，在新模块里定义处理器再 `setdefault` 注入它的 HANDLERS：同一个 build_plans，覆盖面补齐。测试断言 `skipped == []`，以后再加类型忘了写处理器会当场失败。
- owner 的坑：ASG 自己没有 tag，owner 要从成员实例推；misattributed_tags 的 owner 是 tag 里写的那个团队，恰好是错的那个。建议里要写「两边都通知」。
- 预防表的告警名对 `finops.rules.yml` 做测试，和 c0014 的 `alert:Name` 做法一致。有控制但没有告警的类型照样要挂一个已有告警（如 FinOpsRegression），不造不存在的名字。
- 反直觉：加 `owner` 到 `Finding` 不会动 cassette，因为 prompt 只由 `Lead` 渲染。验证办法就是 eval 全部 replay 且不报 CassetteMissing，比读代码可靠。
- 坑：`make rot-demo` 在 main 上本来就是坏的。判断层合入后，next_month 世界的 prompt 没有 cassette，回放直接抛 CassetteMissing。用 `FINOPS_NO_JUDGE=1` 绕开，腐烂检测只靠确定性检测器，结果不变；真要带判断层演示，得有意识地录一次。
- macOS 的 `sed -i` 要带空串参数，改文件用 python 更稳。

PROGRESS_ROW: | c0016-integration-five-part | 10-24 | 每次运行写 plans.json（含判断层 finding）与 fivepart.json，报告每个 finding 卡片是 现状/期望/差异/处置/预防 五段，finding 带 owner；`make rot-demo` 与新套件进 `make test` | status/spec/diff 按 evidence 的 source 分流，LLM 文本不进数字；remediate 没有的类型在新模块注入处理器，测试断言 skipped 为空 | [报告](reports/0016-integration-five-part.html) · [笔记](notes/blog/0016-integration-five-part.md) |
