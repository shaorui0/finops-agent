## Why

有了 ground truth（c0004）和能跑通的流水线（c0005），还缺一个把两者对上的打分器，以及一道自动的闸：陷阱被踩、不变量被破、指标回退，都要让 CI 变红。否则"评估与迭代"只是一句话。

## What Changes

- `eval/score.py`：对照 `testenv/world.yaml` 打分（recall、按金额加权的 recall、precision、金额准确率、方法步骤一致率、按推理深度拆分的 recall、陷阱违规、不变量）；带 baseline 回归闸。
- `eval/baseline.json`：当前确定性层的基线（recall 0.58、金额加权 0.19、深层 0.44），以后每次改进必须不低于它。
- `eval/test_score.py`：打分器自己的负向测试（踩陷阱、注入目标被跳过、回退、跨步骤误匹配、金额越界、不变量）。
- `Makefile`：`make test / check / demo / eval`。
- `.github/workflows/ci.yml`：check → test → eval，运行报告作为 artifact 上传。

## Capabilities

### New Capabilities
- `eval-harness`：打分口径、闸门与基线的约定。

### Modified Capabilities
（无）

## Impact

新增 `eval/`、`Makefile`、`.github/workflows/ci.yml`。
