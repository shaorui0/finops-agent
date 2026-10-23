# testenv

A synthetic AWS account the agent can be developed and evaluated against, without touching a real account.

| Component | What it is | Default |
|---|---|---|
| `world.yaml` | The account: resources, usage, prices, and the ground truth (findings + traps + visibility gaps) | — |
| `world.py` | Derives daily cost lines and metric shapes from `world.yaml` | — |
| `aws_server.py` | **test-aws-server**: EC2, Auto Scaling, STS, Cost Explorer, Resource Groups Tagging, Savings Plans — real wire protocols, read-only | `:4566` |
| `metrics_server.py` | **test-metrics-server**: Prometheus HTTP API with a PromQL subset (selectors, `rate`/`increase`/`*_over_time`/`quantile_over_time`, `sum/avg/max/min/count by`) | `:9090` |

```bash
python3 -m testenv.aws_server --log /tmp/aws_calls.jsonl &
python3 -m testenv.metrics_server &

aws --endpoint-url http://127.0.0.1:4566 --region us-east-1 ec2 describe-volumes
curl -G localhost:9090/api/v1/query --data-urlencode 'query=sum by (status) (increase(ingest_jobs_total[1d]))'
```

boto3 works the same way: pass `endpoint_url`. Any credentials are accepted. Write operations return `UnauthorizedOperation`.

## Why the data is hard on purpose

The account totals about $8.7K/month. A detector that only looks for idle resources finds under $100 of it. The rest only shows up by joining sources:

| Finding | Hops |
|---|---|
| Ingest fleet at 60% CPU doing nothing useful | cost → CPU (looks fine) → `ingest_jobs_total{status="succeeded"}` flat since 09-04 → downstream `QueueDoesNotExist` |
| NAT bill ×5 | `NatGateway-Bytes` jump → retries re-download from S3 → no S3 gateway endpoint |
| Cross-AZ transfer | cost line has no resource ID → instance AZs → `db_client_bytes_total` |
| Savings Plan 40% unused | utilization drop in August → api moved to Graviton → m5 plan cannot follow |
| Scheduling dev "saves" $580 | …except those hours are paid by the under-used Savings Plan, so the real saving is ~0 |
| Mis-tagged ETL host | tags say web → launch template, `job="etl-runner"`, nightly CPU shape say otherwise |

Traps: a tidal web fleet (avg 27%, p95 76%), a warm DR standby, snapshots behind in-use AMIs, and a prompt injection in a Name tag.

Ground truth lives in `world.yaml` under `ground_truth`; `test_testenv.py` checks that its savings ranges agree with the cost model.
