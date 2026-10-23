## 为什么是三次运行，不是两次

`diff_state` 里 `regressed` 的定义是：这个 finding key（`type|sorted(resources)`）在 state 的 `resolved` 里。key 只有在"上一次 open、这一次消失"时才进入 `resolved`。所以：

- 第 1 次运行：state 为空，全部 `new`。
- 第 2 次运行：最多出现 `resolved`、`persisting`、`new`。`resolved` 此刻才第一次有内容，**两次运行不可能出现 regressed**。
- 第 3 次运行：此前 resolved 的 key 重新出现，才是 `regressed`。

备选方案：(a) 往 state 文件里手写一条 resolved——是作弊，演示的不是 agent 自己的行为；(b) 第 2 次运行回到基础世界——时间倒流，且全部 resolved 的东西都回来，没有故事。选三个月：09 基础 → 10 `next_month` → 11 `month_after`。第 2 次的 diff 展示 resolved + new，第 3 次展示 regressed。

## 故事（每条都是真实会发生的腐化）

| 月份 | 事件 | key | 状态 |
|---|---|---|---|
| 10 | team-web 删掉 `tmp-migration` 卷 | `unattached_volume|vol-0orph..` | resolved |
| 10 | EIP 释放 | `idle_public_ip|eipalloc-..0001` | resolved |
| 10 | orders-db 卷迁到 gp3 | `gp2_to_gp3|vol-0db..` | resolved |
| 10 | team-data 留下 `restore-scratch` 卷 | `unattached_volume|vol-0new..` | new |
| 11 | 另一个团队 `terraform apply` 把卷改回 gp2（代码里还写着 gp2） | `gp2_to_gp3|vol-0db..` | **regressed** |
| 11 | scratch 卷被删 | `unattached_volume|vol-0new..` | resolved |
| 11 | canary 临时申请的 EIP 没释放 | `idle_public_ip|eipalloc-..0003` | new |

回归选 gp2 而不是 EIP，是因为 key 含资源 ID：AWS 不会重用已释放的 allocation id，"同一个 EIP 回来"不成立。同一个卷被 IaC 漂移改回去是真实的。重新泄漏的 EIP 用新 id，所以是 `new`，不是 `regressed`，这也是演示里要保留的区别。

## 覆盖层，不是完整世界

两个场景都是覆盖层：`scenario.base` 指向被修改的世界，只写差异。理由：基础世界的价格、用量、事故时间线是唯一来源，复制一份会漂移；差异本身就是场景的故事，读起来一目了然。`month_after` 叠在 `next_month` 上（覆盖层可链式），只写 11 月比 10 月多变的部分。完整世界文件仍然支持（有顶层 `account` 就按完整世界读）。

应用顺序 set → remove → patch → add；引用不存在的 id、添加重复 id 直接报错，防止场景悄悄失效。

## 周期一致性

- `account.period` 由覆盖层 set；metrics 服务只有这个周期内有数据，agent 的 `--start/--end` 必须与之对齐（脚本里写死）。
- `history.cost_start` 不动（2026-06-01），成本历史连续；SP 利用率从历史行算，不需要改。
- 新增资源只从创建日起计费：`volumes[].created`、`addresses[].since`。基础世界的卷都早于 `cost_start`，所以基础成本行不变。
- 事故（09-04 起 ingest 全部失败）在 10、11 月仍在继续：NAT、ingest fleet 等不属于 finding key 里的"可修复项"的东西保持 persisting。

## 真值

场景的真值放在场景文件的 `scenario.expect`（resolved / new / regressed / persisting 四组 key）。不碰 `world.yaml` 的 `ground_truth`，基础评估（`make eval`）不受影响。测试 `ScenarioConsistency` 真实跑 agent 三次并逐项比对，场景改坏会立刻红。

## 全局状态

`world.use(path)` 设置当前世界并清掉 `load` 和 metrics `build` 两个 lru_cache；服务启动时调用一次。测试里需要切换世界时同样用它，`tearDown` 里 `use(None)` 还原。
