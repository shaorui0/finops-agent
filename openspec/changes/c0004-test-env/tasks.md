## 1. 合成账号
- [x] 1.1 `testenv/world.yaml`：资源、用量、价格、ground truth（12 finding / 4 trap / 3 gap）
- [x] 1.2 `testenv/world.py`：成本行（含 SP 摊销）与指标形状

## 2. 服务器
- [x] 2.1 test-aws-server（botocore shape 驱动的序列化、只读、调用日志）
- [x] 2.2 test-metrics-server（Prometheus API + PromQL 子集）

## 3. 文档
- [x] 3.1 `docs/METHOD.md`（M0–M6）
- [x] 3.2 `testenv/README.md`、`rules/WORKSPACE.md`、`requirements.txt`

## 4. 验收
- [x] 4.1 `python3 -m unittest testenv.test_testenv` 全绿（自洽 + 两个服务器 round trip）
- [x] 4.2 aws CLI 走 `--endpoint-url` 可用，且经过只读 hook
- [x] 4.3 `tools/check_rules.py` 与既有单测全绿
- [x] 4.4 `openspec validate c0004-test-env`
