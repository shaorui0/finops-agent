## 1. 数据
- [x] 1.1 `world.yaml`：12 个 finding 与 4 个 trap 各加五个字段
- [x] 1.2 `next_month.yaml` / `month_after.yaml`：`expect.details` 与 `story`

## 2. 生成器与测试
- [x] 2.1 `testenv/catalog.py`（占位符解析、HTML 渲染、`--out`）
- [x] 2.2 `testenv/test_catalog.py`

## 3. 验收
- [x] 3.1 `python3 -m unittest testenv.test_catalog -v`
- [x] 3.2 `make test`、`make check` 全绿，既有测试未改
- [x] 3.3 基础世界 `lines` 的 sha256 改前改后一致
- [x] 3.4 生成 `reports/testenv-catalog.html`，浏览器截图检查桌面与手机宽度
- [x] 3.5 `openspec validate c0014-testenv-catalog`
