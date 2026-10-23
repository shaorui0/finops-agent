## 1. 目标与推导
- [x] 1.1 `config/cost_goals.yaml`（中文，业务语言，来源 METHOD / FINOPS_SLO）
- [x] 1.2 `finops_agent/visibility_llm.py`（prompt、解析、校验、`derive` CLI）
- [x] 1.3 录制 cassette（预算 ≤ 10 次调用）

## 2. 打分
- [x] 2.1 `eval/score_visibility.py`（匹配规则、recall / precision / 逐 SLI 表、②–④ 环缺口对比）
- [x] 2.2 prompt 迭代 ≤ 3 轮，每轮记 evidence.md

## 3. 测试
- [x] 3.1 `finops_agent/test_visibility_llm.py`（prompt 不含指标名、schema 校验、replay 可被 ②–④ 环使用、打分单测）

## 4. 验收
- [x] 4.1 `python3 -m unittest finops_agent.test_visibility_llm`
- [x] 4.2 replay 跑 `derive`，两次输出一致
- [x] 4.3 `python3 -m eval.score_visibility` 输出 overlap / precision / 逐 SLI 表；target ≥ 0.8，未达标如实报
- [x] 4.4 ②–④ 环缺口对比表
- [x] 4.5 `make test`、`make check` 全绿（Makefile 不在本 change 范围，测试文件单独跑）
- [x] 4.6 `openspec validate c0017-visibility-ring1-llm`
