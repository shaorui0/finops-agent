# c0026-code-wrapup 验收证据

## 1. make test（完整）
`make test` 退出码 0。按目录发现：hooks 3 个、tools 29 个、finops_agent 160 个、eval 35 个、testenv 35 个测试，全部 OK（含 test_analyze / test_verify_savings / test_visibility / test_visibility_llm / test_judge_grounding / eval.test_adversarial / eval.test_heldout）。进程内服务器绑定端口 0；eval/heldout.py 用 47500-47599 块。

## 2. 不变量（前后对比）
- `make eval AWS_PORT=44566 PROM_PORT=44567 RUN=t22`：前后输出同为 recall 1.0、savings_recall 1.0、precision 1.0、savings_accuracy 0.9167、leads 7、gates: pass；runs/t22/findings.json 与 slo.json 前后逐字节一致。
- `python3 -m eval.heldout`（FINOPS_HELDOUT_PORTS=44570-44580）前后 diff：只有临时目录路径不同，四个世界的指标行一致。
- `scripts/rot_demo.sh`（FINOPS_NO_JUDGE=1）前后 diff 为空：rot-2 resolved=3 new=1，rot-3 regressed=1，not_redetected=0。
- 未改 prompt 文本、cassette、docs。

## 3. 新检查（D11 / D16）在 main 上的失败清单
`python3 tools/check_rules.py --docs`（退出码 1）：
```
FAIL README.md:1: heading not in Chinese (finops-agent)
FAIL docs/DISTILLATION.md:14: dangling path `skills/INDEX.md`
FAIL docs/FINOPS_SLO.md:37: heading not in Chinese (Waste budget)
FAIL docs/FINOPS_SLO.md:79: heading not in Chinese (Busy but useless)
FAIL docs/FINOPS_SLO.md:83: heading not in Chinese (Path cost)
FAIL eval/EXPERIMENTS.md:222: dangling path `judge/gather.py`
```
这些由 t10 的文档改写去修，本 change 不改 docs。`make check`（不带 --docs）通过。

## 4. 默认端口
`python3 -c "from eval import heldout as h; print(h.PORT_RANGE)"`（无环境变量）→ `range(47500, 47600)`；设置 FINOPS_HELDOUT_PORTS=44570-44580 → `range(44570, 44581)`。

## 5. 交接
文档改写合并后，由主 agent 把 .github/workflows/ci.yml 里 `DOCS_CHECK: ""` 改为 `"1"`，并把本地 `make check` 默认改为带 --docs（Makefile 的 `check` 目前只在 DOCS_CHECK=1 时带）。
