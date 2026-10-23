## 1. 实现
- [x] 1.1 `eval/score.py` + `eval/baseline.json`
- [x] 1.2 `eval/test_score.py`
- [x] 1.3 `Makefile`
- [x] 1.4 `.github/workflows/ci.yml`

## 2. 文档
- [x] 2.1 README（eval、Progress 表）、WORKSPACE、REQUIREMENTS 覆盖面矩阵

## 3. 验收
- [x] 3.1 `make test`、`make check` 全绿
- [x] 3.2 `make eval` 通过且输出指标
- [x] 3.3 负向：踩陷阱 / 回退时闸门失败
- [x] 3.4 `openspec validate c0006-eval-ci`
- [x] 3.5 推到 GitHub 后 CI 绿
