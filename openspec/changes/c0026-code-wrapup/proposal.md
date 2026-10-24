## Why

前几个 change 留下几处代码层面的尾巴：`slo.py` 用模块级变量偷传快照（c0023 的临时做法）；报告的 SLO 一节没有展示 `not_redetected`；`make test` 漏跑 7 个测试模块；`eval/heldout.py` 的默认端口要靠环境变量才好用。另外文档质量（链接失效、英文标题）没有任何仓库检查在拦。

## What Changes

- `tools/check_rules.py` 新增两项检查（`--docs`）：D11 相对链接与反引号路径必须能解析；D16 标题含 ≥2 个英文单词且无中文则失败。`make check-docs` 单独跑；`make check` 仅在 `DOCS_CHECK=1` 时带 `--docs`，CI 的 `DOCS_CHECK` 目前为空，文档改写合并后由主 agent 改成 `1`。
- `make test` 改为按目录发现 finops_agent / eval / testenv / tools / hooks 下所有 `test_*.py`。
- `eval/heldout.py` 默认端口块 47500-47599，`FINOPS_HELDOUT_PORTS` 仍可覆盖。
- `__main__.py` 把快照显式传给 `slo.diff_state`，删除 `slo.py` 的模块级暂存，行为不变。
- `report.py` 的 SLO 一节显示 `not_redetected`（数量 + 列表，原因「资源仍在，但本次未再检出」）。

## Capabilities

### New Capabilities
- `code-wrapup`：文档检查、完整测试入口、显式快照传递、未再检出展示。

### Modified Capabilities
（无）

## Impact

只改 tools/check_rules.py、Makefile、ci.yml、finops_agent/{__main__,report,slo}.py 及其测试、eval/heldout.py。不改 prompt 文本、cassette、docs；`make eval` 与 `python3 -m eval.heldout` 的数字不变。不涉及 AWS 写操作。
