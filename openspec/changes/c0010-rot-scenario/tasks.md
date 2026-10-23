## 1. 世界选择
- [x] 1.1 `world.use()` / `load(path)`；两个服务 `--world`
- [x] 1.2 覆盖层 set / remove / patch / add；`volumes[].created`、`addresses[].since` 控制账单起点

## 2. 场景
- [x] 2.1 `next_month.yaml`：3 个 resolved + 1 个 new
- [x] 2.2 `month_after.yaml`：1 个 regressed + 1 个 resolved + 1 个 new
- [x] 2.3 `scripts/rot_demo.sh`

## 3. 测试
- [x] 3.1 `--world` 加载、覆盖层语义、非法覆盖层
- [x] 3.2 场景自洽：三次真实 agent 运行，diff 与 `scenario.expect` 相等

## 4. 验收
- [x] 4.1 `bash scripts/rot_demo.sh` 打印 resolved / regressed / new 均 >= 1 的 diff
- [x] 4.2 `make test`、`make check` 全绿；基础世界 sha256 与改动前一致
- [x] 4.3 `openspec validate c0010-rot-scenario`
