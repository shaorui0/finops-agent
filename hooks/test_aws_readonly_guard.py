import json
import subprocess
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from aws_readonly_guard import check  # noqa: E402

HOOK = Path(__file__).parent / "aws_readonly_guard.py"

ALLOWED = [
    "ls -la",
    "echo awsome",
    "aws sts get-caller-identity",
    "aws --profile finops-ro ec2 describe-instances --region us-east-1",
    "aws ce get-cost-and-usage --time-period Start=2026-09-01,End=2026-10-01 --granularity MONTHLY --metrics UnblendedCost",
    "aws cloudwatch get-metric-statistics --namespace AWS/EC2 --metric-name CPUUtilization",
    "aws s3 ls s3://bucket/",
    "aws --output=json rds describe-db-instances | jq .",
    "aws ec2 describe-volumes && aws elbv2 describe-load-balancers",
    "/usr/local/bin/aws resourcegroupstaggingapi get-resources",
    "aws help",
    "aws ec2 help",
]

BLOCKED = [
    "aws ec2 terminate-instances --instance-ids i-1",
    "aws ec2 describe-instances; aws ec2 stop-instances --instance-ids i-1",
    "aws s3 rm s3://bucket/key",
    "aws s3 cp a s3://bucket/",
    "aws s3 sync . s3://bucket/",
    "aws --profile x iam create-user --user-name y",
    "aws ec2 create-tags --resources i-1 --tags Key=a,Value=b",
    "aws autoscaling set-desired-capacity --auto-scaling-group-name g --desired-capacity 0",
    "aws secretsmanager get-secret-value --secret-id s",
    "aws ssm get-parameter --name p --with-decryption",
    "aws configure set aws_access_key_id X",
    "bash -c 'aws ec2 terminate-instances --instance-ids i-1'",
    "eval aws ec2 terminate-instances",
    "echo i-1 | xargs aws ec2 terminate-instances --instance-ids",
    "$(echo aws) ec2 terminate-instances",
    "aws ec2",
    "aws 'unterminated",
]


class GuardTest(unittest.TestCase):
    def test_allowed(self):
        for cmd in ALLOWED:
            with self.subTest(cmd=cmd):
                self.assertIsNone(check(cmd))

    def test_blocked(self):
        for cmd in BLOCKED:
            with self.subTest(cmd=cmd):
                self.assertIsNotNone(check(cmd))

    def test_hook_protocol(self):
        def run(cmd, tool="Bash"):
            payload = json.dumps({"tool_name": tool, "tool_input": {"command": cmd}})
            return subprocess.run([sys.executable, str(HOOK)], input=payload, capture_output=True, text=True)

        self.assertEqual(run("aws ec2 describe-instances").returncode, 0)
        blocked = run("aws ec2 terminate-instances --instance-ids i-1")
        self.assertEqual(blocked.returncode, 2)
        self.assertIn("BLOCKED", blocked.stderr)
        self.assertEqual(run("aws ec2 terminate-instances", tool="Read").returncode, 0)


if __name__ == "__main__":
    unittest.main()
