## Why

24 个 change 之后，读者（面试官、评审、维护者）看到的文档落后于代码：README 的结果表还是 c0005 的 7/12，ARCHITECTURE 里还写着判断层和处置计划「进行中」，覆盖面矩阵里有「计划、待建」，没有一份文档把能力、证据和边界放在一起，也没有记录这 24 个 change 是怎么由多个 agent 并行做出来的。这是「人读」的收尾：让一个新读者看到准确、完整、中文、链接齐全的项目。

## What Changes

- 新增 `docs/NARRATIVE.md`（十二项能力声明，各带证据链接与诚实边界，加诚实的成绩单）、`docs/MATURITY.md`（20 条完成标准，状态、证据、验证命令）、`docs/BUILD_PROCESS.md`（闭环、多 agent 调度、波次表、事故与教训）。
- 更新 `README.md`：进度表补 c0009 到 c0025，结果改成三层表（样本内、已污染的样本外、预注册新世界），嵌入图，补入口链接，设计表补判断层、落地与脱敏、计划、五段式、rot 语义、省钱核实、预注册。
- 更新 `docs/ARCHITECTURE.md`：删过期的「进行中」，补判断层与 LLM 录制回放、处置、五段式、预防、核实、可见性第 ② 环发现、五种腐烂状态，嵌架构图和数据流图。
- 更新 `docs/REQUIREMENTS.md` §5：每行写明交付它的 change，只保留两个依赖维护者的例外。
- 更新 `rules/WORKSPACE.md`、`CONTRIBUTING.md`、`docs/METHOD.md`、`docs/DISTILLATION.md`（只加交叉链接）；`eval/EXPERIMENTS.md` 的对抗一节改为 c0022 之后的事实，顶部加摘要和目录。
- 重新生成 `reports/index.html`。

## Capabilities

### New Capabilities
- `docs-consolidation`：文档的链接可解析、标题为中文、状态与代码一致。

## Impact

只改文档和生成的导读页，不改代码、不改任何来自代码的数字（数字取自 `eval/EXPERIMENTS.md` 和生成文档）。`docs/SAVINGS_VERIFICATION.md` 与 `docs/FINOPS_SLO.md` 正文不动。无 AWS 写操作。
