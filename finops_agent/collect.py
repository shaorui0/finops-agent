"""Collect: read-only pulls from AWS and Prometheus into a frozen snapshot.

Every call is appended to the trace (service, operation, parameters, duration),
so a run can be audited and replayed. Analysis only ever reads the snapshot.
"""
from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from datetime import date, timedelta
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import urlopen

import boto3


@dataclass
class Config:
    aws_endpoint: str | None          # None = real AWS (credentials from the environment)
    prom_url: str
    region: str = "us-east-1"
    start: date = date(2026, 9, 1)
    end: date = date(2026, 10, 1)

    @property
    def days(self) -> int:
        return (self.end - self.start).days


@dataclass
class Trace:
    calls: list = field(default_factory=list)

    def record(self, source, op, params, started, ok=True, error=None):
        self.calls.append({"source": source, "op": op, "params": params, "ms": round((time.time() - started) * 1000, 1),
                           "ok": ok, "error": error})


class Collector:
    def __init__(self, cfg: Config, trace: Trace):
        self.cfg, self.trace = cfg, trace
        kw = {"region_name": cfg.region}
        if cfg.aws_endpoint:
            kw.update(endpoint_url=cfg.aws_endpoint, aws_access_key_id="test", aws_secret_access_key="test")
        self._kw = kw
        self._clients = {}

    def _client(self, name):
        if name not in self._clients:
            self._clients[name] = boto3.client(name, **self._kw)
        return self._clients[name]

    def aws(self, service, op, **params):
        started = time.time()
        try:
            out = getattr(self._client(service), op)(**params)
            out.pop("ResponseMetadata", None)
            self.trace.record(f"aws:{service}", op, params, started)
            return out
        except Exception as e:  # recorded, then surfaced to the caller
            self.trace.record(f"aws:{service}", op, params, started, ok=False, error=str(e))
            raise

    def prom(self, path, **params):
        started = time.time()
        url = f"{self.cfg.prom_url}{path}?{urlencode(params, doseq=True)}"
        try:
            with urlopen(url, timeout=60) as r:
                out = json.load(r)
            self.trace.record("prometheus", path, params, started)
            return out["data"]
        except Exception as e:
            self.trace.record("prometheus", path, params, started, ok=False, error=str(e))
            raise

    def prom_query(self, query, at=None):
        at = at or f"{self.cfg.end.isoformat()}T00:00:00Z"
        return self.prom("/api/v1/query", query=query, time=at)["result"]

    # ---- snapshot -----------------------------------------------------------
    def snapshot(self) -> dict:
        c, tp = self.cfg, {"Start": self.cfg.start.isoformat(), "End": self.cfg.end.isoformat()}
        res_start = max(c.start, c.end - timedelta(days=14))
        res_tp = {"Start": res_start.isoformat(), "End": c.end.isoformat()}
        hist_tp = {"Start": (c.start - timedelta(days=92)).isoformat(), "End": c.end.isoformat()}
        snap = {"period": tp, "resource_period": res_tp}
        snap["identity"] = self.aws("sts", "get_caller_identity")
        ec2 = lambda op, **p: self.aws("ec2", op, **p)
        snap["instances"] = [i for r in ec2("describe_instances")["Reservations"] for i in r["Instances"]]
        snap["volumes"] = ec2("describe_volumes")["Volumes"]
        snap["snapshots"] = ec2("describe_snapshots", OwnerIds=["self"])["Snapshots"]
        snap["images"] = ec2("describe_images", Owners=["self"])["Images"]
        snap["addresses"] = ec2("describe_addresses")["Addresses"]
        snap["nat_gateways"] = ec2("describe_nat_gateways")["NatGateways"]
        snap["vpc_endpoints"] = ec2("describe_vpc_endpoints")["VpcEndpoints"]
        snap["launch_templates"] = self._launch_template_versions()
        snap["asgs"] = self.aws("autoscaling", "describe_auto_scaling_groups")["AutoScalingGroups"]
        snap["savings_plans"] = self.aws("savingsplans", "describe_savings_plans")["savingsPlans"]

        ce = lambda op, **p: self.aws("ce", op, **p)
        cost = lambda group, **extra: ce("get_cost_and_usage", TimePeriod=tp, Granularity="MONTHLY",
                                         Metrics=["UnblendedCost", "AmortizedCost", "UsageQuantity"], GroupBy=group, **extra)
        snap["cost_by_service"] = cost([{"Type": "DIMENSION", "Key": "SERVICE"}])["ResultsByTime"]
        snap["cost_by_usage_type"] = cost([{"Type": "DIMENSION", "Key": "SERVICE"}, {"Type": "DIMENSION", "Key": "USAGE_TYPE"}])["ResultsByTime"]
        snap["cost_by_owner"] = cost([{"Type": "TAG", "Key": "owner"}])["ResultsByTime"]
        snap["cost_daily_by_usage_type"] = ce("get_cost_and_usage", TimePeriod=tp, Granularity="DAILY", Metrics=["UnblendedCost"],
                                              GroupBy=[{"Type": "DIMENSION", "Key": "USAGE_TYPE"}])["ResultsByTime"]
        # the window's own jump test cannot see an anomaly that began before the window: keep the days before it as a baseline
        snap["cost_history_daily_by_usage_type"] = ce("get_cost_and_usage", TimePeriod={"Start": (c.start - timedelta(days=92)).isoformat(), "End": c.start.isoformat()},
                                                      Granularity="DAILY", Metrics=["UnblendedCost"],
                                                      GroupBy=[{"Type": "DIMENSION", "Key": "USAGE_TYPE"}])["ResultsByTime"]
        snap["cost_by_resource_14d"] = ce("get_cost_and_usage_with_resources", TimePeriod=res_tp, Granularity="MONTHLY",
                                          Metrics=["UnblendedCost", "AmortizedCost"],
                                          Filter={"Dimensions": {"Key": "SERVICE", "Values": ["Amazon Elastic Compute Cloud - Compute", "EC2 - Other", "Amazon Virtual Private Cloud"]}},
                                          GroupBy=[{"Type": "DIMENSION", "Key": "RESOURCE_ID"}])["ResultsByTime"]
        snap["sp_utilization"] = ce("get_savings_plans_utilization", TimePeriod=hist_tp, Granularity="MONTHLY")["SavingsPlansUtilizationsByTime"]

        snap["metric_names"] = self.prom("/api/v1/label/__name__/values")
        snap["metric_metadata"] = self.prom("/api/v1/metadata")
        return snap

    def _launch_template_versions(self):
        lts = self.aws("ec2", "describe_launch_templates")["LaunchTemplates"]
        out = []
        for lt in lts:
            out += self.aws("ec2", "describe_launch_template_versions", LaunchTemplateId=lt["LaunchTemplateId"])["LaunchTemplateVersions"]
        return out


def save(obj, path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, default=str, ensure_ascii=False))
