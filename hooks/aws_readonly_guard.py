#!/usr/bin/env python3
"""PreToolUse hook: allow only read-only AWS CLI calls from the agent.

Layer 1 of 2. It sees Bash commands only; SDK calls and humans are covered by
AWS-side IAM (docs/aws_account_hardening.md). Fails closed: if a command
mentions aws and cannot be parsed, it is blocked.

Exit 0 = allow, exit 2 = block (stderr is shown to the agent).
"""
import json
import re
import shlex
import sys

READ_OP = re.compile(r"^(describe|get|list|lookup|search|batch-get|head)-")

# Read verbs that still leak secrets.
DENY_OPS = {
    ("secretsmanager", "get-secret-value"),
    ("secretsmanager", "batch-get-secret-value"),
    ("ssm", "get-parameter"),
    ("ssm", "get-parameters"),
    ("ssm", "get-parameters-by-path"),
    ("ec2", "get-password-data"),
    ("kms", "get-key-policy"),
    ("ecr", "get-login-password"),
    ("ecr", "get-authorization-token"),
    ("sts", "get-session-token"),
    ("sts", "get-federation-token"),
    ("iam", "get-credential-report"),
    ("lambda", "get-function"),  # returns a presigned code URL
}

ALLOW_OPS = {
    ("s3", "ls"),
    ("sts", "get-caller-identity"),
    ("configure", "list"),
    ("configure", "list-profiles"),
}

# Global options that take a value.
VALUE_OPTS = {
    "--profile", "--region", "--output", "--query", "--endpoint-url",
    "--color", "--cli-read-timeout", "--cli-connect-timeout", "--ca-bundle",
}

SEPARATORS = re.compile(r"&&|\|\||[;|\n&]")


def check_segment(tokens):
    """Return None if allowed, else a reason string."""
    idx = next((i for i, t in enumerate(tokens) if t.rsplit("/", 1)[-1] == "aws"), None)
    if idx is None:
        return None
    rest = tokens[idx + 1:]
    args = []
    i = 0
    while i < len(rest):
        t = rest[i]
        if t in VALUE_OPTS:
            i += 2
            continue
        if t.startswith("--") and "=" in t and t.split("=", 1)[0] in VALUE_OPTS:
            i += 1
            continue
        if t.startswith("-"):
            i += 1
            continue
        args.append(t)
        i += 1
    if not args or args[0] == "help" or (len(args) > 1 and args[1] == "help"):
        return None
    if len(args) < 2:
        return f"cannot determine operation in: aws {' '.join(rest)}"
    svc, op = args[0], args[1]
    if (svc, op) in ALLOW_OPS:
        return None
    if (svc, op) in DENY_OPS:
        return f"aws {svc} {op} reads secrets; not allowed"
    if svc == "ssm" and "--with-decryption" in rest:
        return "ssm --with-decryption not allowed"
    if READ_OP.match(op):
        return None
    return f"aws {svc} {op} is not a read-only operation"


def check(command):
    if not re.search(r"(^|[^\w-])aws([^\w-]|$)", command):
        return None
    if "$(" in command or "`" in command or re.search(r"\b(eval|xargs)\b", command):
        return "aws inside eval/xargs/command substitution cannot be verified"
    for seg in SEPARATORS.split(command):
        seg = seg.strip()
        if not seg:
            continue
        try:
            tokens = shlex.split(seg, comments=True)
        except ValueError:
            return "unparseable command mentioning aws"
        if tokens and tokens[0] in ("sh", "bash", "zsh") and "-c" in tokens:
            return "aws inside a sub-shell cannot be verified"
        reason = check_segment(tokens)
        if reason:
            return reason
    return None


def main():
    try:
        payload = json.load(sys.stdin)
    except json.JSONDecodeError:
        return 0
    if payload.get("tool_name") != "Bash":
        return 0
    reason = check(payload.get("tool_input", {}).get("command", ""))
    if reason:
        print(f"[aws_readonly_guard] BLOCKED: {reason}. This project is read-only against AWS.", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
