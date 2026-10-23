## 1. Ring 1 in words
- [x] 1.1 `visibility_llm.py`：prompt v4（signal / concept / terms / scope，不要 name）、`build_prompt(sample=)`、校验
- [x] 1.2 录制 cassette（预算 ≤ 15 次调用，prompt 迭代 ≤ 2 轮）

## 2. Ring 2 发现与 ring 4 混合状态
- [x] 2.1 `visibility.py`：`fetch_catalog`、`discover`、`ring2(catalog=)`、`ring4(mix=)`
- [x] 2.2 评审路径不变：`visibility.json` gaps 前后 diff、`make eval` 指标不变

## 3. 评估
- [x] 3.1 `eval/score_visibility.py`：words-only 打分、`--samples N`、缺口表加发现结果和 c/p/m
- [x] 3.2 N=5 采样录进 cassette，均值在 replay 下可复现

## 4. 测试
- [x] 4.1 `finops_agent/test_visibility.py`、`finops_agent/test_visibility_llm.py`

## 5. 验收
- [x] 5.1 `python3 -W ignore -m unittest finops_agent.test_visibility finops_agent.test_visibility_llm`
- [x] 5.2 `python3 -m eval.score_visibility --samples 5`（replay）：mean overlap ≥ 0.8，未达标如实报
- [x] 5.3 缺口表：派生（ring-2 发现后）对评审，②–④ 环，测试指标服务器
- [x] 5.4 评审路径 gaps diff + `make eval` 指标不变
- [x] 5.5 `make test`、`make check` 全绿
- [x] 5.6 `openspec validate c0020-visibility-ring1-stable`
