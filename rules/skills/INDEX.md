# Skills 索引

Skill 文件放在 `.claude/skills/`，Claude Code 会自动加载。遇到"怎么做 X"时先查这里。

| Skill | 用途 |
|---|---|
| `finops-change-loop` | 每个改动的固定闭环：OpenSpec change → 按阶段 commit → 验收 → HTML 报告 + 博客笔记 → 汇报 |
| `openspec-*` | OpenSpec 自带的 change 管理（new / continue / apply / verify / archive 等），由 `openspec init` 生成 |

新增 skill 的判据：同一个动作做了第二次，并且步骤能写成弱模型也能照做的清单。
