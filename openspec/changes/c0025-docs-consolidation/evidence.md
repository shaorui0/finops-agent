# c0025 验收证据

所有输出为本次真实运行原样粘贴（路径为相对路径）。

## 1. 链接与英文标题检查（自写脚本 `openspec/changes/c0025-docs-consolidation/doc_check.py`）

检查范围：README.md、CONTRIBUTING.md、testenv/README.md、eval/EXPERIMENTS.md、docs/**/*.md、rules/**/*.md。规则：相对链接和反引号仓库路径必须存在（忽略 http、纯锚点、runs/、含 `<` 或 `*` 的路径）；标题在反引号之外有两个以上 ASCII 单词且没有汉字即为英文标题。

```
docs/FINOPS_SLO.md:37 HEADING ## Waste budget
docs/FINOPS_SLO.md:79 HEADING ### Busy but useless
docs/FINOPS_SLO.md:83 HEADING ### Path cost
bad= 3
exit=1
```

本 change 拥有的文件全部通过。上面列出的是 `docs/FINOPS_SLO.md` 的英文小标题，属于不归本 change 的正文，本 change 未改动（权限外），列入回报的 BLOCKED；D16 的全仓库英文标题检查要等这三行改成中文才会全绿。

## 2. D12 覆盖面矩阵状态列扫描

```
$ sed -n '/^## 5/,/^## 6/p' docs/REQUIREMENTS.md | awk -F'|' 'NF>4{print $4}' | grep -cE '计划|待建|待设计'
0
```

两个依赖维护者的例外在表后单独列出：真实 AWS 账号、主页入口的 push。

## 3. D18 嵌图

```
$ grep -c 'diagrams/.*svg' README.md docs/ARCHITECTURE.md; ls docs/diagrams/*.svg | wc -l
README.md:5
docs/ARCHITECTURE.md:3
       6
```

## 4. README 三层结果行（数字取自 EXPERIMENTS §7.3，由 `python3 -m eval.heldout` 复现）

```
112:| 预注册的全新世界 | fresh_world（货运 SaaS，冻结后只评估一次） | 0.75 | 0.568 | 0.667 | 1 | 唯一没被污染的泛化数字：换一个世界会掉，漏检在确定性检测与取证层，判断层 8 个判断全部被接受 |

$ python3 -m eval.heldout
| world | kind | recall | savings_recall | precision | savings_accuracy | savings_accuracy_day_scaled | step_agreement | traps | invariants | findings/GT | LLM calls | cost |
| base (in-sample) | in-sample | 1.0 | 1.0 | 1.0 | 0.9167 | 0.9167 | 1.0 | 0 | 0 | 12/12 | 7 | $0.1426 |
| next_month | held-out | 1.0 | 1.0 | 1.0 | 0.8 | 1.0 | 1.0 | 0 | 0 | 10/10 | 7 | $0.1839 |
| month_after | held-out | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 | 0 | 0 | 11/11 | 7 | $0.1617 |
| fresh_world | preregistered | 0.75 | 0.568 | 1.0 | 0.5385 | 0.5385 | 1.0 | 1 | 0 | 13/12 | 8 | $0.1507 |
```

## 5. 导读页

```
Ran 7 tests in 0.057s

OK
1
```

## 6. 无本机绝对路径

```
none
```

## 7. make check 与 make test（写完 evidence 之后）

```
$ make check
python3 tools/check_rules.py
check_rules: OK
$ make test
Ran 3 tests ... OK
Ran 21 tests ... OK
Ran 116 tests ... OK
$ openspec validate c0025-docs-consolidation
Change 'c0025-docs-consolidation' is valid
```
