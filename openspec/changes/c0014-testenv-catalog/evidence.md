# c0014 验收证据

## 3.1 test_catalog
```
test_alert_references_resolve_to_rules (testenv.test_catalog.AlertsExist.test_alert_references_resolve_to_rules) ... ok
test_lines_digest_is_stable_and_ground_truth_semantics_kept (testenv.test_catalog.BaseWorldUnchanged.test_lines_digest_is_stable_and_ground_truth_semantics_kept) ... ok
test_counts (testenv.test_catalog.FivePartsPresent.test_counts) ... ok
test_every_entry_has_all_five_fields (testenv.test_catalog.FivePartsPresent.test_every_entry_has_all_five_fields) ... ok
test_runbook_flags_irreversible_steps (testenv.test_catalog.FivePartsPresent.test_runbook_flags_irreversible_steps) ... ok
test_scenario_details_cover_every_expectation (testenv.test_catalog.FivePartsPresent.test_scenario_details_cover_every_expectation) ... ok
test_cli_writes_file (testenv.test_catalog.GeneratedPage.test_cli_writes_file) ... ok
test_contains_every_id (testenv.test_catalog.GeneratedPage.test_contains_every_id) ... ok
test_contains_scenarios_and_gaps (testenv.test_catalog.GeneratedPage.test_contains_scenarios_and_gaps) ... ok
test_five_part_headings_per_card (testenv.test_catalog.GeneratedPage.test_five_part_headings_per_card) ... ok
test_self_contained (testenv.test_catalog.GeneratedPage.test_self_contained) ... ok
test_no_literal_money_and_placeholders_resolve (testenv.test_catalog.NumbersAreComputed.test_no_literal_money_and_placeholders_resolve) ... ok
test_savings_placeholder_matches_world (testenv.test_catalog.NumbersAreComputed.test_savings_placeholder_matches_world) ... ok
test_unknown_placeholder_fails_loudly (testenv.test_catalog.NumbersAreComputed.test_unknown_placeholder_fails_loudly) ... ok

----------------------------------------------------------------------
Ran 14 tests in 0.572s

OK
```

## 3.2 make test / make check
```
Ran 3 tests in 0.069s
OK
Ran 14 tests in 1.421s
OK
Ran 41 tests in 5.715s
OK
check_rules: OK
```

## 3.3 基础世界 lines 的 sha256（改前 = 改后；第二行为 raw 去掉 ground_truth 后的 sha256）
```
before:
ebb2c2890fbbf99fe06b3f7e7916cffc5971fdb37f36e98fdde824cff8b35db3
77251743aa6e8bdf40e11bc970595f0e00fae39e731a2b947b7b881871768499
after:
ebb2c2890fbbf99fe06b3f7e7916cffc5971fdb37f36e98fdde824cff8b35db3
77251743aa6e8bdf40e11bc970595f0e00fae39e731a2b947b7b881871768499
```
ground_truth 只增不改：对旧版 world.yaml 解析结果去掉五个新字段后与旧版逐项相等（拼接脚本里 assert 通过）。

## 3.4 页面
```
wrote reports/testenv-catalog.html (75321 bytes)
 testenv/catalog.py                 | 520 +++++++++++++++++++++++++++++++++++++
 testenv/scenarios/month_after.yaml | 116 +++++++++
 testenv/scenarios/next_month.yaml  | 132 ++++++++++
 testenv/test_catalog.py            | 150 +++++++++++
 testenv/world.yaml                 | 257 +++++++++++++++++-
 5 files changed, 1171 insertions(+), 4 deletions(-)
```
桌面 1100px 与窄屏 390px 用 headless Chrome 截图检查：卡片五段分色，总览表与架构图可横向滚动，深色模式正常。

## 3.5 openspec validate
```
Change 'c0014-testenv-catalog' is valid
```
