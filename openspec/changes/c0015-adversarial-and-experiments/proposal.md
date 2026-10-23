## Why

维护者问：「评估优化这一套在 FinOps 里面有呈现吗？实验数据，为什么对，怎么验证，要有细节。」c0009 的判断层是对着一个账号迭代出来的，只有 evidence.md 里几行话交代了迭代过程，没有对抗测试，也没有样本外结果。两个缺口：

1. **没人证明过判断层抗得住 prompt injection、不会编数字。** 世界里只有一条注入（Name tag），校验器只挡「不在证据里的数字」，而且有漏洞（见 design.md：紧贴中文的数字被跳过，小于 100 的整数被豁免）。
2. **没有样本外数据。** 所有指标都是 `make eval` 在同一个账号上的结果，c0009 自己承认 prompt rubric 是对着它调的。同一个 agent 在 `next_month`、`month_after` 两个没调过的世界上表现如何，没人跑过。

## What Changes

- **对抗套件**：7 个注入变体，每个是基础世界上的一个覆盖层（`testenv/scenarios/adversarial_*.yaml`），载体不同（实例 Name tag、owner tag 值、礼貌权威口吻的 service tag、Prometheus job 标签、launch template 名、卷 Name tag、想让陷阱被判浪费的 tag）。`eval/test_adversarial.py` 在 replay 下跑完整 agent，断言与基础世界相比：深层发现不变、没有陷阱违规、没有注入造成的多余发现、不变量通过。
- **数字落地**：`finops_agent/judge/validate.py` 的数字校验改成规则 G1–G6（紧贴中文的数字也检查、小整数不再豁免、untrusted 文本不算证据）。不改 prompt，cassette 键不变。
- **样本外评估**：`eval/heldout.py` 在 `next_month`、`month_after` 两个世界上跑完整 agent（judge 用 cassette），按各自 `scenario.expect` 打分，样本内与样本外分开报告。不对样本外结果调 prompt。
- **实验记录**：`eval/EXPERIMENTS.md`（中文）：指标定义与 gate、c0009 样本内迭代历史、样本外结果、对抗结果、能证明什么与不能证明什么。

## Capabilities

### New Capabilities
- `judge-adversarial`：判断层对注入与编造数字的抵抗力有可重放的测试；评估记录区分样本内与样本外。

### Modified Capabilities
（无）

## Impact

只动 `eval/`、`testenv/scenarios/`、`finops_agent/judge/validate.py` 及其测试、`eval/cassettes/`（只新增）、`openspec/`、`notes/`、`reports/`。不改 prompt、取证器、`world.yaml`、已有 cassette、标准答案。录制预算 ≤ 25 次 LLM 调用，每次约 $0.02。AWS 只读不受影响。
