# 0019 human-read-layer 原始笔记

- 起因：仓库有 18 个 change 的实现和证据，但读者没有入口。不知道先看哪，架构只有一张 ASCII 图。维护者原话：「human_read 这一层也要做一下，该画架构图的、表格的等等」。
- 核心想法：给读者的层也要像代码一样可生成、可测试。导读页由 `tools/build_index.py` 从 openspec、reports、notes、eval 生成，测试保证链接不断、图没过期、每个 change 都列了。手写的导读页三个月后必然和仓库脱节。
- 图只画 main 上已有的东西。逐个读 `__main__.py`、`judge/`、`fivepart.py`、`remediate.py`、`prevention.py`、`slo.py`、`config/`、CI、CLAUDE.md 再画。任务清单里提到的「escrow」和「dispatch/worktrees」仓库里没有（grep 只命中 c0010 证据里的一个 worktree 对比），所以没画；harness-layers 里写操作那一格画的是现有机制：`plans.json` 只是 dry-run，人审后手动执行，承诺折扣只给建议不给命令。
- 反直觉 1：mermaid-cli 在容器里渲染，容器没有 CJK 字体，量出来的文字宽度比浏览器里的小，中文标签会被框裁掉。解法是 `mermaid.json` 加大 padding，页面里给 `foreignObject` 设 `overflow:visible`。看图要用真浏览器截图看，不能只看退出码 0。
- 反直觉 2：六张 mermaid SVG 内联进同一个 HTML，它们的 id 全是 `my-svg`，mermaid 的 CSS 按 id 作用域，会互相覆盖样式。构建时按图名改 id。
- 反直觉 3：dataflow 一开始用子图（输入、写入方、产物）分组，布局炸了，边全挤在一起。去掉子图、按流水线顺序摆，才可读。分组不是越多越好。
- 反直觉 4：checkout 不保留 mtime，「SVG 不比 .mmd 旧」在 CI 里没意义。改成在 `docs/diagrams/README.md` 记每个 .mmd 的 sha256，测试核对；mtime 只作为另一条通过路径。
- 图的 SVG 是二进制产物级别的东西，提交进仓库而不是 CI 里渲染：读者在 GitHub 上直接能看；渲染依赖 docker，不该成为读仓库的前提。
- 指标表：基线从 `eval/baseline.json` 读，留出世界跑 `python3 -m eval.heldout`（replay，约 10 秒）。测试用 `--no-heldout`，保证确定性、不起服务。
- 没改 README.md 和 docs/ARCHITECTURE.md。ARCHITECTURE.md 里的「进行中的部分」已经过期（judge 和 plans 早已合入），留给后续一波统一接入。

## 嵌入图的 markdown 片段（后续一波放进 README / ARCHITECTURE）

README.md、docs/ARCHITECTURE.md 在仓库根或 docs/ 下，相对路径不同。从仓库根的 README.md：

```markdown
![架构：模块与分层](docs/diagrams/architecture.svg)
![数据流：产物谁写谁读](docs/diagrams/dataflow.svg)
![可见性链](docs/diagrams/visibility-chain.svg)
![方法 M0 到 M6](docs/diagrams/method.svg)
![腐烂生命周期与巡检节奏](docs/diagrams/rot-lifecycle.svg)
![Harness 分层](docs/diagrams/harness-layers.svg)
导读页：[reports/index.html](reports/index.html)
```

从 docs/ 下的文档（如 docs/ARCHITECTURE.md），把前缀 `docs/diagrams/` 换成 `diagrams/`：

```markdown
![架构：模块与分层](diagrams/architecture.svg)
![数据流：产物谁写谁读](diagrams/dataflow.svg)
```

建议位置：architecture 和 dataflow 放 ARCHITECTURE.md「数据流」节开头；method 放 METHOD.md「七步」前；rot-lifecycle 放 FINOPS_SLO.md「Rot」节；visibility-chain 放 REQUIREMENTS 或 README 的可见性段；harness-layers 放 CONTRIBUTING.md「改动闭环」前。

PROGRESS_ROW: | c0019-human-read-layer | 2026-10-24 | 六张 mermaid 图（架构、数据流、可见性链、方法、腐烂、harness）+ 生成的导读页 reports/index.html + 链接/图新鲜度测试 | 给读者的层也要可生成、可测试：手写导读必然和仓库脱节 | [报告](reports/0019-human-read-layer.html) · [笔记](notes/blog/0019-human-read-layer.md) |
