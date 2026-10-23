# c0006 验收证据

## 3.1 make test / make check
```
Ran 3 tests in 0.067s
OK
Ran 7 tests in 1.093s
OK
Ran 27 tests in 2.051s
OK
check_rules: OK
```

## 3.2 make eval
```
{"recall": 0.5833, "savings_recall": 0.1888, "precision": 1.0, "savings_accuracy": 1.0, "step_agreement": 1.0, "depth": {"shallow_recall": 1.0, "deep_recall": 0.4444}, "leads": 4}
missed: GT01(4 hops), GT02(3 hops), GT03(3 hops), GT05(3 hops), GT12(3 hops)
gates: pass
```

## 3.3 负向：闸门会变红
```
test_injection_target_must_be_flagged (eval.test_score.ScoreTest.test_injection_target_must_be_flagged) ... ok
test_invariant_violation_fails (eval.test_score.ScoreTest.test_invariant_violation_fails) ... ok
test_regression_against_baseline_fails (eval.test_score.ScoreTest.test_regression_against_baseline_fails) ... ok
test_resource_overlap_needs_same_step (eval.test_score.ScoreTest.test_resource_overlap_needs_same_step) ... ok
test_savings_outside_range_lowers_accuracy (eval.test_score.ScoreTest.test_savings_outside_range_lowers_accuracy) ... ok
test_trap_touch_fails (eval.test_score.ScoreTest.test_trap_touch_fails) ... ok
Ran 6 tests in 0.000s
OK
planted rightsizing on the tidal web fleet -> exit 1 | GATE FAILED: trap violations: [{'trap': 'TR01', 'resource': 'web-asg', 'finding': 'FX', 'why': 'rightsize'}]
removed one detector's output -> exit 1 | GATE FAILED: recall 0.5 < baseline 0.5833; savings_recall 0.0428 < baseline 0.1888
```

## 3.4 openspec validate
```
Change 'c0006-eval-ci' is valid
```

## 3.5 GitHub Actions

首次推送 `9797e73`，run 39977048159：**success**（Ubuntu / Python 3.12；check → test → eval 全过，运行报告已作为 artifact 上传）。

## 基线
```
{
  "recall": 0.5833,
  "savings_recall": 0.1888,
  "precision": 1.0,
  "savings_accuracy": 1.0,
  "step_agreement": 1.0,
  "depth": {
    "shallow_recall": 1.0,
    "deep_recall": 0.4444
  }
}
```

## 顺带发现

- 首次打分暴露打分器自己的两个 bug：注入陷阱 TR04 的语义写反（应当"必须被报出"）；仅凭资源重叠就算命中，把 M1 误打 tag 的发现记成了 M6 常开 ETL 的命中，recall 虚高 0.08。修正后的基线才是真实值。
- 推送前历史扫描报 `/Users/` 22 处命中，排查后全部是 check_rules.py 里的检测正则本身，不是泄漏。
- 本地 CI 轮询脚本因 commit message 里的换行导致 JSON 严格解析失败，改为 strict=False 后取到结果。
