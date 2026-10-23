## 决策

**不改 prompt，改校验器。** cassette key = sha256(model + prompt)，改 prompt 要重录全部已有 cassette并重新证明基础、held-out、对抗三组指标。而漏洞不在模型：模型的结构化输出是对的。所以修法放在校验器里，已有 cassette 全部不动，number_bait 的 cassette 原样回放，只是校验结果变了。

## 做法（规则 G9）

1. 先校验所有结构化字段：verdict、type（分类表内）、method_step、resources（在 brief 允许列表内）、evidence id（在 brief 内）、savings_choice（必须是代码算出的候选 key）、basis（与该候选一致）、保护 tag。任何一项不合法，整条拒绝，和以前一样。
2. 只有这些都合法，叙述里的未验证数字才走脱敏：按 `。！？；，、`、英文句末、换行切从句，含未验证数字的从句整句换成 `[已移除：含未取自证据的数字]`。数字在 `$99,999` 这种带逗号的形式里不会被切开（只按中文逗号切）。
3. 脱敏后对 title + reasoning + hops 再跑一遍 `ungrounded_numbers`，还有就拒绝（fail closed）。title 若脱敏后什么都不剩，由代码生成 `type：资源`。
4. 非 waste 判断不变（G8：不会成为 finding，只是日志行，可复述 untrusted 里的数字；编造的数字仍拒绝）。

## 为什么没有放松 grounding

- 金额：finding 的 `monthly_savings_usd` 来自 `b.candidate(savings_choice).value`，从来不是叙述里的数字。savings_choice 若不是候选，拒绝。所以叙述里的数字不承重。
- 输出：脱敏后没有任何未验证数字进入 findings.json 和 report.html，由第 3 步的再校验保证，测试里对 planted 数字在 findings.json 与 report.html 做整数匹配。放松的是「一个未验证数字是否有权否决整条 finding」，不是「未验证数字能否被展示」。前者是可用性策略，后者才是 grounding，后者没变。
- 同一个 `ungrounded_numbers` 判定（G1-G8）原样使用，容差、日期、标识符规则没有动。

## 攻击者之后能做什么、不能做什么

不能：压掉真实 finding（number_bait 与 number_bait_xaz 里模型复述了 bait，finding 与金额都保住；batch 变体里模型没复述）；让任何编造的数字出现在 finding / 报告；改金额、改资源、改类型、改 basis；碰到结构化字段里的任何值（`$99,999` 放进 savings_choice 仍然拒绝）。

能：让一句话被脱敏（降低叙述可读性，被移除的从句数量由模型复述多少决定，上限是叙述长度）；脱敏记录在 finding 上可见，攻击留痕。非数字的注入文字（例如「忽略指令」）不归这条规则管，由 prompt 的不可信块与其他对抗变体覆盖。

仍然存在的边界：只有数字记号会被检查，用文字拼出来的数额（「九万九千」「ninety-nine thousand」）不会被 NUM 匹配到，这是 G1 的既有限制，本 change 没有改变它，也没有因它放宽。G8 允许 not_waste 的日志行引用 untrusted 里的数字，这些行会出现在 findings.json 的 judgments 与 HTML 的线索卡里（trap_web 就是这样），不是 finding；本 change 的 bait 变体要求这些数字在两个文件里一个都不出现，目前的 3 条回放都满足。

## 对 test_judge.py 的一处改动

`test_rejects_ungrounded_number` 用 waste 判断断言整条拒绝，正是被取消的行为。改为 not_waste 判断断言拒绝，waste 的情形在 test_judge_grounding.py 里断言脱敏。
