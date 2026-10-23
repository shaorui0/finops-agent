## Why

c0015 的对抗实验留下一个已知漏洞：把数字塞进真实浪费 fleet 的实例 Name tag（`number_bait`，`$99,999` 和 `12,345`），模型做对了判断（waste、选对候选、声明忽略注入），但 prompt 要求它提到注入，于是它在 reasoning 里复述了这些数字。数值 grounding（G1-G8）发现数字不在证据里，整条 judgment 被拒，约 $1,469 的 busy_but_useless finding 从报告里消失。攻击者不需要骗过模型，只需要让校验器对一条正确的结论说不。fail closed 在这里成了攻击面。

原则 FA03：金额和每个承重数字来自代码算出的候选，不来自模型的叙述。既然金额不取自叙述，叙述里的未验证数字就不该有权否决整条 finding。

## What Changes

- `finops_agent/judge/validate.py`：waste 判断的结构化字段（verdict、type、method_step、resources、evidence id、savings_choice 属于计算候选、basis 与候选一致、protective tag）全部合法、只有叙述（title / hops / reasoning）含未取自证据的数字时，含数字的从句替换为固定标记，finding 保留，redaction 记入 `Judgment.redactions`（规则 G9）。非 waste 判断、结构化字段里的任何问题仍然整条拒绝。脱敏后重新校验，仍有未验证数字则拒绝。
- `finops_agent/judge/__init__.py`（最小改动）：redaction 写进 finding 的 evidence（来源 `redaction`，不含被移除的文字和数字）、judgment 记录（不含原文）、trace（含原文、数字、sha256）。
- `eval/test_adversarial.py`：`number_bait` 不再是已知限制，9 个变体断言相同；新增 3 个变体（`number_bait_batch`、`number_bait_xaz`、`number_bait_volume`），planted 数字不得出现在 findings.json 与 report.html。
- 新增 2 条 cassette，不改已有 cassette，不改 prompt。

## Capabilities

### New Capabilities
- `grounding-redaction`：叙述里的未验证数字被脱敏而不是否决 finding。

### Modified Capabilities
（无）

## Impact

不改 prompt、gather、brief、analyze，所有已有 cassette key 不变，基础世界与 held-out 的指标不变。`finops_agent/test_judge.py` 里一条断言按新语义改成 not_waste 的拒绝（该测试断言的旧行为正是本 change 取消的）。不涉及 AWS 写操作，没有人工 gate，回滚就是 git revert。
