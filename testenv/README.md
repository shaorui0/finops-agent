# testenv

一个合成的 AWS 账号。agent 可以对着它开发和评估，不碰任何真实账号。

| 组件 | 是什么 | 默认端口 |
|---|---|---|
| `world.yaml` | 账号本身：资源、用量、价格，以及标准答案（发现 + 陷阱 + 可见性缺口） | — |
| `world.py` | 从 `world.yaml` 推导逐日成本行和指标形状 | — |
| `aws_server.py` | **test-aws-server**：EC2、Auto Scaling、STS、Cost Explorer、Resource Groups Tagging、Savings Plans。真实的线上协议，只读 | `:4566` |
| `metrics_server.py` | **test-metrics-server**：Prometheus HTTP API，支持 PromQL 子集（选择器、`rate`/`increase`/`*_over_time`/`quantile_over_time`、`sum/avg/max/min/count by`） | `:9090` |

```bash
python3 -m testenv.aws_server --log /tmp/aws_calls.jsonl &
python3 -m testenv.metrics_server &

aws --endpoint-url http://127.0.0.1:4566 --region us-east-1 ec2 describe-volumes
curl -G localhost:9090/api/v1/query --data-urlencode 'query=sum by (status) (increase(ingest_jobs_total[1d]))'
```

boto3 同理，传 `endpoint_url` 即可。任何凭据都接受。写操作返回 `UnauthorizedOperation`。

## 数据为什么故意做难

账号每月约 $8.7K。只找闲置资源的检测器只能找到其中不到 $100。其余的要把几个数据源关联起来才能看到：

| 发现 | 推理跳数 |
|---|---|
| CPU 60% 的 ingest fleet 没干任何有用的事 | 成本 → CPU（看着正常）→ `ingest_jobs_total{status="succeeded"}` 从 09-04 起持平 → 下游 `QueueDoesNotExist` |
| NAT 账单 ×5 | `NatGateway-Bytes` 跳涨 → 重试导致反复从 S3 下载 → 没有 S3 gateway endpoint |
| 跨 AZ 流量 | 成本行没有资源 ID → 实例所在 AZ → `db_client_bytes_total` |
| Savings Plan 40% 未用 | 8 月利用率下滑 → api 迁到 Graviton → m5 的计划跟不过去 |
| 给 dev 排开关机"省" $580 | 但那些小时由一个用不满的 Savings Plan 支付，实际节省约等于 0 |
| 归因错误的 ETL 主机 | tag 写 web → 启动模板、`job="etl-runner"`、夜间 CPU 形状都说是另一回事 |

陷阱：潮汐 web fleet（平均 27%，p95 76%）、DR 温备、被在用 AMI 引用的快照，以及 Name tag 里的一条 prompt 注入。

标准答案在 `world.yaml` 的 `ground_truth` 下；`test_testenv.py` 校验其中的节省区间与成本模型一致。
