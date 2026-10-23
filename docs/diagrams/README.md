# 图

六张图，每张都是 mermaid 源文件（`.mmd`）加渲染好的 SVG。框图只画仓库里已有的模块和文件，标识符保持英文，说明用中文。汇总页见 `reports/index.html`。

| 图 | 画了什么 | 对应的文档 |
|---|---|---|
| `architecture` | 模块与分层：collect、snapshot、检测器、线索、judge（LLM，replay）、不变量、五段式与处置计划、SLO、报告；三层只读护栏；eval 与测试环境 | `docs/ARCHITECTURE.md` |
| `dataflow` | 一次运行写出的产物（snapshot、findings、plans、fivepart、visibility、slo、finops_metrics.prom、trace、report）、谁写谁读，以及 state.json 和 cassettes | `docs/ARCHITECTURE.md` 的产物契约 |
| `visibility-chain` | 可见性链环 1 到环 4 与「目标先行」规则，以及 LLM 推导环 1 的打分 | `docs/REQUIREMENTS.md` R17、R19，`eval/EXPERIMENTS.md` |
| `method` | M0 到 M6，运营级与架构级，先删、再降、最后买的顺序与硬规则 | `docs/METHOD.md` |
| `rot-lifecycle` | 发现的 new、persisting、resolved、regressed，每日、每周、每月节奏，告警 | `docs/FINOPS_SLO.md` |
| `harness-layers` | 规则层、hook、OpenSpec 改动循环与分阶段提交、eval 闸门、CI、写操作的人工 gate | `CONTRIBUTING.md`，`.claude/skills/finops-change-loop/SKILL.md` |

## 重新渲染

需要 docker。镜像版本固定为 `minlag/mermaid-cli:11.4.2`。

```bash
docs/diagrams/render.sh      # 渲染全部 .mmd，打印每个的退出码和 sha256
python3 tools/build_index.py # 重新生成 reports/index.html（内嵌 SVG）
```

单张：

```bash
docker run --rm -u $(id -u):$(id -g) -v "$PWD/docs/diagrams":/data minlag/mermaid-cli:11.4.2 -c /data/mermaid.json -i /data/architecture.mmd -o /data/architecture.svg
```

## 渲染所依据的源文件 sha256

`tools/test_build_index.py` 用下表核对 SVG 渲染自当前的源文件（checkout 不保留 mtime，所以不能只比时间）。改了 `.mmd` 之后重新渲染并更新这里。

| 源文件 | sha256 |
|---|---|
| `architecture.mmd` | `97c4e65413bc1ca9df781afe22f2a83093660a738e5408f4ed464f0e6799c0b3` |
| `dataflow.mmd` | `51387898ea9028af0ad4bd73512184758d423c7cd5b73746b9fa5794f973d5df` |
| `visibility-chain.mmd` | `abb02a9d949539a4ed5ca790ed4fd4181f5cd8b4fd35b41e34b5c42cf3d6f971` |
| `method.mmd` | `50a71c065abb5df72321a8b6f20613fb6f42cfd0b89d4f62c87fb42fa34780ed` |
| `rot-lifecycle.mmd` | `6521c1aa835860d7909bac16b14b6ac558e01b2b85c8745263d7f13474532dcc` |
| `harness-layers.mmd` | `975a09e43e77c191c1547ae3b8ab05afdf89b2749deb79903afd7d8cbeb13122` |
