# c0001 验收证据

## 3.1 单元测试
```
test_allowed (hooks.test_aws_readonly_guard.GuardTest.test_allowed) ... ok
test_blocked (hooks.test_aws_readonly_guard.GuardTest.test_blocked) ... ok
test_hook_protocol (hooks.test_aws_readonly_guard.GuardTest.test_hook_protocol) ... ok

----------------------------------------------------------------------
Ran 3 tests in 0.073s

OK
```

## 3.2 按注册命令行调用 hook
```
$ aws ec2 terminate-instances --instance-ids i-1
[aws_readonly_guard] BLOCKED: aws ec2 terminate-instances is not a read-only operation. This project is read-only against AWS.
exit=2
$ aws ce get-cost-and-usage
exit=0
$ bash -c 'aws s3 rm s3://b/k'
[aws_readonly_guard] BLOCKED: aws inside a sub-shell cannot be verified. This project is read-only against AWS.
exit=2
```

## 3.3 openspec validate
```
Change 'c0001-requirements-v2' is valid
```

## 3.4 敏感信息扫描
```
matches-exit=1 (1 = 无命中)
```
