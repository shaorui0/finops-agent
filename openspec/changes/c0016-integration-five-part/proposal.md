## Why

维护者要的是「测试数据能够清晰可见，也就是能够看到 status/spec -> diff -> 如何做/runbook -> 预防等等，都能看见」。testenv 的标准答案已经是五段式（c0014），remediate 已经能出处置计划（c0015 之前合入），但真正跑一次 agent，报告里看不到：finding 只有标题、证据表，没有「期望是什么、差多少、怎么处置、怎么不再发生」；处置计划要手动对 findings.json 再跑一次 CLI，判断层产出的 finding 根本没有处理器；finding 也不知道该通知谁。

## What Changes

- 每次运行都写 `runs/<id>/plans.json`（经 `finops_agent.remediate`），覆盖包括判断层产出在内的所有 finding；每个计划带 `reversal_cost`、`rollback`、审批说明，报告展示它们并声明没有执行任何命令。判断层的四种类型（nat_path_cost / cross_az_traffic / busy_but_useless / always_on_batch）在 `fivepart.py` 里补处理器，注册进 `remediate.HANDLERS`，不改 `remediate.py`。
- 新增 `finops_agent/fivepart.py`：对每个 finding 由类型和证据确定性算出 status / spec / diff（数字来自代码、SLO 配置，不抄 LLM 文本），runbook 取计划步骤（无计划的给建议），prevention 取 `finops_agent/prevention.py`。字段名与 testenv ground truth 一致，写入 `runs/<id>/fivepart.json`。
- 新增 `finops_agent/prevention.py`：finding 类型 -> 预防控制表（lifecycle policy、tag policy/SCP、AWS Config 规则、launch template / Terraform、`docs/FINOPS_SLO.md` 的巡检节奏、必须在 `config/alerts/finops.rules.yml` 里存在的告警名）。
- 报告：每张 finding 卡片按 现状 / 期望 / 差异 / 处置 / 预防 五个带标题的段落展示，证据收进折叠区；顶部新增「处置计划」总览表。
- finding 新增 `owner`（取自资源 tag，ASG 取成员实例的 owner，缺失为「未知」），计划的通知对象跟随它。
- Makefile：新增 `rot-demo`；`make test` 追加 `testenv.test_catalog`、`finops_agent.test_remediate`、`finops_agent.test_fivepart`。
- `FINOPS_NO_JUDGE=1`（等价于 `--no-judge`）：`make rot-demo` 用它，因为后两个月的世界没有 LLM cassette，不录制就没法回放（见 design 取舍）。

## Capabilities

### New Capabilities
- `five-part-report`：每次运行产出 plans.json 与 fivepart.json，报告每个 finding 卡片都是五段式，finding 带 owner。

### Modified Capabilities
（无）

## Impact

只动 `finops_agent/{__main__,analyze,report,fivepart,prevention}.py`、两个测试文件、`Makefile`、本 change 目录、笔记与报告。判断层 prompt 不变（`Lead` 与 `judge/` 未动），cassette 回放结果不变：eval recall 与 savings_recall 仍为 1.0。AWS 只读：计划里的写操作命令是给人看的文本，写明需人工审批与撤回成本，`fivepart.py` 不含任何进程执行（测试断言）。人工 gate 与回滚见每个计划的 `rollback` 与审批说明。
