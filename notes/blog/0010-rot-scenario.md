# 0010-rot-scenario 博客笔记

- 两次运行不可能出现 regressed。`resolved` 只在"上次 open、这次消失"时才有内容，regressed 又要求它之后再回来，所以最少三个周期。第一版设计想在两次里塞下 resolved / regressed / new，写 design 时才发现 `diff_state` 的定义做不到。
- 回归要选"同一个 key 能真实回来"的东西。key 含资源 ID，AWS 不会重用已释放的 EIP allocation id，所以"EIP 又漏了"是 new 不是 regressed；同一个卷被 terraform 漂移改回 gp2 才是真回归。"新 ID 的同类问题"和"同一个问题回来"是两件事，rot 指标里要分开数。
- 场景写成覆盖层而不是复制一份世界：只写差异，价格/用量/事故时间线仍是单一来源；场景文件读起来就是故事。
- 场景的标准答案放进场景文件的 `scenario.expect`，测试真跑 agent 三次逐项比对。场景一改坏就红，不靠人眼看演示输出。
- 踩坑：演示脚本里端口被上次手工探测遗留的 metrics 进程占着，新服务绑定失败被 `2>/dev/null` 吞掉，agent 悄悄连到了旧的基础世界。结果看起来"差不多对"，因为大多数 finding 不依赖指标。脚本现在启动前检查端口，被占就报错。吞掉 stderr 的脚本最怕这种"看起来对"。
- 基础世界不变用 sha256（`World.raw` + 全部成本行）证明，比"测试还绿"强：测试只覆盖我想到的断言。
PROGRESS_ROW: | c0010-rot-scenario | 2026-10-24 | 合成账号加 `--world` 与下个月场景（next_month / month_after 覆盖层），`scripts/rot_demo.sh` 三周期演示 resolved / regressed / new | 两次运行不可能出现 regressed，至少要三个周期 | [报告](reports/0010-rot-scenario.html) · [笔记](notes/blog/0010-rot-scenario.md) |
