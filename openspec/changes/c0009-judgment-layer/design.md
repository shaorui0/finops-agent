## 上下文

一条线索要变成发现，需要跨源取数、算数、再判断。让 LLM 全做会有两个问题：算错数字（FA03），以及证据混在一起互相污染（FA11）。

## 决定

**1. 取证和判断分开。** `gather.py` 按线索种类写死取证逻辑：查快照和 Prometheus，算出成本、比率、GB、候选节省。LLM 看到的是一份带编号的证据（E1..En）和一组候选节省（key + 数值 + 口径）。

**2. LLM 只做选择。** 输出严格 JSON：verdict、type、method_step、title、resources、hops、evidence、savings_choice、basis、reasoning。节省金额和口径由代码按 savings_choice 填，模型写的文字里的数字必须在证据里出现（1% 容差），否则整条判断被拒。拒绝不修补，记进 trace 和报告。

**3. 每条线索一次独立调用。** prompt 里只有这条线索的证据。并发用线程池，上限 4。隔离由单测断言，不靠自觉。

**4. record / replay。** cassette 键是 sha256(model + prompt)，所以任何改变 prompt 的改动都会让旧 cassette 失效，replay 报错而不是悄悄回退。这是有意的：它强迫 prompt 变更伴随一次重新录制和一次 eval。录制用 `claude -p --tools "" --setting-sources ""` 在临时目录里跑，不带项目 CLAUDE.md，一次调用约 $0.01 到 $0.02。

**5. 新线索。** 一部分漏报在现有线索里根本没有对应物（dev 调度、夜间 ETL）。`idle_window_leads` 从按小时的 CPU 里找出忙时占比低于 50% 的非 ASG 实例，相同形状的分成一组。

**6. 护栏。** 带 `dr` / `keep` 等意图 tag 的资源被判浪费时，代码直接拒绝。这是对 FA07 的回应：agent 是不可靠组件，模型之外要有一道确定性的闸。tag 和 Name 是不可信输入，只在 `<untrusted_metadata>` 块里出现。

**7. Savings Plan 对节省的改写。** idle_window 取证器同时给出 `idle_hours_cost`（不考虑承诺）和 `net_after_commitment`（扣除未用承诺后的现金节省）。被覆盖的机型族，未用承诺大于释放的花费时，后者为 0。

## 取舍

- 取证器是按线索种类写的，不是通用的。新增一种线索要加一个取证器。换来的是每个数字都能追溯到一条查询。
- 并发度 4 是保守值；七条线索时总延迟约等于最慢的两次调用。
- 模型版本固定在 `sonnet` 别名。别名漂移会改变回答但不改变 cassette 键，所以键里放的是别名而不是日期；本次录制时 `claude -p` 的 modelUsage 报告的模型是 claude-sonnet-5-5，记在 evidence.md。

## 风险

- prompt 与 eval 的耦合：prompt 的 rubric 是为这个账号迭代出来的，必须在报告里如实写迭代次数，不能当成泛化证据。
- 取证器的阈值（忙时 CPU 10%、忙时占比 50%）是常量，换账号要重新看。
