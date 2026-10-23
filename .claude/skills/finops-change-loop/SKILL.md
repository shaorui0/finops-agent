---
name: finops-change-loop
description: 本仓库每个改动的固定闭环：OpenSpec change → 实现 → 验收 → HTML 报告 + 博客笔记 → 一个 commit。用户说「做下一个 change」「按 loop 走」「提交这个改动」，或在本仓库开始任何代码/文档改动时使用。
---

# finops-change-loop

一个 change = 一个 OpenSpec change = 一个 commit。没有验收证据的 change 不提交。

## 步骤

1. **开 change**：`openspec new change <NNNN-slug>`（编号四位递增，看 `reports/` 最大号 +1）。写 proposal / tasks；tasks 里必须有一条「验收」，写明用什么命令或 eval 证明做完。
2. **实现**：只改 tasks 里列的东西。
3. **验收**：跑 tasks 里的验收命令，把输出原样存到 `openspec/changes/<id>/evidence.md`。失败就回到 2，不往下走。
4. **HTML 报告**：`reports/<NNNN-slug>.html`。内容：改了什么、为什么、验收证据、前后对比（有 eval 时给指标）。本地 HTML 文件，不发 Claude artifact。可以先写 md 再 `pandoc -s --metadata title=<slug> in.md -o reports/<NNNN-slug>.html`。
5. **博客笔记**：`notes/blog/<NNNN-slug>.md`。只列核心想法、踩的坑、反直觉的结论，bullet 即可，**不做写作润色**。
6. **提交**：`git add` 本 change 涉及的文件（不用 `-A`），commit message 首行 `<NNNN-slug>: <一句话>`，正文列验收结论。
7. **汇报验收**：在 main agent 里把验收结果告诉用户——通过/失败、关键输出、HTML 报告路径。没汇报不算做完。
8. 完成后 `openspec archive <id>`（可与下一个 change 一起做）。

## 硬规则

- 给用户看的 markdown 同时出 HTML。
- 公司数据（账单、账号号、资源 ID、内部代码）不进仓库；提交前 `git diff --cached` 扫一遍。
- 报告里的每个数字要能指回 evidence 或数据行。
- 涉及 AWS 写操作的 change 必须在 proposal 写明人工 gate 和回滚。
