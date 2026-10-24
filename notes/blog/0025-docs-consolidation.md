# 0025 docs-consolidation 原始笔记

- 诚实的成绩单要把样本内 1.0 和预注册 0.75 放在同一张表里，并写明每一层证明什么。只放 1.0，读者得到的是一个被调出来的数字。
- 起因：24 个 change 之后，README 的结果表还停在 c0005 的 7/12，ARCHITECTURE 写着判断层「进行中」，覆盖面矩阵里还有「计划、待建」。文档比代码老四个版本。
- 进度表不靠记忆：每个笔记最后一行是 `PROGRESS_ROW`，README 的行直接从那里取。c0011 的行用了「/」分隔，其余是「·」，合并时统一了。
- 数字全部抄自 EXPERIMENTS §7 和生成文档，没有重算。样本外两个世界标「已污染」，不是为了谦虚，是因为 c0023 对着它们的失败修过。
- 覆盖面矩阵的验证命令不能数全文里的「计划」：dry-run 计划是正常用词。改成只扫状态列，输出 0，两个依赖维护者的例外（真实 AWS 账号、主页 push）在表后单独列出。
- 写 BUILD_PROCESS 最有用的是翻调度记录：几次「不勾」的决定（D7、D8、D19、D3）都来自 agent 如实回报自己的结果不够强，判据因此收紧。这比勾满更能说明编排有效。
- 事故一条比一条朴素：worktree 里没有被 gitignore 的私有词表，所以泄漏扫描在合并后才拦下；两条分支各自绿，合并后全局状态泄漏；每合并一个 change 导读页就过期。
- 链接和英文标题检查是自写的小脚本，因为 `tools/check_rules.py` 的同类检查在并行的另一个 change 里。脚本先跑在改动前的状态，抓出 README 标题 `# finops-agent`（两个 ASCII 词）、REQUIREMENTS 里几个仓库外的路径、EXPERIMENTS 的 `judge/`。
- 坑：backtick 里写 API 路径（`/api/v1/series`）会被当成仓库路径检查，改成文字描述。
- 坑：README 表格里 `scenarios/` 这类相对简写要写全路径，否则检查找不到。
- 没做：FINOPS_SLO.md 里还有几个英文小标题（Waste budget、Busy but useless、Path cost），正文不在本 change 范围，留给它的主人。
PROGRESS_ROW: | c0025-docs-consolidation | 10-24 | 文档合并：README 三层结果与嵌图、ARCHITECTURE 补判断层与处置、NARRATIVE、MATURITY、BUILD_PROCESS、覆盖面矩阵、实验记录对抗段、导读页重建 | 诚实的成绩单要把样本内 1.0 和预注册 0.75 放在同一张表里，并写明每一层证明什么 | [报告](reports/0025-docs-consolidation.html) · [笔记](notes/blog/0025-docs-consolidation.md) · [叙事](docs/NARRATIVE.md) |
