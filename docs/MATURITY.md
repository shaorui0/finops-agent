# 成熟度：完成标准（DoD）逐条核对

这份表是整个项目的唯一停机判据：20 条断言，每条有状态、证据链接和可复现的验证命令。状态是写文档这一刻的事实，不是目标。构建过程见 [`BUILD_PROCESS.md`](BUILD_PROCESS.md)，对外叙事见 [`NARRATIVE.md`](NARRATIVE.md)。

状态含义：完成，表示判据已满足且主 agent 在合并后的主干上重新验证过；待定，表示还差一步，原因写在表后。

| 编号 | 断言 | 状态 | 证据 | 验证命令 |
|---|---|---|---|---|
| D1 | 判断层回答线索：深层 recall 不低于 0.8，savings_recall 不低于 0.7，陷阱违规为 0 | 完成（样本内，见 D20） | [`openspec/changes/c0009-judgment-layer/evidence.md`](../openspec/changes/c0009-judgment-layer/evidence.md) | `make eval`，输出 recall 1.0、savings_recall 1.0、深层 1.0、`gates: pass` |
| D2 | LLM 调用可录制可回放：CI 没有 API key，用 cassette 跑判断层且为绿 | 完成 | [`openspec/changes/c0009-judgment-layer/evidence.md`](../openspec/changes/c0009-judgment-layer/evidence.md)、[`finops_agent/llm.py`](../finops_agent/llm.py) | GitHub Actions 成功；`grep -c '"source": "llm"' runs/ci/trace.jsonl` 不小于 5（本地 `make eval RUN=ci` 同判据；复核时 PATH 不含 claude、无 API key，7 次 llm 调用全部 `mode=replay`） |
| D3 | 对抗用例集：至少 6 种注入变体加输出数字溯源检查，全部通过 | 完成 | [`openspec/changes/c0015-adversarial-and-experiments/evidence.md`](../openspec/changes/c0015-adversarial-and-experiments/evidence.md)、[`openspec/changes/c0022-grounding-number-bait/evidence.md`](../openspec/changes/c0022-grounding-number-bait/evidence.md) | `python3 -W ignore -m unittest eval.test_adversarial -v`，12 个变体；number_bait 一度压掉真 finding，c0022 后保留 |
| D4 | 修复计划：有节省的发现都有 dry-run 计划（撤回成本、回滚），无 `--approve` 不可执行 | 完成 | [`openspec/changes/c0011-remediation-plans/evidence.md`](../openspec/changes/c0011-remediation-plans/evidence.md)、[`openspec/changes/c0016-integration-five-part/evidence.md`](../openspec/changes/c0016-integration-five-part/evidence.md) | `python3 -W ignore -m unittest finops_agent.test_remediate`；`plans.json` 每条含 `reversal_cost`、`rollback`，`dry_run` 为 true，`executed` 为 false |
| D5 | agent 可观测性：trace 中每次 LLM 调用有 tokens、延迟、成本；报告有 Agent 成本一节 | 完成 | [`openspec/changes/c0009-judgment-layer/evidence.md`](../openspec/changes/c0009-judgment-layer/evidence.md) | 断言 trace 字段（`tokens_in`、`tokens_out`、`latency_ms`、`cost_usd`）；`grep -c "Agent 成本" runs/<id>/report.html` 为 1 |
| D6 | 上下文隔离：每条线索独立上下文判断，prompt 不含其他线索的证据 | 完成 | [`finops_agent/judge/prompt.py`](../finops_agent/judge/prompt.py)、[`finops_agent/test_judge.py`](../finops_agent/test_judge.py) | `python3 -W ignore -m unittest finops_agent.test_judge`（含隔离用例） |
| D7 | 第 ① 环可由 LLM 从成本目标推导，与审阅版的重合度不低于 0.8，且是不少于 5 次采样的均值 | 完成（判据收紧后） | [`openspec/changes/c0017-visibility-ring1-llm/evidence.md`](../openspec/changes/c0017-visibility-ring1-llm/evidence.md)、[`openspec/changes/c0020-visibility-ring1-stable/evidence.md`](../openspec/changes/c0020-visibility-ring1-stable/evidence.md) | `python3 -m eval.score_visibility --samples 5`（回放）：均值 0.964，最小 0.91，最大 1.00。c0017 单次 0.91，重采样均值约 0.79；c0020 的量尺不同（对第 ② 环发现的名字打分），两个数不可直接比 |
| D8 | rot 场景：连续三个周期（基础、next_month、month_after），累计出现 resolved、regressed、new | 完成 | [`openspec/changes/c0010-rot-scenario/evidence.md`](../openspec/changes/c0010-rot-scenario/evidence.md)、[`openspec/changes/c0016-integration-five-part/evidence.md`](../openspec/changes/c0016-integration-five-part/evidence.md) | `make rot-demo`。判据原文写「两次运行」，在 `diff_state` 语义下不可能出现 regressed，据此改成三个周期 |
| D9 | 规则同步工具：对比母版产出建议 diff，不自动合入 | 完成 | [`openspec/changes/c0012-rules-sync/evidence.md`](../openspec/changes/c0012-rules-sync/evidence.md) | `python3 -m unittest discover -s tools -p test_sync_rules.py`（夹具母版目录） |
| D10 | 开源完整：CONTRIBUTING、ARCHITECTURE；临时目录全新 clone 跑 `make test && make eval` 为绿 | 待定：本波文档合入后由主 agent 只读复核 | [`CONTRIBUTING.md`](../CONTRIBUTING.md)、[`ARCHITECTURE.md`](ARCHITECTURE.md)、[`openspec/changes/c0013-oss-docs/evidence.md`](../openspec/changes/c0013-oss-docs/evidence.md) | 在临时目录全新 clone，跑 `make test && make eval` |
| D11 | NARRATIVE.md：每个能力声明链接到 change、eval 或文件，链接全部可解析 | 完成（主线复核：`make check` 含 `--docs` 链接检查通过） | [`NARRATIVE.md`](NARRATIVE.md)、[`openspec/changes/c0025-docs-consolidation/evidence.md`](../openspec/changes/c0025-docs-consolidation/evidence.md) | `python3 tools/check_rules.py`（链接检查）；evidence 里有自写脚本的输出 |
| D12 | 覆盖面矩阵没有「计划、待建、待设计」，除列明的人工阻塞项 | 完成（主线复核：§5 状态列 0 处计划/待建/待设计，例外 2 项已列明） | [`REQUIREMENTS.md`](REQUIREMENTS.md) §5 | `sed -n '/^## 5\./,/^## 6\./p' docs/REQUIREMENTS.md \| awk -F'\|' 'NF>4{print $4}' \| grep -cE '计划\|待建\|待设计'` 输出 0（状态列无未交付字样）；两个依赖维护者的例外在表后单独列出 |
| D13 | 主页 FinOps Agent 入口：本地构建含链接，push 走 escrow | 待定：等维护者批准主页 push | 主页在另一个仓库，不在本仓库 | 构建产物含链接，加 escrow 表（见 [`BUILD_PROCESS.md`](BUILD_PROCESS.md)） |
| D14 | prompt prehook：在个人 context 仓库内实现并测试，启用走 escrow | 完成 | 在另一个仓库，本仓库只记结论 | 该仓库内 hook 单测 10/10；「这个方案怎么验证它可靠」注入公理提示，「跑」无注入 |
| D15 | 措辞与叙事符合维护者口径 | 待定：等维护者通读 | [`NARRATIVE.md`](NARRATIVE.md)、[`../README.md`](../README.md) | 人读，没有机器验证 |
| D16 | 新增文档与报告为中文 | 完成（主线复核：`make check` 含 `--docs` 标题语言检查通过） | 本 change 的 evidence | `python3 tools/check_rules.py`（英文标题检查）；evidence 里有自写脚本的输出 |
| D17 | 每条标准答案与报告里每条发现都呈现五段：现状、期望、差异、处置、预防；testenv 有可读的场景目录页 | 完成 | [`openspec/changes/c0014-testenv-catalog/evidence.md`](../openspec/changes/c0014-testenv-catalog/evidence.md)、[`openspec/changes/c0016-integration-five-part/evidence.md`](../openspec/changes/c0016-integration-five-part/evidence.md)、[`reports/testenv-catalog.html`](../reports/testenv-catalog.html) | `python3 -W ignore -m unittest testenv.test_catalog finops_agent.test_fivepart`；`report.html` 每个五段小标题的数量等于发现数 |
| D18 | 人读层：至少 6 张图（mermaid 源加渲染 SVG），README 与 ARCHITECTURE 引用，导读页串起报告、图、表 | 完成（主线复核：6 张图、README 与 ARCHITECTURE 已嵌图、导读页 7 项测试通过） | [`openspec/changes/c0019-human-read-layer/evidence.md`](../openspec/changes/c0019-human-read-layer/evidence.md)、[`docs/diagrams/README.md`](diagrams/README.md)、[`../reports/index.html`](../reports/index.html) | `docs/diagrams/render.sh` 六图退出码全 0；`python3 -m unittest tools.test_build_index`；`grep -c "diagrams/.*svg" README.md docs/ARCHITECTURE.md` |
| D19 | 省钱核实：对 resolved 的发现用前后两期 Cost Explorer 数据算实际节省并与预测对比，场景数据中至少一条实现率不为 100% 且偏差原因被正确归类 | 完成（判据收紧后） | [`SAVINGS_VERIFICATION.md`](SAVINGS_VERIFICATION.md)、[`openspec/changes/c0018-savings-verification/evidence.md`](../openspec/changes/c0018-savings-verification/evidence.md)、[`openspec/changes/c0021-savings-verification-real-deviations/evidence.md`](../openspec/changes/c0021-savings-verification-real-deviations/evidence.md) | `bash scripts/verify_savings.sh`；`python3 -W ignore -m unittest finops_agent.test_verify_savings`。场景链 5 条：预测 $744.21，实现 $140.60（18.9%），偏差四类各有归因，账单分解精确闭合 |
| D20 | 评估与优化实验记录：判断层每轮调优的改动、指标、取舍，样本内与样本外分开报 | 完成 | [`../eval/EXPERIMENTS.md`](../eval/EXPERIMENTS.md)、[`openspec/changes/c0015-adversarial-and-experiments/evidence.md`](../openspec/changes/c0015-adversarial-and-experiments/evidence.md)、[`openspec/changes/c0024-fresh-heldout/evidence.md`](../openspec/changes/c0024-fresh-heldout/evidence.md) | `python3 -m eval.heldout`：基础世界、两个已污染的样本外世界、预注册的 fresh_world 四行分开 |

## 收紧过的判据

四条判据在构建中被收紧，原因都来自 agent 自己的诚实回报，不是我事后放宽：

- D7：单次采样 0.91 是运气好的一次（重采样 0.82、0.64），判据改成不少于 5 次采样的均值。
- D8：两次运行不可能出现 regressed，判据改成三个周期。
- D19：首版 4 条核实全是 100%，那是零假设结果，判据加上「至少一条实现率不为 100%」。
- D3：9 个变体里 number_bait 压掉了真实 finding，所以没有勾，由 c0022 修复后才算完成。

## 还没有勾的三条

- D10：新 clone 实跑要等本波文档合入主干后由主 agent 只读复核。
- D13：主页入口在另一个仓库，本地构建可以做，push 需要维护者批准。
- D15：措辞与叙事是否符合口径只能由维护者通读判断。

另有一项不在 D 列表里的阻塞：接入个人 AWS 只读账号，等维护者建好 profile。没有它，所有数字都来自合成账号。
