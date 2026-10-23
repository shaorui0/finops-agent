## Why

可见性链第 ① 环现在是人工写的 `config/visibility_requirements.yaml`（c0002/c0005）。要证明「以终为始」也能交给 LLM：只给成本目标，不给任何现有指标，让它反推需要看到什么，再拿人工评审过的那份当标准答案打分。这是一个实验，结果如实报，包括没达标的情况。

## What Changes

- 新增 `config/cost_goals.yaml`：这个账号的成本目标，只用业务语言（浪费比例、不砍 SLO 余量、承诺折扣利用率、共享成本可归因、单位工作成本……），依据 `docs/METHOD.md` 和 `docs/FINOPS_SLO.md`，不抄 `visibility_requirements.yaml` 的结构和 SLI id。
- 新增 `finops_agent/visibility_llm.py`：`python3 -m finops_agent.visibility_llm derive --goals ... --out ...`，经 `finops_agent/llm.py`（默认 replay）产出同 schema 的第 ① 环 YAML（外加 `not_metric_observable`，放不能用时序指标衡量的目标）。prompt 里不含服务器上的指标名，也不含评审文件里的名字（测试断言）。
- 新增 `eval/score_visibility.py`：派生版对评审版的覆盖率（recall）、精确率、逐 SLI 表；`--snapshot --prom` 时再跑 ②–④ 环出对比缺口表。
- 新增 cassette（只加不改）和 `finops_agent/test_visibility_llm.py`。

## Capabilities

### New Capabilities
- `visibility-ring1-llm`：从目标文件由 LLM 推出第 ① 环，并对照评审版打分。

### Modified Capabilities
（无）

## Impact

只加文件，不改 `visibility.py`、`__main__.py`、Makefile。LLM 调用预算 ≤ 10，实际用量写在 evidence。不碰 AWS（只读，且本 change 只读测试服务器）。prompt 迭代最多 3 轮，每轮的改动和得分记在 evidence。
