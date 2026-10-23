## 1. 实现
- [x] 1.1 collect（只读采集 + trace + 快照）
- [x] 1.2 analyze（确定性检测器、Lead、不变量）
- [x] 1.3 visibility（四环）+ `config/visibility_requirements.yaml`
- [x] 1.4 report + CLI

## 2. 测试
- [x] 2.1 `finops_agent/test_pipeline.py`：两个服务器进程内启动，全链路 9 项断言

## 3. 文档
- [x] 3.1 README quickstart、WORKSPACE、REQUIREMENTS 覆盖面矩阵

## 4. 验收
- [x] 4.1 `python3 -m unittest finops_agent.test_pipeline` 全绿
- [x] 4.2 对着运行中的两个服务器跑 `python3 -m finops_agent run`，报告可打开
- [x] 4.3 回归：testenv、tools、hook 单测与 check_rules
- [x] 4.4 `openspec validate c0005-pipeline-skeleton`
