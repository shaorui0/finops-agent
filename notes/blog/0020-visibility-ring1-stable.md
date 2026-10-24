- 单次 0.91 是运气：c0017 重采样 0.82 和 0.64。要看均值，N=5 起步，还要报 min。
- 让 LLM 猜 metric 名正则是错的任务：它在没看系统时只能凭惯例写，写出来的有些根本不存在。改成让它只说「需要什么量、按什么维度、用哪些词描述」，名字交给 ring 2 去在线上目录里找。
- 这不违反「目标优先」：ring 1 仍然一个服务器指标名都没见过，ring 2 才是看系统的地方。
- ring 2 的发现是确定性代码：metadata 的 HELP 文本 + 指标名 + scope 标签，至少命中 2 个词，且不能只靠「utilization / percent / bytes」这类泛词。没有这条泛词规则，内存需求会被 CPU 指标顶替，planted gap 就被盖住了。
- ring 4 改成 need 级判断：合并 SLI 里一个 need 缺，不再让整个 SLI 变 missing。派生缺口表从 2 covered / 0 partial / 5 missing 变成 3 / 5 / 0，但 partial 里是真实的 scope 覆盖不全，别读成「变好了」。
- 评审路径用默认参数保持原样，`visibility.json` 的 gaps 前后 cmp 一致。新功能全部走可选参数，这是最省事的回归保护。
- 结果：N=5 均值 0.964，min 0.91；N=10 复核同样 0.964。prompt 只改了一轮。
- 反直觉：尺子换了。旧 overlap 比的是「LLM 写的正则」，新 overlap 比的是「ring 2 发现的候选名」，0.79 到 0.96 里有一部分是我写的 `discover` 的功劳，不是 LLM 变聪明了。
- 坑：evidence 里 Markdown 反引号写在未加引号的 heredoc 里，shell 当命令执行了一次 `make eval`，在默认端口起了服务器。heredoc 一律加引号。
- 10 次调用，约 0.31 USD。

PROGRESS_ROW: | c0020-visibility-ring1-stable | 10-24 | ring 1 只说词不写名，ring 2 按 HELP/name/scope 确定性发现候选名，ring 4 need 级混合状态；`--samples N` 评估 | N=5 overlap 均值 0.964（min 0.91），评审路径 gaps 与 make eval 不变；尺子换了，不能和 c0017 的 0.79 直接比 | [报告](reports/0020-visibility-ring1-stable.html) · [笔记](notes/blog/0020-visibility-ring1-stable.md) |
