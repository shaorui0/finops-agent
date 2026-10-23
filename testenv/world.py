"""Derive cost lines and metric series from world.yaml.

Both test servers import this module; the agent never does.

Cost model (per day, per line):
  - running instance: unblended = on-demand price x 24h.
  - instance in a family covered by a Savings Plan: adds a negation line
    (-on-demand) and its amortized cost is the SP rate (on-demand x (1-discount)).
  - Savings Plan recurring fee: unblended = commitment x 24h; amortized = the
    unused part only (the used part is amortized into the covered instances).
  - EBS, snapshots, NAT, cross-AZ, public IPv4, flat services: unblended = amortized.
"""
from __future__ import annotations

import functools
import math
import random
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import yaml

WORLD_FILE = Path(__file__).with_name("world.yaml")
STEP = 300  # metric resolution, seconds

SERVICE_EC2 = "Amazon Elastic Compute Cloud - Compute"
SERVICE_EC2_OTHER = "EC2 - Other"
SERVICE_VPC = "Amazon Virtual Private Cloud"
SERVICE_SP = "Savings Plans for AWS Compute usage"


def _d(s: str) -> date:
    return date.fromisoformat(s[:10])


def _ts(s: str) -> float:
    return datetime.fromisoformat(s.replace("Z", "+00:00")).timestamp()


def family(instance_type: str) -> str:
    return instance_type.split(".")[0]


@dataclass
class CostLine:
    day: date
    service: str
    usage_type: str
    resource_id: str | None
    tags: dict
    unblended: float
    amortized: float
    quantity: float
    region: str = "us-east-1"


