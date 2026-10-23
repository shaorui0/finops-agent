## Why

23:47：项目要覆盖工业级使用 agent 的方方面面，本项目是完整样例——需要一张可逐项打勾的覆盖面清单，否则"体现 Harness Engineering"无法验收。
23:48：可见性要以终为始、一环套一环，每环有计划有结果。原来的 D1b 是一步到位的缺口表，要拆成四环。

## What Changes

- REQUIREMENTS：R15 补"工业级方方面面"；新增 R19；D1b 拆成四环链；§5 改为 Harness Engineering 覆盖面矩阵（13 面，带状态）；Q5 已确认。
- 新增 spec `visibility-chain`，定义四环的输入、输出与验收（实现留给后续 change）。

## Capabilities

### New Capabilities
- `visibility-chain`：从成本目标反推可见性需求，到 metric 缺口表的四环链。

### Modified Capabilities
（无）

## Impact

只改文档和 spec，不改代码。
