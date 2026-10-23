# 0018 savings verification 笔记

- resolved 不等于省钱。agent 只知道 key 不见了。要证明省钱，得拿下一期的账单去对：被处理资源的反事实成本减实际成本。
- 两张发票相减是错的方法。10 月到 11 月的真实演示里：三项清理省 $76.05，账单却涨了 $474.93，因为 10 月多一天（+$290.43）和 NAT 用量上涨（+$247.75）。只看总账单会得出「清理没效果」。
- 对照组必须分层。全体对照的漂移系数是 1.028，被 NAT 拉高；卷所在的 EBS 层是 1.000。不分层会把卷的节省多算 2.8%。
- agent 的 billed 型预测是按分析周期的天数外推的（analyze.py 里 cost * days / res_days）：10 月的预测是 16.53，30 天的实现是 16.00。这不是错误，是口径。先把预测换到标准月再比，实现率才是 100%。
- 实现率 100% 是零结果，不是方法的功劳：世界用同一张价格表生成账单和预测依据。证据价值在于流水线没凭空制造偏差，以及方法在合成案例里能给出正确的偏差（用量降、涨、中途创建、承诺吸收）。
- gp2 改 gp3 在 10 月完全兑现（实现 $20.00），11 月被 terraform 回退归零。一次 resolved 不是终点，要在 N+2 期再测一次。
- 账单分解用 Fraction，等式 sum == delta 精确成立。浮点下只能 assertAlmostEqual，不能证明没有漏项。
- 踩坑一：resolved 列表来自集合差，顺序随哈希种子变，文档两次生成不一致。确定性测试（采集两次比对）抓到的，修法是按 key 排序。
- 踩坑二：boto3 的 get_cost_and_usage_with_resources 要求必带 Filter（真实 API 也如此），资源级请求还限 14 天，要分段。
- 场景里没有中途删除、没有承诺覆盖的 resolved 项，这两个检测只有合成单测。要补样例需要改 testenv，这个 change 不能碰。
PROGRESS_ROW: | c0018-savings-verification | 2026-10-24 | 用 Cost Explorer 核实 resolved finding 的真实节省：反事实基线 + 分层对照组 + 保持测量 + 精确账单分解，生成中文文档与 HTML | 两张发票相减会得出「清理没效果」：三项清理省 $76.05，账单涨 $474.93 | [报告](reports/0018-savings-verification.html) · [笔记](notes/blog/0018-savings-verification.md) · [文档](docs/SAVINGS_VERIFICATION.md) |
