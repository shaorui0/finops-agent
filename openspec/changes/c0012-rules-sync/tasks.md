## 1. 工具
- [x] 1.1 `tools/sync_rules.py`：映射解析、manifest 对比、泄漏标记、回提列表
- [x] 1.2 `tools/test_sync_rules.py` + `tools/fixtures_sync/` 夹具母版
- [x] 1.3 `tools/rules_sync_manifest.json`：对真实母版生成（只存文件名与哈希）

## 2. 验收
- [x] 2.1 `python3 -m unittest discover -s tools -p 'test_sync_rules.py' -v` 通过（覆盖 a/b/c/d 四类）
- [x] 2.2 对真实母版跑一次，evidence.md 只记计数
- [x] 2.3 `make check`、`make test` 全绿
