# 0002-visibility-chain 博客笔记

- 以终为始：先问"成本目标用什么 SLI 衡量"，再去找 metric。反过来做（先盘点有什么 metric）会得到一堆指标，却回答不了"够不够"。
- 找 metric 本身是一个任务：先出计划（去哪找、查什么、什么算找到），再执行；执行的每条查询都必须在计划里。这条就是可审计性。
- 四环各自产出、各自验收，上一环的产物是下一环的输入。这样每一环都能单独评估，agent 错在哪一环一眼可见。
- "体现 Harness Engineering"本身要可验收：把它拆成 13 个面、每面写实现和状态，比一句"全面"有说服力。
- 过程教训：c0001 一个 commit 塞了五件事，看不出阶段。改成按阶段 commit（proposal → spec+tasks → impl → docs → acceptance），并且把这条写进了 change-loop skill。
