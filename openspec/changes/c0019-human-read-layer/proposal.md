## Why

仓库里有实现、eval、文档和 18 个 change，但读者（面试官、评审、维护者自己）没有一个入口：不知道先看什么，架构和数据流只有文字和一张 ASCII 图，18 个 change 的动机散在各自的 proposal 里。维护者的要求：「human_read 这一层也要做一下，该画架构图的、表格的等等」。

## What Changes

- 新增 `docs/diagrams/`：六张图，每张是 mermaid 源文件加用固定版本 mermaid-cli 渲染的 SVG：architecture、dataflow、visibility-chain、method、rot-lifecycle、harness-layers。每个框都对照 `finops_agent/`、`eval/`、`testenv/`、`config/`、`hooks/`、`.github/`、`docs/` 里已有的东西，不画未来的东西。附 `README.md`（每张图画了什么、怎么重新渲染、源文件 sha256）和 `render.sh`。
- 新增 `tools/build_index.py`，生成 `reports/index.html`：自包含导读页（深浅色、手机可读、内嵌 SVG、无 JS、无外链），含项目是什么、10 分钟读法、六张图、全部 change 一览表（动机取 proposal 的 Why 第一句）、关键证据页、当前指标（`eval/baseline.json` 和 `python3 -m eval.heldout`）。
- 新增 `tools/test_build_index.py`：所有链接和资源都存在，六张 SVG 非空且与源文件对得上，每个 change 目录都在索引里。
- 不改 `README.md` 和 `docs/ARCHITECTURE.md`（后续一波统一接入）；嵌入图的 markdown 片段写在笔记里。

## Capabilities

### New Capabilities
- `human-read-layer`：为读者准备的图和导读页，由代码从仓库状态生成并有测试守住。

## Impact

只增文件，不改 agent 行为、eval 基线和任何运行产物。无 AWS 写操作，无需人工 gate。
