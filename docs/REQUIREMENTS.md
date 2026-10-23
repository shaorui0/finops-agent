# 需求分析：FinOps Agent

来源：语音 `2026-10-23_2311` / `2331` / `2335`（主），`1715` / `1758` / `1809`（FinOps 模型补充），`2026-10-20_1206`（面试叙事）。原文在 `context-infrastructure/contexts/daily_records/`，不进本仓库。

## 1. 一句话

做一个开源的 AWS FinOps Agent，用它作为「我是 Agent Engineer」的唯一旗舰证据：产品本身证明 FinOps 模型，构建过程（spec / change / eval / harness / context）证明 Agent 工程能力。FinOps 是载体，真正要练和要展示的是 Harness Engineering（R15）。

## 2. 需求拆解

| # | 需求 | 原话锚点 | 归属 |
|---|---|---|---|
| R1 | 定位是 **Agent Engineer / Agent Infra Engineer**，不是"做 Agent 应用开发"；面试"就面你一个东西"，必须能讲清楚真正的优点 | 2311、2331 末尾 | 叙事 |
| R2 | FinOps 分层能力：可见性/归因（识别 tag、owner，**还要校验打得对不对**）→ 明显浪费（闲置）→ 潜在浪费 → 可优化 → 自动打平到目标 spec | 1809、2335 | 本项目 |
| R3 | 浪费判据要分**潮汐短期 vs 长期**：短期冲高是正常弹性，长期不降才算浪费；成本告警本身是一套 SLA 体系，水位对 SLO 负责 | 1809、1758 | 本项目 |
| R4 | 治理顺序：先删 → 再降配 → 最后买承诺（SP/RI）；单位成本/对账（每次查询多少钱） | 1715、1758 | 本项目 |
| R5 | **第一轮只做分析**，结果交给我，再往下做 | 2335 | 本项目，M1 |
| R6 | 体现 LLM 能力边界与风险：幻觉、prompt 注入，三层——是什么 / 怎么触发 / 系统上如何避免；Context 定上限，Harness 定下限 | 2331、1758 | 本项目 |
| R7 | 评估与迭代：用什么指标、优化什么、为什么优化、结果是否可验证可复用；"不是去判断，而是去验证" | 2311、2331 | 本项目 |
| R8 | 过程即交付：每个 change 走 OpenSpec + 一个 commit，有验收 loop（被动 loop + 主动 loop），不能"只有开发没有测试" | 2335 | 本项目 |
| R9 | 每个 change 产出：本地 HTML 报告（**不是** Claude artifact）+ 博客想法（只整理核心内容，**不做写作优化**） | 2335 | 本项目 |
| R10 | cron 定期把项目的公理/规则蒸馏出来，形成本项目自己的 context 层（context、rules：axioms / skills / communication / soul / user / workspace），以 context-infrastructure 为母版 | 2335 | 本项目 |
| R11 | 发到 GitHub，标准是"完完整整真正好的开源项目" | 2335 | 本项目 |
| R12 | 该做成 skill 的都做成 skill，包括"每个 change 一个 commit"这个动作本身 | 2335 末尾 | 本项目 |
| R13 | prompt prehook：每次发 prompt 时，按我的认知/公理去校验或优化 prompt | 2335 开头 | **context-infrastructure，不在本仓库** |
| R14 | 每次验收结果都要告诉我（在 main agent 里汇报）；给我看的 markdown 一律同时出 HTML | 2341 | 本项目，进 change-loop |
| R16 | 接个人 AWS 账号，**只读**。只读由项目级 hook 实现并注册在本项目 `.claude/settings.json`，这本身是项目的生产安全设计；AWS 侧再加一层限制（独立账号、只读角色等）**先只列需求，不改 AWS** | 2344 | 本项目 |
| R17 | 可见性用 **本地搭的 Grafana**。指标分两步：先由 agent 分析「需要哪些 metric」，再去系统里查「有没有」，差集就是可见性缺口 | 2345 | 本项目 |
| R18 | 个人主页（shaorui0.github.io）顶部加 **FinOps Agent** 入口页：链到博客、GitHub 地址、我的思考过程、按阶段画出的流程图、每个 commit 的交付物；按阶段展示，不一次性端出 | 2345 | 主页仓库 + 本项目 |
| R15 | **项目目的是学 Harness Engineering 最佳实践、体现对 AI Agent 的掌控力**，不是为做而做，也不只为解决成本问题。取舍冲突时，过程的可展示性优先于功能广度 | 2341 | 全局原则 |

## 3. 交付物

