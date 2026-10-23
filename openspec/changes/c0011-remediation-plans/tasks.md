## 1. 计划生成
- [x] 1.1 `finops_agent/remediate.py`：Plan 数据结构、六类 finding 的处理器、排序
- [x] 1.2 CLI：`plans <findings.json> --out`、`apply <plans.json> --approve <id> [--script]`
## 2. 测试
- [x] 2.1 用真实 run 产出的 `test_remediate_fixture.json`，覆盖四个判据和"不执行"断言
## 3. 验收
- [x] 3.1 `python3 -m unittest finops_agent.test_remediate -v` 通过
- [x] 3.2 `make test`、`make check` 全绿
- [x] 3.3 `openspec validate c0011-remediation-plans`
