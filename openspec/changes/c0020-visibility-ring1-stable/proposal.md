## Why

c0017 的结论：LLM 推出的第 ① 环 overlap 录制 0.91，但重采样 0.82、0.64，均值约 0.79，不稳。缺口表也和评审版差很多。两个根因（见 c0017 evidence）：

1. ring 1 在没看系统的情况下猜 metric 名正则，猜出来的有些根本不存在（`aws_ec2_network_in.*`）。
2. ring 4 里合并后的 SLI 只要有一个 need 缺，整个 SLI 就记 missing，已覆盖的 need 被抹掉。

目标不变（FA12：ring 1 不得出现服务器上的指标名）：让 ring 1 稳定达到评审要求，判据是 5 次采样的**均值** overlap ≥ 0.8，不是单次运气好。

## What Changes

- ring 1（`visibility_llm.py`，prompt v4）：只用文字说需要什么信号（`signal` 中文、`concept` 英文短语、`terms` 5-8 个小写单词）加 `scope`；不再写 `name`。校验拒绝带 `name` 的 need 和带下划线或标点的 term。
- ring 2（`visibility.py`）：新增 `fetch_catalog`（metadata 的 HELP 文本 + series 标签）和确定性的 `discover`：按含义在在线服务器的指标目录里找候选名，要求至少命中 2 个 term 且其中一个不是单位/统计类泛词，且带 scope 标签。无 `name` 的 need 才走发现；带 `name` 的评审路径逐字节不变。
- ring 4：`ring4(..., mix=True)` 逐 need 判断，SLI 状态按占比给 covered / partial / missing 并报告 `mix` 计数。默认 `mix=False`，评审路径输出不变。
- 评分 `eval/score_visibility.py`：words-only need 经 ring 2 发现后再和评审版比；新增 `--samples N`（派生 N 次，报 mean / min / max overlap）；缺口表加「ring-2 发现了什么」和 SLI 的 c/p/m 计数。
- cassette 只加不改；每次采样一个 prompt 变体（`(draw #k)`），各有各的 cassette，replay 可复现 5 次均值。

## Capabilities

### New Capabilities
- `visibility-ring1-stable`：words-only ring 1、ring 2 按语义发现名字、ring 4 need 级混合状态、`--samples N` 均值评估。

### Modified Capabilities
- `visibility-ring1-llm`（c0017）：LLM 派生文件不再含 `name`（评审文件 schema 不变）。

## Impact

只动 `visibility.py`、`visibility_llm.py`、两个测试文件、`eval/score_visibility.py`、cassette（只加）。不动 `__main__.py`、评审配置、Makefile；`make eval` 指标与评审路径的 `visibility.json` gaps 必须不变（证据里 diff）。LLM 调用预算 ≤ 15，prompt 迭代 ≤ 2 轮，每轮记入 evidence。不碰 AWS。
