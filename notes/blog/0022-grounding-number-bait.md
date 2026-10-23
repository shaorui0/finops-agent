- fail closed 不等于安全。校验器对一条正确结论说不，攻击者就赢了：不用骗过模型，只要让模型老实地复述注入文字。
- 数字 grounding 保护的是「展示出去的数字」，不是「叙述有权否决 finding」。金额来自代码算的候选，叙述里的数字本来就不承重，所以否决权可以收回，展示的约束不动。
- 修法放在校验器而不是 prompt：cassette key 含 prompt，改 prompt 要重录全部 cassette 再重证三组指标；模型这次没错，没理由动它。已有 cassette 全部原样回放，只多录 2 条（$0.0452）。
- 脱敏后必须再校验一遍，仍有未验证数字就拒绝。「先修再信」不行，「修完再验」才行。
- 留痕要分开放：finding 上只记长度和 sha256 前缀，不记被移除的文字（否则 planted 数字又进了 findings.json）；原文和数字放 trace。审计靠 sha256 对得上。
- 踩坑：测试里查「planted 数字不在 findings.json」，子串匹配会误中 49.99999928 里的 99999，要按整数边界匹配。
- 踩坑：切从句不能切 ASCII 逗号，否则 $99,999 被切成两半，数字落到两个从句里都不超标。
- 新增的 batch 变体里模型根本没复述 bait，不触发脱敏；变体只保证「复述了才有脱敏，没复述就没有」，两种都被断言。
- 没有改的：英文数字词（ninety-nine thousand）NUM 本来就抓不到，这是 G1 的既有限制，不是这次放松的。
PROGRESS_ROW: | c0022-grounding-number-bait | 2026-10-24 | 叙述里的未验证数字不再否决整条 waste finding：结构化字段合法时按从句脱敏并留痕，number_bait 的 $1,469 finding 保住；新增 3 个 bait 变体 | 校验器的 fail closed 本身是攻击面：不改 prompt、不放松 grounding，只改「谁有否决权」 | [报告](reports/0022-grounding-number-bait.html) · [笔记](notes/blog/0022-grounding-number-bait.md) |
