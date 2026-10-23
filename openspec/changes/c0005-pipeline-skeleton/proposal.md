## Why

有了测试环境（c0004），要让整条链路先跑通：采集 → 冻结快照 → 分析 → 可见性链 → 报告。骨架阶段只放确定性检测器，需要跨源判断的深层发现以 lead 的形式交给后面的判断层，这样第一次 eval 就能如实暴露 recall 缺口，而不是用启发式把它糊过去。

## What Changes

- `finops_agent/collect.py`：boto3 + Prometheus HTTP 只读采集，所有调用记 trace；输出冻结快照。
- `finops_agent/analyze.py`：按 METHOD 步骤组织的确定性检测器（M1 tag 与启动模板冲突、M2 二八与意外项、M3 未挂载卷/空闲 IP/停机实例存储/孤儿快照、M4 gp2→gp3、M5 SP 利用率）；跨源信号输出为 Lead；不变量检查（节省 ≤ 资源花费、非零节省必须有口径、必须有证据）。
- `finops_agent/visibility.py` + `config/visibility_requirements.yaml`：可见性链四环落地（①为人工给定的需求表，后续由判断层生成）。
- `finops_agent/report.py`：按 M0–M6 组织的 HTML 报告，每条 finding 展示推理链与证据表；附可见性缺口表与调用 trace。
- `python3 -m finops_agent run`：一条命令跑完。

## Capabilities

### New Capabilities
- `analysis-pipeline`：采集、快照、检测、不变量、报告的行为约定。
- `visibility-chain-impl`：c0002 规格的第一版实现。

### Modified Capabilities
（无）

## Impact

新增 `finops_agent/`、`config/`；运行产物写到 `runs/`（gitignore）。