@dataclass
class World:
    raw: dict
    lines: list[CostLine] = field(default_factory=list)

    # ---- accessors -------------------------------------------------------
    @property
    def account_id(self) -> str:
        return self.raw["account"]["id"]

    @property
    def region(self) -> str:
        return self.raw["account"]["region"]

    @property
    def period(self) -> tuple[date, date]:
        p = self.raw["account"]["period"]
        return _d(p["start"]), _d(p["end"])

    @property
    def instances(self) -> list[dict]:
        return self.raw["instances"]

    def instance(self, iid: str) -> dict:
        return next(i for i in self.instances if i["id"] == iid)

    @property
    def prices(self) -> dict:
        return self.raw["prices"]

    @property
    def incident_ts(self) -> float:
        return _ts(self.raw["usage"]["incident_start"])

    def snapshots(self) -> list[dict]:
        out = []
        n = 0
        for img in self.raw["images"]:
            for k in range(img["snapshots"]):
                n += 1
                out.append({
                    "id": f"snap-0img{n:013d}",
                    "volume_id": f"vol-0src{n:013d}",
                    "size": self.raw["image_snapshot_gb"],
                    "start": img["created"] + "T00:00:00Z",
                    "description": f"Created by CreateImage for {img['id']}",
                    "image": img["id"],
                })
        orphan = self.raw["orphan_snapshot_series"]
        start = date(2026, 5, 17)
        for k in range(orphan["count"]):
            out.append({
                "id": f"snap-0orp{k + 1:013d}",
                "volume_id": orphan["source_volume"],
                "size": orphan["gb_each"],
                "start": (start + timedelta(days=k)).isoformat() + "T01:00:00Z",
                "description": "Created by lifecycle policy dlm-daily for tag backup=daily",
                "image": None,
            })
        return out

    def all_volumes(self) -> list[dict]:
        vols = []
        for inst in self.instances:
            for v in inst.get("volumes", []):
                vols.append({**v, "az": inst["az"], "state": "in-use", "instance": inst["id"],
                             "tags": inst["tags"], "created": "2025-10-01T00:00:00Z"})
        for v in self.raw["volumes"]:
            vols.append({**v, "instance": None})
        return vols

    # ---- savings plan ----------------------------------------------------
    def sp_hourly_usage(self, day: date) -> float:
        """SP-rate cost per hour of covered usage on `day` (before capping at commitment)."""
        used = 0.0
        for sp in self.raw["savings_plans"]:
            disc = self.prices["sp_discount"][sp["family"]]
            for itype, hours in self._instance_hours(day):
                if family(itype) == sp["family"]:
                    used += self.prices["ec2_hourly"][itype] * (1 - disc) * hours / 24
        return used

    def sp_utilization(self, day: date) -> dict:
        sp = self.raw["savings_plans"][0]
        total = sp["commitment_hourly"] * 24
        used = min(total, self.sp_hourly_usage(day) * 24)
        return {"total": total, "used": used, "unused": total - used}

    def _instance_hours(self, day: date):
        """Yield (instance_type, hours) for every instance running on `day`, incl. history."""
        hist = self.raw["history"]["api_pre_migration"]
        migrated = _d(hist["until"])
        for inst in self.instances:
            if inst["tags"].get("service") == "api" and day < migrated:
                continue
            if inst.get("state") == "stopped" and day >= _d(inst["stopped_at"]):
                continue
            yield inst["type"], 24.0
        if day < migrated:
            for _ in range(hist["count"]):
                yield hist["type"], 24.0

    # ---- cost lines ------------------------------------------------------
    def build_lines(self) -> None:
        start = _d(self.raw["history"]["cost_start"])
        _, end = self.period
        day = start
        while day < end:
            self.lines.extend(self._lines_for(day))
            day += timedelta(days=1)

    def _lines_for(self, day: date) -> list[CostLine]:
        P = self.prices
        out: list[CostLine] = []
        sp_families = {sp["family"]: P["sp_discount"][sp["family"]] for sp in self.raw["savings_plans"]}
        hist = self.raw["history"]["api_pre_migration"]
        migrated = _d(hist["until"])

        def compute(rid, itype, tags):
            od = P["ec2_hourly"][itype] * 24
            disc = sp_families.get(family(itype))
            amort = od * (1 - disc) if disc is not None else od
            out.append(CostLine(day, SERVICE_EC2, f"BoxUsage:{itype}", rid, tags, od, amort, 24))
            if disc is not None:
                out.append(CostLine(day, SERVICE_EC2, f"SavingsPlanNegation:BoxUsage:{itype}", rid, tags, -od, 0.0, 0))

        for inst in self.instances:
            if inst["tags"].get("service") == "api" and day < migrated:
                continue
            if inst.get("state") == "stopped" and day >= _d(inst["stopped_at"]):
                continue
            compute(inst["id"], inst["type"], inst["tags"])
        if day < migrated:
            for k in range(hist["count"]):
                compute(f"i-0retired000000{k:03d}", hist["type"], {"service": "api", "owner": "team-api", "env": "prod"})

        util = self.sp_utilization(day)
        out.append(CostLine(day, SERVICE_SP, "SavingsPlanRecurringFee", self.raw["savings_plans"][0]["id"], {},
                            util["total"], util["unused"], 24))

        for v in self.all_volumes():
            gb = P["ebs_gb_month"][v["type"]] * v["size"] / 30
            ut = "EBS:VolumeUsage.piops" if v["type"] == "io1" else f"EBS:VolumeUsage.{v['type']}"
            tags = v.get("tags", {})
            out.append(CostLine(day, SERVICE_EC2_OTHER, ut, v["id"], tags, gb, gb, v["size"] / 30))
            if v["type"] == "io1":
                iops = P["io1_iops_month"] * v["iops"] / 30
                out.append(CostLine(day, SERVICE_EC2_OTHER, "EBS:VolumeP-IOPS.piops", v["id"], tags, iops, iops, v["iops"] / 30))

        for s in self.snapshots():
            if _d(s["start"]) <= day:
                c = P["snapshot_gb_month"] * s["size"] / 30
                out.append(CostLine(day, SERVICE_EC2_OTHER, "EBS:SnapshotUsage", s["id"], {}, c, c, s["size"] / 30))

        nat = self.raw["nat_gateways"][0]["id"]
        out.append(CostLine(day, SERVICE_EC2_OTHER, "NatGateway-Hours", nat, {}, P["nat_hourly"] * 24, P["nat_hourly"] * 24, 24))
        gb = self.nat_gb_on(day)
        out.append(CostLine(day, SERVICE_EC2_OTHER, "NatGateway-Bytes", nat, {}, gb * P["nat_gb"], gb * P["nat_gb"], gb))

        xaz = self.raw["usage"]["api_to_db_gb_month"] / 30
        out.append(CostLine(day, SERVICE_EC2_OTHER, "DataTransfer-Regional-Bytes", None, {}, xaz * P["cross_az_gb"], xaz * P["cross_az_gb"], xaz))

        for a in self.raw["addresses"]:
            ut = "PublicIPv4:InUseAddress" if a.get("instance") else "PublicIPv4:IdleAddress"
            c = P["public_ipv4_hourly"] * 24
            out.append(CostLine(day, SERVICE_VPC, ut, a["allocation_id"], {}, c, c, 24))

        for svc, monthly in self.raw["flat_services"].items():
            out.append(CostLine(day, svc, f"{svc}:Usage", None, {}, monthly / 30, monthly / 30, 1))
        return out

    # ---- shared usage model ---------------------------------------------
    def ingest_attempts_per_hour(self, ts: float) -> float:
        u = self.raw["usage"]
        base = u["ingest_attempts_per_hour_ok"]
        return base * u["ingest_retry_multiplier"] if ts >= self.incident_ts else base

    def nat_gb_on(self, day: date) -> float:
        u = self.raw["usage"]
        hours_before = 0.0
        day_start = datetime(day.year, day.month, day.day, tzinfo=timezone.utc).timestamp()
        for h in range(24):
            if day_start + h * 3600 < self.incident_ts:
                hours_before += 1
        attempts = hours_before * u["ingest_attempts_per_hour_ok"] + (24 - hours_before) * u["ingest_attempts_per_hour_ok"] * u["ingest_retry_multiplier"]
        return u["nat_gb_baseline_month"] / 30 + attempts * u["ingest_s3_gb_per_attempt"]


