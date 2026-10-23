# 0014 testenv-catalog 笔记

- 标准答案只有 id、跳数、区间时，人读不出「现在什么样、该什么样、差在哪、怎么做、怎么不再发生」。五段式（status、spec、diff、runbook、prevention）把一条 finding 变成一张能执行的工单。
- 陷阱也要五段。spec 写成「为什么现状就是规格」，diff 写「无差距」，runbook 的处置是「不动」。这样陷阱不再是一句 why，而是一份拒绝动手的理由。
- 散文里的数字一律用占位符，渲染时对着 `testenv.world.load()` 算。好处是改一个价格，页面和文字同时更新；测试里扫 `$数字` 字面量，手写金额直接失败。
- 占位符要能选世界：`@base`、`@next`。已解决的卷在场景世界里不存在，得回基础世界取它当时的月费。
- 腐化时间线靠 `scenario.expect` 的 key 反推：base 里只要在 next 的 resolved 或 persisting 中就是 open。不用另存一份状态表。
- 预防里引用告警名用 `alert:Name` 标记，测试去 `finops.rules.yml` 对表。没有对应告警的（TR03、GT12 的批处理）如实写「无直接告警」，不凑数。
- 反直觉：GT11 的预防是「先改 IaC 再改现网」。month_after 的回归就是代码从没改成 gp3，机制缺口在 IaC，不在清理动作。
- 坑：headless Chrome 窗口最窄约 500px，390 截图会被裁，真机宽度要靠 `overflow-x:auto` 容器保证。表格里的 id 用 `word-break:break-all` 会逐字符换行，要给表内 code 单独设 nowrap。

PROGRESS_ROW: | c0014-testenv-catalog | 10-24 | 测试账号 12 个发现、4 个陷阱、2 个场景的全部期望补齐 现状→期望→差异→处置→预防 五段，数字由成本模型计算；`python3 -m testenv.catalog` 生成自包含目录页 | 数字用占位符对着 world 计算，测试扫字面量金额，改价格页面自动跟着变 | [报告](reports/0014-testenv-catalog.html) · [笔记](notes/blog/0014-testenv-catalog.md) |
