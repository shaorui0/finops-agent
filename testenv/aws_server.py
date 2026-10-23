#!/usr/bin/env python3
"""test-aws-server: a read-only fake of the AWS APIs this project uses.

Speaks the real wire protocols (EC2 query/XML, query/XML, JSON 1.1, REST-JSON),
serialized from botocore's own service models, so boto3 and the aws CLI work
unchanged with `--endpoint-url http://127.0.0.1:4566`.

Every response is derived from testenv/world.yaml. Write operations return
UnauthorizedOperation, like a read-only IAM role would.

Usage: python3 -m testenv.aws_server [--port 4566] [--log calls.jsonl]
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs
from xml.sax.saxutils import escape

import botocore.session

from testenv.world import load, family, use as use_world

_session = botocore.session.get_session()
_models = {}

QUERY_VERSIONS = {"2016-11-15": "ec2", "2011-01-01": "autoscaling", "2011-06-15": "sts"}
JSON_TARGETS = {"AWSInsightsIndexService": "ce", "ResourceGroupsTaggingAPI_20170126": "resourcegroupstaggingapi"}
READ_OP = re.compile(r"^(Describe|Get|List|Lookup|Search|BatchGet)")


def model(service):
    if service not in _models:
        _models[service] = _session.get_service_model(service)
    return _models[service]


# ---- XML serialization driven by botocore shapes ---------------------------
def _scalar(shape, v):
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, datetime):
        return v.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")
    return escape(str(v))


def _xml(shape, value, name, list_item):
    t = shape.type_name
    if t == "structure":
        inner = "".join(
            _xml(ms, value[mn], ms.serialization.get("name", mn), list_item)
            for mn, ms in shape.members.items() if mn in value and value[mn] is not None
        )
        return f"<{name}>{inner}</{name}>"
    if t == "list":
        item = shape.member.serialization.get("name", list_item)
        return f"<{name}>" + "".join(_xml(shape.member, v, item, list_item) for v in value) + f"</{name}>"
    return f"<{name}>{_scalar(shape, value)}</{name}>"


def to_xml(service, op, body):
    m = model(service)
    out = m.operation_model(op).output_shape
    ns = m.metadata.get("xmlNamespace", "")
    if m.protocol == "ec2":
        inner = "".join(_xml(ms, body[mn], ms.serialization.get("name", mn), "item")
                        for mn, ms in out.members.items() if mn in body)
        return f'<{op}Response xmlns="{ns}"><requestId>fake-{int(time.time())}</requestId>{inner}</{op}Response>'
    wrapper = out.serialization.get("resultWrapper", f"{op}Result")
    inner = "".join(_xml(ms, body[mn], ms.serialization.get("name", mn), "member")
                    for mn, ms in out.members.items() if mn in body)
    return (f'<{op}Response xmlns="{ns}"><{wrapper}>{inner}</{wrapper}>'
            f"<ResponseMetadata><RequestId>fake</RequestId></ResponseMetadata></{op}Response>")


def _query_list(params, prefix):
    out, i = [], 1
    while f"{prefix}.{i}" in params:
        out.append(params[f"{prefix}.{i}"])
        i += 1
    return out


def _filters(params):
    out, i = {}, 1
    while f"Filter.{i}.Name" in params:
        out[params[f"Filter.{i}.Name"]] = _query_list(params, f"Filter.{i}.Value")
        i += 1
    return out


def _tags(d):
    return [{"Key": k, "Value": v} for k, v in d.items()]


# ---- EC2 / autoscaling / sts -----------------------------------------------
class Ec2:
    def __init__(self, w):
        self.w = w
        self.lt_ids = {"lt-web": "lt-0web0000000000001", "lt-ingest": "lt-0ing0000000000001"}

    def _instance(self, inst):
        tags = dict(inst["tags"])
        asg = inst.get("asg")
        lt = inst.get("launch_template") or (self.w.raw["asgs"][asg]["launch_template"] if asg else None)
        if asg:
            tags["aws:autoscaling:groupName"] = asg
        if lt:
            tags["aws:ec2launchtemplate:id"] = self.lt_ids[lt]
            tags["aws:ec2launchtemplate:version"] = "3"
        stopped = inst.get("state") == "stopped"
        image = None
        if asg:
            image = self.w.raw["asgs"][asg]["image"]
        elif lt == "lt-ingest":
            image = "ami-ingest-v7"
        d = {
            "InstanceId": inst["id"],
            "InstanceType": inst["type"],
            "ImageId": image or "ami-base-al2023",
            "State": {"Code": 80 if stopped else 16, "Name": "stopped" if stopped else "running"},
            "Placement": {"AvailabilityZone": inst["az"], "Tenancy": "default"},
            "LaunchTime": datetime(2026, 8, 20 if family(inst["type"]) == "m6g" else 1, tzinfo=timezone.utc),
            "Tags": _tags(tags),
            "Architecture": "arm64" if family(inst["type"]) == "m6g" else "x86_64",
            "PrivateIpAddress": f"10.0.{1 if inst['az'].endswith('a') else 2}.{int(inst['id'][-3:]) % 250}",
            "SubnetId": "subnet-0priv0000000000a" if inst["az"].endswith("a") else "subnet-0priv0000000000b",
            "VpcId": "vpc-0main000000000001",
            "BlockDeviceMappings": [
                {"DeviceName": "/dev/sdf", "Ebs": {"VolumeId": v["id"], "Status": "attached",
                                                    "AttachTime": datetime(2025, 10, 1, tzinfo=timezone.utc)}}
                for v in inst.get("volumes", [])
            ],
        }
        if stopped:
            d["StateTransitionReason"] = f"User initiated ({inst['stopped_at'].replace('T', ' ').replace('Z', ' GMT')})"
        return d

    def DescribeInstances(self, p):
        ids = set(_query_list(p, "InstanceId"))
        f = _filters(p)
        res = []
        for inst in self.w.instances:
            d = self._instance(inst)
            if ids and inst["id"] not in ids:
                continue
            if "instance-state-name" in f and d["State"]["Name"] not in f["instance-state-name"]:
                continue
            tag_ok = all(any(t["Key"] == k[4:] and t["Value"] in vals for t in d["Tags"])
                         for k, vals in f.items() if k.startswith("tag:"))
            if tag_ok:
                res.append({"ReservationId": f"r-{inst['id'][2:]}", "OwnerId": self.w.account_id, "Instances": [d]})
        return {"Reservations": res}

    def DescribeVolumes(self, p):
        out = []
        for v in self.w.all_volumes():
            d = {"VolumeId": v["id"], "Size": v["size"], "VolumeType": v["type"], "AvailabilityZone": v["az"],
                 "State": v["state"], "CreateTime": datetime.fromisoformat(v["created"].replace("Z", "+00:00")),
                 "Encrypted": True, "Tags": _tags(v.get("tags", {})), "Attachments": []}
            if v.get("iops"):
                d["Iops"] = v["iops"]
            if v["instance"]:
                d["Attachments"] = [{"VolumeId": v["id"], "InstanceId": v["instance"], "Device": "/dev/sdf",
                                     "State": "attached", "DeleteOnTermination": False,
                                     "AttachTime": datetime(2025, 10, 1, tzinfo=timezone.utc)}]
            out.append(d)
        return {"Volumes": out}

    def DescribeSnapshots(self, p):
        return {"Snapshots": [
            {"SnapshotId": s["id"], "VolumeId": s["volume_id"], "VolumeSize": s["size"], "State": "completed",
             "StartTime": datetime.fromisoformat(s["start"].replace("Z", "+00:00")), "Description": s["description"],
             "OwnerId": self.w.account_id, "StorageTier": "standard", "Progress": "100%"}
            for s in self.w.snapshots()]}

    def DescribeImages(self, p):
        snaps = defaultdict(list)
        for s in self.w.snapshots():
            if s["image"]:
                snaps[s["image"]].append(s)
        return {"Images": [
            {"ImageId": img["id"], "Name": img["id"], "State": "available", "OwnerId": self.w.account_id,
             "CreationDate": img["created"] + "T00:00:00.000Z",
             "BlockDeviceMappings": [{"DeviceName": f"/dev/sd{chr(97 + k)}", "Ebs": {"SnapshotId": s["id"], "VolumeSize": s["size"]}}
                                     for k, s in enumerate(snaps[img["id"]])]}
            for img in self.w.raw["images"]]}

    def DescribeAddresses(self, p):
        out = []
        for a in self.w.raw["addresses"]:
            d = {"AllocationId": a["allocation_id"], "PublicIp": a["public_ip"], "Domain": "vpc"}
            if a.get("instance"):
                d["InstanceId"] = a["instance"]
                d["AssociationId"] = "eipassoc-" + a["allocation_id"][-8:]
            out.append(d)
        return {"Addresses": out}

    def DescribeNatGateways(self, p):
        return {"NatGateways": [
            {"NatGatewayId": n["id"], "State": "available", "SubnetId": "subnet-0pub00000000000a", "VpcId": "vpc-0main000000000001",
             "ConnectivityType": "public", "CreateTime": datetime(2025, 9, 1, tzinfo=timezone.utc)}
            for n in self.w.raw["nat_gateways"]]}

    def DescribeVpcEndpoints(self, p):
        return {"VpcEndpoints": self.w.raw["vpc_endpoints"]}

    def DescribeLaunchTemplates(self, p):
        return {"LaunchTemplates": [
            {"LaunchTemplateId": lid, "LaunchTemplateName": name, "LatestVersionNumber": 3, "DefaultVersionNumber": 3,
             "Tags": _tags({"owner": "team-web" if name == "lt-web" else "team-data"})}
            for name, lid in self.lt_ids.items()]}

    def DescribeLaunchTemplateVersions(self, p):
        image = {"lt-web": "ami-web-v12", "lt-ingest": "ami-ingest-v7"}
        itype = {"lt-web": "m5.xlarge", "lt-ingest": "c5.2xlarge"}
        return {"LaunchTemplateVersions": [
            {"LaunchTemplateId": lid, "LaunchTemplateName": name, "VersionNumber": 3, "DefaultVersion": True,
             "LaunchTemplateData": {"ImageId": image[name], "InstanceType": itype[name]}}
            for name, lid in self.lt_ids.items()]}

    def DescribeAutoScalingGroups(self, p):
        out = []
        for name, a in self.w.raw["asgs"].items():
            members = [i for i in self.w.instances if i.get("asg") == name]
            out.append({
                "AutoScalingGroupName": name, "MinSize": len(members), "MaxSize": len(members) * 2,
                "DesiredCapacity": len(members), "DefaultCooldown": 300, "HealthCheckType": "EC2",
                "AvailabilityZones": sorted({i["az"] for i in members}),
                "CreatedTime": datetime(2025, 9, 1, tzinfo=timezone.utc),
                "LaunchTemplate": {"LaunchTemplateId": self.lt_ids[a["launch_template"]], "LaunchTemplateName": a["launch_template"], "Version": "3"},
                "Instances": [{"InstanceId": i["id"], "InstanceType": i["type"], "AvailabilityZone": i["az"],
                               "LifecycleState": "InService", "HealthStatus": "Healthy", "ProtectedFromScaleIn": False}
                              for i in members],
                "Tags": [],
            })
        return {"AutoScalingGroups": out}

    def GetCallerIdentity(self, p):
        return {"UserId": "AROAFAKEREADONLY:finops-agent", "Account": self.w.account_id,
                "Arn": f"arn:aws:sts::{self.w.account_id}:assumed-role/finops-readonly/finops-agent"}


# ---- Cost Explorer ----------------------------------------------------------
def _match(line, expr):
    if not expr:
        return True
    if "And" in expr:
        return all(_match(line, e) for e in expr["And"])
    if "Or" in expr:
        return any(_match(line, e) for e in expr["Or"])
    if "Not" in expr:
        return not _match(line, expr["Not"])
    if "Dimensions" in expr:
        d = expr["Dimensions"]
        return _dim(line, d["Key"]) in d["Values"]
    if "Tags" in expr:
        t = expr["Tags"]
        return line.tags.get(t["Key"], "") in t.get("Values", [""])
    return True


def _dim(line, key):
    return {
        "SERVICE": line.service, "USAGE_TYPE": line.usage_type, "RESOURCE_ID": line.resource_id or "NoResourceId",
        "REGION": line.region, "LINKED_ACCOUNT": "000000000000", "RECORD_TYPE": "Usage",
    }.get(key, "")


def _group_key(line, g):
    if g["Type"] == "TAG":
        return f"{g['Key']}${line.tags.get(g['Key'], '')}"
    return _dim(line, g["Key"])


METRIC_ATTR = {"UnblendedCost": "unblended", "AmortizedCost": "amortized", "NetAmortizedCost": "amortized",
               "BlendedCost": "unblended", "NetUnblendedCost": "unblended", "UsageQuantity": "quantity"}


def _buckets(start, end, granularity):
    out, d = [], start
    while d < end:
        if granularity == "MONTHLY":
            nxt = date(d.year + (d.month == 12), d.month % 12 + 1, 1)
        else:
            nxt = d + timedelta(days=1)
        out.append((d, min(nxt, end)))
        d = nxt
    return out


class Ce:
    def __init__(self, w):
        self.w = w

    def _cost(self, req, with_resources):
        start, end = date.fromisoformat(req["TimePeriod"]["Start"]), date.fromisoformat(req["TimePeriod"]["End"])
        gran = req.get("Granularity", "MONTHLY")
        metrics = req.get("Metrics", ["UnblendedCost"])
        groups = req.get("GroupBy", [])
        for g in groups:
            if g["Key"] == "RESOURCE_ID" and not with_resources:
                raise ApiError(400, "ValidationException", "RESOURCE_ID grouping requires GetCostAndUsageWithResources")
        if with_resources and (end - start).days > 14:
            raise ApiError(400, "DataUnavailableException", "Resource-level data is only available for the last 14 days")
        flt = req.get("Filter")
        results = []
        for b0, b1 in _buckets(start, end, gran):
            lines = [l for l in self.w.lines if b0 <= l.day < b1 and _match(l, flt)]
            def metric_block(ls):
                return {m: {"Amount": f"{sum(getattr(l, METRIC_ATTR[m]) for l in ls):.6f}",
                            "Unit": "N/A" if m == "UsageQuantity" else "USD"} for m in metrics}
            entry = {"TimePeriod": {"Start": b0.isoformat(), "End": b1.isoformat()}, "Estimated": False}
            if groups:
                agg = defaultdict(list)
                for l in lines:
                    agg[tuple(_group_key(l, g) for g in groups)].append(l)
                entry["Groups"] = [{"Keys": list(k), "Metrics": metric_block(v)} for k, v in sorted(agg.items())]
                entry["Total"] = {}
            else:
                entry["Total"] = metric_block(lines)
                entry["Groups"] = []
            results.append(entry)
        return {"ResultsByTime": results, "GroupDefinitions": groups, "DimensionValueAttributes": []}

    def GetCostAndUsage(self, req):
        return self._cost(req, False)

    def GetCostAndUsageWithResources(self, req):
        return self._cost(req, True)

    def GetSavingsPlansUtilization(self, req):
        start, end = date.fromisoformat(req["TimePeriod"]["Start"]), date.fromisoformat(req["TimePeriod"]["End"])
        out, T = [], {"total": 0, "used": 0}
        for b0, b1 in _buckets(start, end, req.get("Granularity", "MONTHLY")):
            tot = used = 0.0
            d = b0
            while d < b1:
                u = self.w.sp_utilization(d)
                tot, used = tot + u["total"], used + u["used"]
                d += timedelta(days=1)
            T["total"] += tot
            T["used"] += used
            out.append({"TimePeriod": {"Start": b0.isoformat(), "End": b1.isoformat()}, "Utilization": _util(tot, used)})
        return {"SavingsPlansUtilizationsByTime": out, "Total": {"Utilization": _util(T["total"], T["used"])}}


def _util(tot, used):
    return {"TotalCommitment": f"{tot:.2f}", "UsedCommitment": f"{used:.2f}", "UnusedCommitment": f"{tot - used:.2f}",
            "UtilizationPercentage": f"{(100 * used / tot) if tot else 0:.2f}"}


class Tagging:
    def __init__(self, w):
        self.w = w

    def GetResources(self, req):
        acct, region = self.w.account_id, self.w.region
        items = [(f"arn:aws:ec2:{region}:{acct}:instance/{i['id']}", i["tags"]) for i in self.w.instances]
        items += [(f"arn:aws:ec2:{region}:{acct}:volume/{v['id']}", v.get("tags", {})) for v in self.w.raw["volumes"]]
        wanted = {f["Key"]: f.get("Values") for f in req.get("TagFilters", [])}
        out = []
        for arn, tags in items:
            if all(k in tags and (not vals or tags[k] in vals) for k, vals in wanted.items()):
                out.append({"ResourceARN": arn, "Tags": _tags(tags)})
        return {"ResourceTagMappingList": out, "PaginationToken": ""}


class SavingsPlans:
    def __init__(self, w):
        self.w = w

    def DescribeSavingsPlans(self, req):
        return {"savingsPlans": [
            {"savingsPlanId": sp["id"], "savingsPlanArn": f"arn:aws:savingsplans::{self.w.account_id}:savingsplan/{sp['id']}",
             "savingsPlanType": sp["type"], "ec2InstanceFamily": sp["family"], "region": self.w.region,
             "commitment": f"{sp['commitment_hourly']:.2f}", "currency": "USD", "state": "active",
             "start": sp["start"] + "T00:00:00Z", "end": sp["end"] + "T00:00:00Z",
             "paymentOption": "No Upfront", "termDurationInSeconds": 31536000}
            for sp in self.w.raw["savings_plans"]]}


class ApiError(Exception):
    def __init__(self, status, code, message):
        super().__init__(message)
        self.status, self.code, self.message = status, code, message


# ---- HTTP -------------------------------------------------------------------
class Handler(BaseHTTPRequestHandler):
    server_version = "test-aws-server/0.1"
    log_file = None

    def log_message(self, *a):
        pass

    def _send(self, status, body, ctype):
        data = body.encode()
        self.send_response(status)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("x-amzn-RequestId", "fake-request-id")
        self.end_headers()
        self.wfile.write(data)

    def _record(self, service, op, status):
        if self.log_file:
            with open(self.log_file, "a") as f:
                f.write(json.dumps({"ts": time.time(), "service": service, "op": op, "status": status}) + "\n")

    def do_GET(self):
        if self.path == "/health":
            return self._send(200, '{"ok": true}', "application/json")
        self._send(404, "{}", "application/json")

    def do_POST(self):
        w = load()
        raw = self.rfile.read(int(self.headers.get("Content-Length", 0))).decode()
        target = self.headers.get("X-Amz-Target")
        try:
            if target:
                prefix, op = target.split(".", 1)
                service = JSON_TARGETS.get(prefix)
                impl = {"ce": Ce, "resourcegroupstaggingapi": Tagging}.get(service)
                self._guard(service, op, impl)
                body = getattr(impl(w), op)(json.loads(raw or "{}"))
                self._record(service, op, 200)
                return self._send(200, json.dumps(body), "application/x-amz-json-1.1")
            if self.path.startswith("/DescribeSavingsPlans"):
                self._record("savingsplans", "DescribeSavingsPlans", 200)
                return self._send(200, json.dumps(SavingsPlans(w).DescribeSavingsPlans(json.loads(raw or "{}"))), "application/json")
            params = {k: v[0] for k, v in parse_qs(raw).items()}
            op = params.get("Action", "")
            service = QUERY_VERSIONS.get(params.get("Version", ""), "ec2")
            self._guard(service, op, Ec2)
            body = getattr(Ec2(w), op)(params)
            self._record(service, op, 200)
            return self._send(200, to_xml(service, op, body), "text/xml")
        except ApiError as e:
            self._record(locals().get("service"), locals().get("op"), e.status)
            self._error(e, locals().get("service"))

    def _guard(self, service, op, impl):
        if not READ_OP.match(op or ""):
            raise ApiError(403, "UnauthorizedOperation", f"You are not authorized to perform: {op}. This test account is read-only.")
        if impl is None or not hasattr(impl, op):
            raise ApiError(400, "InvalidAction", f"test-aws-server does not implement {service}:{op}")

    def _error(self, e, service):
        if service in ("ce", "resourcegroupstaggingapi"):
            return self._send(e.status, json.dumps({"__type": e.code, "message": e.message}), "application/x-amz-json-1.1")
        if service == "ec2" or service is None:
            return self._send(e.status, f"<Response><Errors><Error><Code>{e.code}</Code><Message>{escape(e.message)}</Message>"
                                        f"</Error></Errors><RequestID>fake</RequestID></Response>", "text/xml")
        return self._send(e.status, f"<ErrorResponse><Error><Type>Sender</Type><Code>{e.code}</Code><Message>{escape(e.message)}</Message>"
                                    f"</Error><RequestId>fake</RequestId></ErrorResponse>", "text/xml")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=4566)
    ap.add_argument("--log", help="append one JSON line per API call")
    ap.add_argument("--world", help="world file (full world or scenario overlay); default testenv/world.yaml")
    a = ap.parse_args(argv)
    use_world(a.world)
    Handler.log_file = a.log
    load()
    srv = ThreadingHTTPServer((a.host, a.port), Handler)
    print(f"test-aws-server listening on http://{a.host}:{a.port}", file=sys.stderr, flush=True)
    srv.serve_forever()


if __name__ == "__main__":
    main()