@functools.lru_cache(maxsize=1)
def load(path: str | None = None) -> World:
    raw = yaml.safe_load(Path(path or WORLD_FILE).read_text())
    w = World(raw)
    w.build_lines()
    return w


# ---- metric profiles -------------------------------------------------------
def _hour(ts: float) -> float:
    return (ts % 86400) / 3600


def _weekday(ts: float) -> int:
    return datetime.fromtimestamp(ts, timezone.utc).weekday()


def _bell(h: float, start: float, end: float) -> float:
    if h < start or h > end:
        return 0.0
    return math.sin(math.pi * (h - start) / (end - start))


def _office(ts: float) -> bool:
    return _weekday(ts) < 5 and _hour(ts) < 10


def cpu(world: World, inst: dict, ts: float, rng: random.Random) -> float | None:
    p = inst["profile"]
    n = rng.uniform(-2, 2)
    if p == "web_tidal":
        weekend = 0.6 if _weekday(ts) >= 5 else 1.0
        return max(1.0, 9 + 69 * weekend * _bell(_hour(ts), 0, 11) + n)
    if p == "api_steady":
        return 35 + 3 * n
    if p == "db_steady":
        return 40 + 2 * n
    if p == "ingest_retry_storm":
        return (62 if ts >= world.incident_ts else 30) + n
    if p == "etl_nightly":
        return 85 + n if 2 <= _hour(ts) < 4 else max(0.5, 2 + n / 2)
    if p == "dev_office_hours":
        return 30 + 2 * n if _office(ts) else max(0.3, 1 + n / 4)
    if p == "dr_standby":
        return max(0.3, 1 + n / 4)
    return None


JOB_BY_PROFILE = {
    "web_tidal": "web", "api_steady": "api", "db_steady": "orders-db",
    "ingest_retry_storm": "ingest-worker", "etl_nightly": "etl-runner",
    "dev_office_hours": "web-dev", "dr_standby": "orders-db-replica",
}
