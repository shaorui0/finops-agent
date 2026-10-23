# 0001-requirements-v2 博客笔记

- 接真实账号之前先装闸：第一行业务代码之前，先写的是"它不能做什么"。
- 只读有两层：hook 管 agent，IAM 管所有人。hook 只看得见 Bash，boto3 直连它看不见，所以真正的保证必须在 AWS 侧。
- 读操作也会泄密：`get-secret-value`、`ssm get-parameter --with-decryption` 名字是 get，实际是外泄面。按动词放行之外还要一张 deny 表。
- fail-closed：`bash -c`、`eval`、`xargs`、`$( )` 包着的 aws 一律拒绝。看不懂就拒，而不是看不懂就放。
- 可见性缺口的两步法：先问"该看哪些 metric"，再查"系统里有没有"。差集本身就是一份 FinOps 发现。
- 小坑：OpenSpec 的 change 名必须字母开头，`0001-xxx` 会被拒，改成 `c0001-xxx`。
