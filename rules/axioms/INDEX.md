# 项目公理索引

公理是本项目的判断依据（为什么），skill 是执行步骤（怎么做）。每条公理都必须能在仓库里找到落地点。来源见 `docs/DISTILLATION.md`。

| ID | 公理 | 一句话 |
|---|---|---|
| FA01 | [可验证先于正确](fa01_verifiability_first.md) | 设计时让错误容易被发现，而不是假设它不会发生。 |
| FA02 | [隔离、处理、验证](fa02_isolate_process_verify.md) | 高风险操作强制三段：只读收集事实，在沙盒里可重复地处理，验证后经人工闸门才发布。 |
| FA03 | [数据优于观点](fa03_data_over_opinion.md) | 能测量就用测量结果决策，不用叙事和直觉。 |
| FA04 | [误差会级联放大](fa04_precision_cascades.md) | 耦合系统里，误差在接口间相乘而不是相加。 |
| FA05 | [先找大杠杆](fa05_big_levers_first.md) | 用粗略量化找到支配结果的少数几项，先把时间花在那里。 |
| FA06 | [成本治理是一个控制回路](fa06_cost_is_a_control_loop.md) | 可见性是传感器，预算/SLO/目标 spec 是设定值，修复是执行器，人是最慢的兜底控制器。 |
| FA07 | [agent 是不可靠组件，SRE 是外壳](fa07_agent_is_unreliable_component.md) | 把 agent 当成一个不可靠的组件来运维：给它定目标、量它的错误率、用护栏限制它的爆炸半径，而不是要求它表现得确定。 |
| FA08 | [责任不能委派](fa08_responsibility_not_delegated.md) | 执行可以交给 agent，结果的责任仍在人。 |
| FA09 | [文档即长期记忆](fa09_docs_are_memory.md) | 上下文窗口会丢，文档不会。 |
| FA10 | [用机制暴露盲区](fa10_engineered_exposure.md) | 不知道自己不知道的东西，靠更努力地想解决不了，只能靠持续运行的暴露机制。 |
| FA11 | [上下文隔离](fa11_context_isolation.md) | 多 agent 的价值在于每个 agent 有干净的信息域，而不是模仿组织分工。 |
| FA12 | [以终为始](fa12_start_from_the_end.md) | 先定义要回答什么问题、用什么指标衡量，再去找数据。 |
| FA13 | [潮汐不是浪费](fa13_tide_is_not_waste.md) | 短期冲高是弹性在工作，长期不降才是浪费。 |

## 常一起用

- **可信的发现**：FA01 + FA03 + FA04
- **安全地动手**：FA02 + FA06 + FA08
- **把 agent 当组件运维**：FA07 + FA10 + FA11
- **判定浪费**：FA05 + FA12 + FA13
