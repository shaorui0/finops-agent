# 验收证据

## D9 单测
```
test_a_changed_mapped_axiom_listed_as_update (test_sync_rules.SyncRulesTest.test_a_changed_mapped_axiom_listed_as_update) ... ok
test_b_new_unmapped_axiom_is_candidate_only (test_sync_rules.SyncRulesTest.test_b_new_unmapped_axiom_is_candidate_only) ... ok
test_baseline_has_no_proposals (test_sync_rules.SyncRulesTest.test_baseline_has_no_proposals) ... ok
test_c_private_and_public_leaks_flagged_and_not_copied (test_sync_rules.SyncRulesTest.test_c_private_and_public_leaks_flagged_and_not_copied) ... ok
test_cli_writes_only_out_and_refuses_protected_dirs (test_sync_rules.SyncRulesTest.test_cli_writes_only_out_and_refuses_protected_dirs) ... ok
test_d_native_axioms_proposed_back (test_sync_rules.SyncRulesTest.test_d_native_axioms_proposed_back) ... ok
test_mapping_parsed_from_distillation_doc (test_sync_rules.SyncRulesTest.test_mapping_parsed_from_distillation_doc) ... ok

----------------------------------------------------------------------
Ran 7 tests in 0.158s

OK
```

## make check
```
python3 tools/check_rules.py
check_rules: OK
```

## make test（尾部）
```
Ran 32 tests in 2.010s

OK
<tmp>/report.html
```

## 对真实母版跑一次（只记计数）

母版 axioms 基线：manifest 记录 50 个文件名 + sha256，无内容；基线取自今天的母版，所以与蒸馏当时的版本是否一致无法证明，首次运行必为 0 变更。
```
$ python3 tools/sync_rules.py --parent <母版>/rules --out <scratchpad>/real_proposal.md
摘要：母版已变更且已映射 0 条；母版新增未映射 0 条（候选）；项目原生可回提 2 条；未变化 14 条；映射缺失 0 条；命中泄漏模式被标记 0 条。
```

说明：本机没有 `.leak_patterns.local`，真实运行只用公开模式；私有模式路径已由夹具测试覆盖。

## 只读性
`git status` 在母版目录无改动由工具本身不写入保证；测试 `test_cli_writes_only_out_and_refuses_protected_dirs` 比对了母版夹具与 rules/ 的字节快照。
