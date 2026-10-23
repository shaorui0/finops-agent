"""Prevention: finding type -> preventive controls.

Fixing a finding once is a cleanup; the control below is what stops it from coming back (the
`regressed` state in docs/FINOPS_SLO.md). Each entry names, in this order, the control a
platform team would put in place (lifecycle policy, tag policy/SCP, AWS Config rule,
launch-template / Terraform change), the alert rules that watch for it (they must exist in
config/alerts/finops.rules.yml; a test asserts that) and the review cadence from the Cadence
table in docs/FINOPS_SLO.md. Data only; nothing here touches AWS.
"""
from __future__ import annotations

from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
RULES_FILE = ROOT / "config" / "alerts" / "finops.rules.yml"

DAILY = "每日巡检看 {sli}（docs/FINOPS_SLO.md Cadence 每日）"
WEEKLY = "每周看 {sli}（docs/FINOPS_SLO.md Cadence 每周）"
MONTHLY = "每月{what}（docs/FINOPS_SLO.md Cadence 每月）"

PREVENTION = {
    "unattached_volume": {
        "controls": ["启动模板 / Terraform 里卷设 DeleteOnTermination=true，迁移任务的临时卷同样",
                     "tag policy 要求 owner 与 expire-on；SCP 拒绝创建缺这两个 tag 的卷",
                     "AWS Config 规则 ec2-volume-inuse-check 标记长期 available 的卷"],
        "alerts": ["FinOpsSLOViolated"], "cadence": WEEKLY.format(sli="orphan_max_age_days")},
    "idle_public_ip": {
        "controls": ["AWS Config 规则 eip-attached 标记未关联的 Elastic IP",
                     "tag policy 要求 Elastic IP 带 owner；Terraform 里 EIP 与它的资源同模块、同生命周期"],
        "alerts": ["FinOpsSLOViolated"], "cadence": WEEKLY.format(sli="orphan_max_age_days")},
    "stopped_instance_storage": {
        "controls": ["SCP 与 tag policy 强制 owner、env tag，缺失则拒绝创建",
                     "AWS Config 规则 ec2-stopped-instance（allowedDays 设 30）标记超期停机实例",
                     "停机超过 30 天的实例走终止流程：先做 AMI，再终止，卷随实例删除"],
        "alerts": ["FinOpsSLOViolated"], "cadence": WEEKLY.format(sli="attribution_coverage 与 orphan_max_age_days")},
    "orphan_snapshots": {
        "controls": ["删卷流程里同步移除 DLM（Data Lifecycle Manager）lifecycle policy 的目标 tag，避免继续生成快照",
                     "AMI 清理用 EC2 Image Builder 或 DLM 的 AMI 策略，按「未被任何启动模板引用且超过保留期」判定",
                     "快照设置保留期（lifecycle policy 的 RetainRule），不无限保留"],
        "alerts": ["FinOpsSLOViolated"], "cadence": WEEKLY.format(sli="orphan_max_age_days")},
    "gp2_to_gp3": {
        "controls": ["先改 Terraform 再改现网，否则下次 terraform apply 会改回 gp2",
                     "Terraform 模块默认 gp3；自定义 AWS Config 规则（或 SCP 条件 ec2:VolumeType）禁止新建 gp2"],
        "alerts": ["FinOpsRegression"], "cadence": WEEKLY.format(sli="regressed 列表")},
    "savings_plan_underutilized": {
        "controls": ["换实例家族的迁移，变更模板必须有「承诺影响」检查项（launch template / Terraform 变更评审清单）",
                     "新购优先 Compute Savings Plan，购买走审批；禁止用 SCP 之外的角色购买"],
        "alerts": ["FinOpsSLOViolated"], "cadence": MONTHLY.format(what="关账后评审 commitment_utilization")},
    "misattributed_tags": {
        "controls": ["launch template 的 TagSpecifications 固化 service 与 owner，SCP 禁止手改 owner",
                     "AWS Config 规则 required-tags 检查 service、owner、env",
                     "tag 内容当不可信数据处理，不当指令"],
        "alerts": ["FinOpsSLOViolated"], "cadence": WEEKLY.format(sli="attribution_coverage")},
    "nat_path_cost": {
        "controls": ["Terraform 的 VPC 模块默认创建 S3 gateway endpoint 并关联私有路由表",
                     "自定义 AWS Config 规则检查每个带私有子网的 VPC 都有 S3 gateway endpoint",
                     "任务失败率与重试量进告警，不靠账单发现"],
        "alerts": ["NatBytesSurge", "RetryStorm"], "cadence": DAILY.format(sli="anomaly_time_to_detect_days")},
    "cross_az_traffic": {
        "controls": ["延迟敏感依赖在服务评审里写明 AZ 亲和；ASG 的子网覆盖多个 AZ 并均衡（launch template / Terraform）",
                     "读流量走同 AZ 副本，跨 AZ 只用于容灾复制"],
        "alerts": ["FinOpsSLOViolated"], "cadence": MONTHLY.format(what="架构级 finding 评审")},
    "busy_but_useless": {
        "controls": ["删除队列前必须先查消费者，写进变更评审清单",
                     "任务成功率进 SLO（useful_work_ratio），重试上限与退避写进 worker 的 Terraform / 模板配置"],
        "alerts": ["BusyButUselessFleet", "RetryStorm"], "cadence": DAILY.format(sli="useful_work_ratio")},
    "always_on_batch": {
        "controls": ["批处理标准模板默认临时运行（EventBridge Scheduler 或 Batch），常驻批处理主机要在评审里登记理由",
                     "tag policy 要求 workload-type（batch / service），Config 规则检查 batch 类型的常驻实例"],
        "alerts": ["FinOpsWasteSlowBurn"], "cadence": MONTHLY.format(what="架构级评审")},
    "schedulable_idle": {
        "controls": ["dev 环境的 launch template / Terraform 模块默认带启停计划（ASG scheduled action 或 Instance Scheduler）",
                     "评审清单固定先看承诺利用率，再算停机收益"],
        "alerts": ["DevEnvironmentIdleRunning"], "cadence": WEEKLY.format(sli="waste_ratio 与 dev 环境清单")},
}

DEFAULT = {
    "controls": ["为这类 finding 补一条控制：tag policy / SCP、AWS Config 规则或 Terraform 默认值（评审时选定）"],
    "alerts": ["FinOpsRegression"], "cadence": WEEKLY.format(sli="regressed 列表")}


def for_type(t: str) -> dict:
    return PREVENTION.get(t, DEFAULT)


def alert_names() -> set:
    rules = yaml.safe_load(RULES_FILE.read_text())
    return {r["alert"] for g in rules["groups"] for r in g["rules"] if "alert" in r}


def render_text(t: str) -> str:
    """Same shape as testenv ground_truth prevention: 控制 / 告警 / 节奏."""
    p = for_type(t)
    return "\n".join([*(f"控制：{c}" for c in p["controls"]),
                      "告警：" + "、".join(f"alert:{a}" for a in p["alerts"]),
                      f"节奏：{p['cadence']}"])
