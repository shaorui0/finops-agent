# c0003 验收证据

## 4.1 check_rules
```
check_rules: OK
exit=0
```

## 4.2 单测
```
test_axiom_missing_section (test_check_rules.CheckRulesTest.test_axiom_missing_section) ... ok
test_axiom_not_indexed (test_check_rules.CheckRulesTest.test_axiom_not_indexed) ... ok
test_baseline_passes (test_check_rules.CheckRulesTest.test_baseline_passes) ... ok
test_dangling_reference (test_check_rules.CheckRulesTest.test_dangling_reference) ... ok
test_missing_required_file (test_check_rules.CheckRulesTest.test_missing_required_file) ... ok
test_private_leak_from_local_file (test_check_rules.CheckRulesTest.test_private_leak_from_local_file) ... ok
test_public_leak (test_check_rules.CheckRulesTest.test_public_leak) ... ok
Ran 7 tests in 0.268s
OK
Ran 3 tests in 0.064s
OK
```

## 4.3 openspec validate
```
Change 'c0003-project-rules' is valid
```

## 负向验证：泄漏扫描确实生效
```
FAIL leak pattern in rules/_probe.md:1
exit=1
```

## 顺带发现

第一次跑负向验证时，check_rules 还报出 `openspec/specs/` 不存在：空目录不被 git 跟踪，新 clone 会缺这个目录。已加 `openspec/specs/.gitkeep`。

## 规则层清单
```
rules/axioms/fa01_verifiability_first.md
rules/axioms/fa02_isolate_process_verify.md
rules/axioms/fa03_data_over_opinion.md
rules/axioms/fa04_precision_cascades.md
rules/axioms/fa05_big_levers_first.md
rules/axioms/fa06_cost_is_a_control_loop.md
rules/axioms/fa07_agent_is_unreliable_component.md
rules/axioms/fa08_responsibility_not_delegated.md
rules/axioms/fa09_docs_are_memory.md
rules/axioms/fa10_engineered_exposure.md
rules/axioms/fa11_context_isolation.md
rules/axioms/fa12_start_from_the_end.md
rules/axioms/fa13_tide_is_not_waste.md
rules/axioms/INDEX.md
rules/COMMUNICATION.md
rules/skills/INDEX.md
rules/SOUL.md
rules/USER.md
rules/WORKSPACE.md
```
