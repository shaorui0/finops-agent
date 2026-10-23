# c0013 验收证据

## 2.1 链接与路径检查
```
CONTRIBUTING.md checked 34
docs/ARCHITECTURE.md checked 54
skipped(generated/placeholder): ['eval.json', 'findings.json', 'finops_metrics.prom', 'label/<name>/values', 'notes/blog/<NNNN-slug>.md', 'openspec/changes/<id>/', 'openspec/changes/<id>/evidence.md', 'report.html', 'reports/<NNNN-slug>.html', 'runs/<id>/', 'runs/<id>/eval.json', 'runs/<run_id>/', 'runs/local/', 'runs/state.json', 'slo.json', 'snapshot.json', 'trace.jsonl', 'visibility.json']
ALL OK
```

脚本规则：相对链接必须存在；反引号里形如路径的词（含 `/` 或常见扩展名）必须存在；`runs/` 开头、含 `<>` 占位符、以及裸文件名的产物（如 `snapshot.json`）是生成物，列入 skipped。

## 2.2 产物字段对照（文档反引号覆盖真实运行的 keys）
```
findings.json top: 10 keys, undocumented: []
finding: 11 keys, undocumented: []
lead: 6 keys, undocumented: []
ranking: 4 keys, undocumented: []
attribution: 4 keys, undocumented: []
visibility.json top: 4 keys, undocumented: []
plan: 8 keys, undocumented: []
search: 5 keys, undocumented: []
gap: 4 keys, undocumented: [] (needs 以 `needs[]` 形式记载)
need: 7 keys, undocumented: []
slo top: 3 keys, undocumented: []
slo row: 11 keys, undocumented: []
slo row budget: 2 keys, undocumented: []
snapshot: 9 keys, undocumented: []
snapshot grouped: 12 keys, undocumented: []
trace: 6 keys, undocumented: []
prom metrics: 7 keys, undocumented: []
```

## 2.3 make check / make test / make eval
```
python3 tools/check_rules.py
check_rules: OK
Ran 3 tests in 0.069s
OK
Ran 7 tests in 1.115s
OK
Ran 32 tests in 1.997s
OK
python3 -m eval.score runs/t6eval/findings.json; status=$?; /Applications/Xcode.app/Contents/Developer/usr/bin/make stop; exit $status
{"recall": 0.5833, "savings_recall": 0.1888, "precision": 1.0, "savings_accuracy": 1.0, "step_agreement": 1.0, "depth": {"shallow_recall": 1.0, "deep_recall": 0.4444}, "leads": 4}
missed: GT01(4 hops), GT02(3 hops), GT03(3 hops), GT05(3 hops), GT12(3 hops)
gates: pass
```

## 2.4 openspec validate
```
Change 'c0013-oss-docs' is valid
```