| ID | 交付物 | 验收标准（可验证） | 对应需求 |
|---|---|---|---|
| D0 | 仓库骨架 + 本文档 + change-loop skill（本次 init commit） | `openspec list` 可用；`.claude/skills/finops-change-loop` 存在；init 有 HTML 报告 + 博客笔记 | R8 R9 R12 |
| D1 | **只读分析 Agent**：输入个人 AWS 账号的成本/资源数据（经只读 hook）+ 合成数据（给 eval 和 demo） → 输出分层报告（归因 / 闲置 / 潜在 / 可优化），每条 finding 带证据（资源 ID、指标、时间窗、计算式） | 在 demo 数据集上跑通；每条 finding 都能回溯到原始数据行；零写操作 | R2 R3 R4 R5 |
| D2 | **Eval harness**：植入已知浪费的合成数据集（golden set）+ 自动打分 | 指标至少：finding precision/recall、证据引用率、**savings ≤ 实际花费**不变量、跨运行稳定性；CI 里能跑 | R7 |
| D3 | **安全 / 风险用例集**：tag 值、资源名、描述字段里埋 prompt 注入；无证据数字（幻觉）检测 | 注入用例全部不改变 agent 行为；报告里无来源的数字 = 0 | R6 |
| D4 | 修复计划（dry-run）：把 finding 转成可审阅的变更计划，人工 gate 后才执行 | 默认只输出 plan；执行路径需要显式确认；有回滚说明 | R2 R4 |
| D1b | 可见性缺口分析：agent 先列所需 metric，再查本地 Grafana / 数据源里有没有，输出缺口表 | 缺口表每行有「需要的理由」和「查询证据」 | R17 |
| D5 | 主动 loop：cron 定期跑分析 + eval 回归 + 公理蒸馏，写进 `context/` | 每次运行留一份可 diff 的产物；回归下降会报出来 | R8 R10 |
| D6 | 开源打磨：README、架构图、quickstart（demo 数据 5 分钟跑起来）、LICENSE、贡献指南 | 新人 clone 后不需要 AWS 账号即可跑 demo | R11 |
| D7 | 面试叙事：一页「这个项目证明了什么」，按 R1 的 Agent Engineer 口径 | 每个论点链接到具体 change / eval 结果 | R1 |
| D8 | 主页 FinOps Agent 页：阶段时间线（每个 change → 交付物 → 报告/博客链接）+ GitHub 链接 | 页面从本仓库 `reports/` 和 git log 生成，新 change 提交后可重建；导航栏有入口 | R18 |
| D9 | AWS 侧只读加固需求清单（只分析，不动 AWS） | `docs/aws_account_hardening.md`，每条写明防的是什么、hook 层为什么挡不住 | R16 |
| X1 | prompt prehook（UserPromptSubmit） | — | R13，另起，挂在 context-infrastructure |

里程碑：**M0** = D0（本次）→ **M1** = D1 + D2 最小版（R5 说的"先做分析，结果给我"在这里停一次）→ M2 = D3 → M3 = D4 → M4 = D5 → M5 = D6 + D7 发布。

## 4. 设计约束

- **公司数据零进入**。雇主的账单、资源 ID、账号号、内部代码都不能进仓库。只用合成数据，或用户自己的个人 AWS 账号（只读角色）。
- **只读优先**。M1–M2 全程无写 API；写路径（D4）单独 gate。两层防线：项目 hook（`hooks/aws_readonly_guard.py`，拦 agent 发出的 aws CLI 写操作，fail-closed）＋ AWS 侧 IAM（D9，真正的保证；hook 挡不住 SDK 直连和人手误操作）。
- **数字必须有出处**。这条来自以前做成本可见性服务的教训：报告里推荐的 savings 比花费本身还大（资源重复计 + 单价错）。在这里它直接变成 D2 的硬不变量，也是面试里最有说服力的"为什么要做 eval"。
- **LLM 只做判断层**。拉数、聚合、计算交给确定性代码（脚本/SQL），LLM 负责归类、解释、排序和计划；这样每个数字都能复算。
- 每个 change：`openspec` change → 实现 → 验收（测试/eval）→ HTML 报告 + 博客笔记 → 一个 commit。流程写在 `.claude/skills/finops-change-loop/SKILL.md`。

## 5. Agent Engineer 叙事映射（D7 的骨架）

| 面试主题 | 在本项目里的证据 |
|---|---|
| Context engineering（上限） | `context/` 蒸馏层；FinOps 领域模型作为 context 喂给 agent |
| Harness（下限） | 只读边界、注入隔离、写操作 gate |
| 幻觉 / 注入 | D3 用例集 + 无出处数字检测 |
| 评估与迭代 | D2 golden set + 指标 + 每次 change 的前后对比 |
| Spec 驱动 | OpenSpec change 历史 = 设计决策留痕 |
| 自动化 loop | 被动：CI / hook；主动：cron（D5） |

## 6. 已确认（2026-10-23 23:44–23:45）

| Q | 决定 |
|---|---|
| Q1 数据源 | 个人 AWS 账号，只读（R16）；合成数据仍用于 eval 和 demo |
| Q2 可见性 | Grafana，本地搭（R17） |
| Q3 LICENSE | MIT |
| Q4 名字 | GitHub 仓库 `finops-agent`（FinOps Agent） |

## 7. 待确认

- Q5 个人主页是哪个仓库？`blog-system` 部署在 `shaorui0.github.io/tech`，根域名 `shaorui0.github.io` 的仓库没在本地找到。
