# 0009-judgment-layer 博客笔记

- 确定性检测器 + LLM 的分工线：代码取证、算数、列候选；LLM 只做"选"。节省金额由代码按 `savings_choice` 填，模型文字里的数字必须能在证据里找到，否则整条判断被拒。拒绝不修补，记 trace。
- eval 从 recall 0.58 / deep 0.44 / savings 0.19 到 1.0 / 1.0 / 1.0。别当成泛化证据：prompt 的 rubric 是对着这个账号迭代出来的（6 轮全量录制），代码和测试里没有任何资源 ID，但"模型被调到会答这个账号"是事实。
- cassette 键是 sha256(model + prompt)，所以改 prompt 就会让所有旧 cassette 失效，replay 直接报错而不是悄悄回退。这是特性：prompt 变更必须伴随一次重录和一次 eval。
- 重录会改判断。同样的 prompt 重录一次，NAT 线索从"浪费"变成"证据不足"（理由合理：没有按目的地拆分的字节）。LLM 的方差只在录制时出现，replay 之后固定。所以 eval 的稳定性来自 cassette，不来自模型。
- 修复方法不是改 prompt 放水，而是多算一个事实：NAT 多出的 GB 除以重试多出的次数，得到每次固定的字节数。证据变强，判断自己就稳了。
- 隔离要靠测试断言，不靠自觉。用真实数据重建每条线索的 prompt，和 cassette 里实际发出的 prompt 逐字比，再断言不含其他线索独有的证据行。
- 第一批录制的 usage 里 cache_read 有 73K tokens，同一个 prompt 事后单独调只有 3.4K，原因没查清。丢掉重录。教训：trace 里的 tokens 值要有量级的合理性检查，否则成本报表是错的而没人发现。
- `claude -p --output-format json` 的字段：`result`、`usage.{input_tokens,cache_creation_input_tokens,cache_read_input_tokens,output_tokens}`、`total_cost_usd`、`duration_ms`、`modelUsage`。加 `--tools "" --setting-sources "" --disable-slash-commands` 后单次约 3K tokens、$0.02；不加的话光系统提示就几万 tokens、约 $0.1。
- tag 里的 prompt injection 靠两层：prompt 里用 `<untrusted_metadata>` 块声明那是数据；代码里不让模型的文字决定是否"跳过"。模型自己在 reasoning 里指出了那条 Name 是第三方写入的数据，没有影响判断。
- 意图 tag 护栏：带 `dr` 等 tag 的资源被判浪费，代码直接拒绝。模型这次都答对了，护栏没触发，但它存在是因为 FA07：模型之外要有确定性的闸。
- dev 调度那条的答案是 0。取证器同时给出 `idle_hours_cost` 和 `net_after_commitment`，被覆盖的机型族、未用承诺大于释放的花费时后者为 0。模型选了后者。这条发现的价值是"不要做"，节省 recall 里它占的权重是中点金额。
- 坑：`make eval` 的 `demo` 失败时 `make stop` 不会执行，测试服务器会留在后台占端口；管道里接 `tail` 会因为后台进程持有 stdout 而挂住。Makefile 的 `export X ?= v   # 注释` 会把注释前的空格带进变量值。
- 线索种类写死了取证器，换来每个数字都能追溯到一条查询；代价是新线索要新写取证器。
PROGRESS_ROW: | c0009-judgment-layer | 10-24 | 判断层：LLM 逐条回答线索（代码取证并算数，模型只选候选，record/replay cassette），新增空闲时段线索，报告加「Agent 成本」 | 代码算数、模型只选：eval 深度 recall 0.44 → 1.0，且重录会改判断，稳定性来自 cassette 而不是模型 | [报告](reports/0009-judgment-layer.html) · [笔记](notes/blog/0009-judgment-layer.md) |
