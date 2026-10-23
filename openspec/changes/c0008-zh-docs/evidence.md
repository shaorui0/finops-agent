# c0008 验收证据

## 3.1 测试与评估
```
Ran 3 tests in 0.063s
OK
Ran 7 tests in 1.755s
OK
Ran 32 tests in 2.012s
OK
check_rules: OK
{"recall": 0.5833, "savings_recall": 0.1888, "precision": 1.0, "savings_accuracy": 1.0, "step_agreement": 1.0, "depth": {"shallow_recall": 1.0, "deep_recall": 0.4444}, "leads": 4}
gates: pass
```

## 3.2 报告语言
```
标题/表头总数 60 | 残留英文界面标签 2 ['M5 承诺折扣 · Savings Plan / RI，放在清理和降配之后', 'F07 · Savings Plan 利用率 60.5%（本周期 $683 未用），不要再买承诺']
  含 NatGateway-Bytes: True
  含 vol-0leg000000000b001: False
  含 aws_ec2_cpuutilization_average: True
  含 可见性链: True
  含 运行留痕: True
  含 FinOps SLO: True
```

## 3.3 openspec validate
```
Change 'c0008-zh-docs' is valid
```

## 说明与顺带发现

- 残留的 2 处"英文"是 AWS 产品名 Savings Plan，按约定保留。
- 验收时发现报告的发现卡片从未显示资源 ID（`vol-0leg000000000b001` 不在报告里）。这与翻译无关，是 c0005 起就有的缺口：看不到资源的发现无法执行。已在卡片上加"资源"一行，重跑后报告含该卷 ID（1 处）。
