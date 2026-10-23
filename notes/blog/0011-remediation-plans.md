# 0011-remediation-plans 博客笔记

- 发现到动手之间缺的不是自动化，是"撤回成本"这一列。同一个"删"，未挂载卷（先快照可重建）和孤儿快照（删了就没了）完全不是一个风险等级，计划必须把这差别写在最前面。
- 高撤回成本的动作，计划里连命令都不该给全：孤儿快照只给隔离打标，真正删除宽限期后另开审批；承诺只给建议。FA06 落到代码就是"没有命令"这个字段为空。
- "永不执行"要能被测试证明，不能靠自觉：用 AST 检查模块不 import subprocess/os，再在 apply 路径 mock 掉 subprocess.run/os.system 断言调用 0 次。
- 写脚本文件也是副作用：脚本不加执行位，头部带前置检查清单，逼人读完再跑。
- findings 里没有 owner 字段，"该通知谁"只能诚实地写"未知，先查"。计划层暴露了发现层缺的数据，这比硬编一个 owner 有用。
PROGRESS_ROW: | c0011-remediation-plans | 2026-10-24 | findings 转可审阅的 dry-run 修复计划（撤回成本/回滚/前置检查），apply 永不执行 | 高撤回成本的动作连命令都不给全（承诺只有建议，孤儿快照只隔离） | [报告](reports/0011-remediation-plans.html) / [笔记](notes/blog/0011-remediation-plans.md) |
