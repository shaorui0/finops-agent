## 1. 图
- [x] 1.1 读 `finops_agent/`、`eval/`、`testenv/`、`config/`、`docs/`、`rules/`、`.github/`、`Makefile`，列出每张图的框
- [x] 1.2 六个 `.mmd`，用 `minlag/mermaid-cli:11.4.2` 渲染成 SVG，退出码记入证据
- [x] 1.3 `docs/diagrams/README.md`、`render.sh`、`mermaid.json`

## 2. 导读页
- [x] 2.1 `tools/build_index.py`：项目说明、读法、六图、change 表、证据页、指标
- [x] 2.2 `tools/test_build_index.py`

## 3. 验收
- [x] 3.1 六图渲染退出码全 0；`python3 -m unittest tools.test_build_index -v` 全绿
- [x] 3.2 `python3 tools/build_index.py` 生成 `reports/index.html`，浏览器截图检查
- [x] 3.3 `make test`、`make check` 全绿（写完证据后再跑 check）；`openspec validate c0019-human-read-layer`
