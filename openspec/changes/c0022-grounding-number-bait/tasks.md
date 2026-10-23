## 1. 实现
- [x] 1.1 validate.py：结构化字段先校验，叙述含未验证数字时按从句脱敏（G9），再校验一遍，仍有则拒绝
- [x] 1.2 judge/__init__.py：redaction 写入 finding evidence、judgment、trace
## 2. 测试
- [x] 2.1 test_judge_grounding.py：脱敏保留 grounded 从句；title/hops；全 bait 标题；结构化字段仍拒绝；非 waste 仍拒绝；finding 与 trace 的记录
- [x] 2.2 test_adversarial.py：number_bait 不再是限制，9 个变体同一断言；新增 3 个变体并录 cassette（2 次调用）
## 3. 验收
- [x] 3.1 `make eval AWS_PORT=38566 PROM_PORT=38567 RUN=t19`：recall 1.0、savings_recall 1.0、gates pass
- [x] 3.2 `python3 -m eval.heldout` 与 main 逐字相同
- [x] 3.3 `python3 -W ignore -m unittest eval.test_adversarial eval.test_heldout finops_agent.test_judge_grounding` OK
- [x] 3.4 `make test`、`make check` 全绿；`openspec validate c0022-grounding-number-bait`
