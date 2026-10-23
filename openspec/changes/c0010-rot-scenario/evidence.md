# c0010-rot-scenario 验收证据

## 1. `bash scripts/rot_demo.sh`（退出码 0，结束后 16566/16990 无监听）

```
== rot-1 (run 1, base world, period 2026-09) ==
   new=7  persisting=0  resolved=0  regressed=0
   new        misattributed_tags|i-0a1b2c3d4e5f60501
   new        unattached_volume|vol-0orph00000000c001
   new        idle_public_ip|eipalloc-0aa0000000000001
   new        stopped_instance_storage|i-0a1b2c3d4e5f60801,vol-0leg000000000b001
   new        orphan_snapshots|ami-ingest-v1,ami-ingest-v2,ami-ingest-v3,ami-ingest-v4,ami-ingest-v5,vol-0gone00000000d001
   new        gp2_to_gp3|vol-0db0000000000a001
   new        savings_plan_underutilized|sp-ec2-m5-01
== rot-2 (run 2, next_month, period 2026-10) ==
   new=1  persisting=4  resolved=3  regressed=0
   resolved   gp2_to_gp3|vol-0db0000000000a001
   resolved   unattached_volume|vol-0orph00000000c001
   resolved   idle_public_ip|eipalloc-0aa0000000000001
   new        unattached_volume|vol-0new000000000e001
== rot-3 (run 3, month_after, period 2026-11) ==
   new=1  persisting=4  resolved=1  regressed=1
   resolved   unattached_volume|vol-0new000000000e001
   regressed  gp2_to_gp3|vol-0db0000000000a001  (resolved in rot-2)
   new        idle_public_ip|eipalloc-0aa0000000000003
```

## 2. 基础世界不变

对 `World.raw` 与全部成本行取 sha256，改动后 worktree 与 main 一致：

```
worktree  0c5f19f2b30798a7b87a8b17eb84399a856e5261b19860ef552bd1aea33d361f
main      0c5f19f2b30798a7b87a8b17eb84399a856e5261b19860ef552bd1aea33d361f
```

## 3. `make test` / `make check`

```
Ran 3 tests in 0.067s
OK
Ran 7 tests in 1.027s
OK
Ran 41 tests in 5.607s
OK
make test exit=0
check_rules: OK
```

其中 `testenv.test_testenv.ScenarioConsistency` 真实跑 agent 三次（共用 state），diff 与各场景文件的 `scenario.expect` 逐项相等；`WorldSelection` 覆盖 `--world` 加载、覆盖层链式、非法覆盖层、服务按所选世界应答。

## 4. `openspec validate c0010-rot-scenario`

```
Change 'c0010-rot-scenario' is valid
```
