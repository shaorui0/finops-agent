## 1. LLM 客户端
- [x] 1.1 `finops_agent/llm.py`：replay / record / live，cassette 键 sha256(model + prompt)，缺 cassette 报错
- [x] 1.2 `finops_agent/test_llm.py`

## 2. 判断层
- [x] 2.1 取证器 `judge/gather.py`：cost_growth、unattributed_transfer、fleet_work、idle_window；候选数字全部由代码算
- [x] 2.2 idle_window 线索生成器（按小时 CPU）
- [x] 2.3 `judge/prompt.py`、`judge/validate.py`（严格 JSON、白名单资源、数字落地、意图 tag 护栏）
- [x] 2.4 `judge/__init__.py`：每条线索独立调用，线程池并发，trace 记录
- [x] 2.5 `finops_agent/test_judge.py`：校验规则、prompt 隔离、并发、trace 字段、注入

## 3. 接线
- [x] 3.1 `__main__` 接入判断层（`--no-judge` 可关）；`Lead` 增加 `kind` / `params`
- [x] 3.2 报告：线索卡片显示判断，新增「Agent 成本」
- [x] 3.3 `Makefile`（FINOPS_LLM_MODE 默认 replay，`make record`）、CI 显式 replay
- [x] 3.4 `test_pipeline` 增加判断层端到端断言

## 4. 录制与基线
- [x] 4.1 用真实 `claude -p` 录制 cassette 并提交
- [x] 4.2 新指标通过后 `--write-baseline`

## 5. 验收
- [x] 5.1 `make eval AWS_PORT=15566 PROM_PORT=15990 RUN=t1`：deep_recall >= 0.8，savings_recall >= 0.7，门禁通过
- [x] 5.2 replay：PATH 里没有 claude 也能跑；trace 里 `"source": "llm"` >= 5
- [x] 5.3 `make test`、`make check` 全绿
- [x] 5.4 `openspec validate c0009-judgment-layer`
