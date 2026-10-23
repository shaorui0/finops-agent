# c0019-human-read-layer 验收证据

所有输出为本次真实运行原样粘贴（路径已是相对路径）。

## 1. 六张图渲染（docs/diagrams/render.sh，镜像 minlag/mermaid-cli:11.4.2）
```
architecture.mmd exit=0 sha256=97c4e65413bc1ca9df781afe22f2a83093660a738e5408f4ed464f0e6799c0b3
dataflow.mmd exit=0 sha256=51387898ea9028af0ad4bd73512184758d423c7cd5b73746b9fa5794f973d5df
harness-layers.mmd exit=0 sha256=975a09e43e77c191c1547ae3b8ab05afdf89b2749deb79903afd7d8cbeb13122
method.mmd exit=0 sha256=50a71c065abb5df72321a8b6f20613fb6f42cfd0b89d4f62c87fb42fa34780ed
rot-lifecycle.mmd exit=0 sha256=6521c1aa835860d7909bac16b14b6ac558e01b2b85c8745263d7f13474532dcc
visibility-chain.mmd exit=0 sha256=abb02a9d949539a4ed5ca790ed4fd4181f5cd8b4fd35b41e34b5c42cf3d6f971
render.sh exit=0
42472 docs/diagrams/architecture.svg
39104 docs/diagrams/dataflow.svg
27768 docs/diagrams/harness-layers.svg
20435 docs/diagrams/method.svg
29322 docs/diagrams/rot-lifecycle.svg
15589 docs/diagrams/visibility-chain.svg
```

## 2. 测试 tools.test_build_index
```
test_build_is_deterministic_without_heldout (tools.test_build_index.IndexTest.test_build_is_deterministic_without_heldout) ... ok
test_diagrams_exist_and_match_source (tools.test_build_index.IndexTest.test_diagrams_exist_and_match_source) ... ok
test_every_link_resolves (tools.test_build_index.IndexTest.test_every_link_resolves) ... ok
test_first_sentence (tools.test_build_index.IndexTest.test_first_sentence) ... ok
test_index_exists_and_is_self_contained (tools.test_build_index.IndexTest.test_index_exists_and_is_self_contained) ... ok
test_index_lists_every_change (tools.test_build_index.IndexTest.test_index_lists_every_change) ... ok
test_key_evidence_pages_linked (tools.test_build_index.IndexTest.test_key_evidence_pages_linked) ... ok

----------------------------------------------------------------------
Ran 7 tests in 0.051s

OK
exit=0
```

## 3. 生成导读页
```
reports/index.html
exit=0
  198739 reports/index.html
0
0
```

## 4. 留出世界指标（页面「当前指标」所用）
```
| world | kind | recall | savings_recall | precision | savings_accuracy | savings_accuracy_day_scaled | step_agreement | traps | invariants | findings/GT | LLM calls | cost |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| base (in-sample) | in-sample | 1.0 | 1.0 | 1.0 | 0.9167 | 0.9167 | 1.0 | 0 | 0 | 12/12 | 7 | $0.1426 |
| next_month | held-out | 0.9 | 0.5658 | 1.0 | 0.8889 | 1.0 | 1.0 | 0 | 0 | 9/10 | 6 | $0.1199 |
| month_after | held-out | 0.9091 | 0.5664 | 1.0 | 1.0 | 1.0 | 1.0 | 0 | 0 | 10/11 | 6 | $0.1193 |
```

## 5. make test
```
make test exit=0
Ran 3 tests in 0.077s
OK
Ran 21 tests in 2.369s
OK
Ran 108 tests in 7.288s
OK
```

## 6. openspec validate
```
Change 'c0019-human-read-layer' is valid
```

## 7. make check（写完证据和报告之后，见第 8 节）

## 8. 终检（报告与导读页生成之后）
```
reports/index.html
Ran 7 tests in 0.044s

OK
make test exit=0
check_rules: OK
make check exit=0
```
