## Why

仓库准备开源，外部贡献者没有可读的入口：怎么搭环境、怎么跑测试、改动流程是什么、硬规则有哪些，现在只散落在 `CLAUDE.md`、skill 和各 change 里。模块职责和运行产物的字段也没有集中说明，要读代码才能知道。

## What Changes

- 新增 `CONTRIBUTING.md`：环境、测试命令、改动闭环摘要、硬规则、语言规则、如何加检测器、如何加测试场景和标准答案、eval 基线怎么卡 CI。
- 新增 `docs/ARCHITECTURE.md`：`finops_agent/`、`testenv/`、`eval/`、`config/`、`hooks/`、`tools/` 的模块地图，以及 8 个运行产物的数据契约。字段清单来自代码和一次真实运行。判断层与处置方案标注为进行中。

## Capabilities

### New Capabilities
- `oss-docs`：贡献者文档的准确性约定。

### Modified Capabilities
（无）

## Impact

只增加两个文档，不改代码和配置。README 不在本 change 范围内。
