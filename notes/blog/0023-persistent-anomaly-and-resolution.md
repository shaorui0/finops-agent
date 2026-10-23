# 0023 持续异常与 resolved 语义

- 样本内 1.0 是调出来的，样本外第一个缺口来自检测器不是 LLM：跳变检测只比窗口内前 3 天和后 7 天，异常在窗口开始前就在，就看不见。修法是给它一段更早的历史当基线。
- 基线用 P25 不用中位数。month_after 的 92 天历史里异常已占 58 天，中位数会把异常当成正常。这个选择是看过样本外才做的，所以要写明。
- 新线索排在所有旧线索之后，旧线索的 id 和文字不动，基础世界 7 个 cassette 键前后完全一致，零重录。样本外世界因为 idle_window 线索编号顺延，多录了 6 次（$0.1845）。
- 反直觉：修好之后 next_month 的 savings_accuracy 从 0.8889 掉到 0.8。不是退步，是 GT02 以前没找到所以不计入，现在找到了才暴露金额超区间 1.7%。
- 新线索的取证器仍按窗口内 head/tail 算「多出的部分」，持续异常里它约等于 0（$-0.00），最后选的是整条路径月化。找到了，金额口径是凑巧对的，取证器要单独改。
- 漏检被记成修复，比漏检本身更糟：它会让 regressed 告警和 remediation 统计一起失真。resolved 要有成本侧证据（资源没了、属性变了、成本掉了），否则叫 not_redetected。
- not_redetected 不进 resolved 记录。否则它之后重新出现会被报成 regressed，把检测器抖动当成腐烂。
- 关掉 judge 跑第二期，judge 产出的 5 条 finding 全是 not_redetected，而不是 resolved；旧代码会报 5 条已解决。
- 看过样本外结果之后改了 agent，这两个世界对这类失败就不再是样本外。数字回到 1.0 只说明修复有效，要证明泛化得有一个改动之前冻结的新世界。
- 坑：`__main__.py` 不在本 change 范围内，diff_state 拿不到快照，只好让 compute_slis 把快照暂存在模块变量里。后续应该直接传参。
- 坑：heldout 的端口范围写死 31568-31599，并行跑时会撞，加了环境变量 FINOPS_HELDOUT_PORTS。

PROGRESS_ROW: | c0023-persistent-anomaly-and-resolution | 10-24 | 窗口前就存在的费用异常用前 92 天 P25 基线出线索；消失的 finding 分 resolved / not_redetected；样本外 recall 0.9/0.9091 -> 1.0（已被污染） | 漏检被记成修复比漏检本身更糟；对着样本外失败修完，那两个世界就不再是样本外 | [报告](reports/0023-persistent-anomaly-and-resolution.html) · [笔记](notes/blog/0023-persistent-anomaly-and-resolution.md) |
