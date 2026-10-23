# AWS 侧只读加固需求（D9）

状态：**只列需求，不改 AWS**。本项目的只读是两层：

| 层 | 实现 | 挡得住 | 挡不住 |
|---|---|---|---|
| 1 项目 hook | `hooks/aws_readonly_guard.py`（PreToolUse / Bash，fail-closed） | agent 通过 Bash 发出的 aws CLI 写操作、读密钥操作 | Python/boto3 直连、别的工具、人手操作、hook 被绕过或未加载 |
| 2 AWS IAM | 下表 | 一切写操作，不论谁、用什么客户端 | 权限本身配错 |

第 2 层才是真正的保证，第 1 层负责早拦截和给 agent 可读的拒绝原因。

## 需求清单

| # | 需求 | 防的是什么 |
|---|---|---|
| H1 | agent 用的 profile 只绑一个 IAM role，挂 `ViewOnlyAccess`（不是 `ReadOnlyAccess`，后者能读 S3 对象和部分密钥） | 写操作；读到业务数据 |
| H2 | 额外挂一条 inline 允许：`ce:Get*`、`ce:Describe*`、`cur:Describe*`、`pricing:Get*`、`cloudwatch:GetMetric*`、`tag:GetResources`、`compute-optimizer:Get*` | ViewOnly 缺的成本类读权限 |
| H3 | 显式 Deny：`secretsmanager:GetSecretValue`、`ssm:GetParameter*`、`kms:Decrypt`、`s3:GetObject`（CUR 桶除外） | 读权限里的数据外泄面 |
| H4 | 用 IAM Identity Center（SSO）发短期凭证，不发长期 access key | 凭证泄漏后长期可用 |
| H5 | 理想形态：成本分析放在独立的 member account，或在 Organization 层用 SCP 兜底拒绝写操作 | role 被误改成可写 |
| H6 | 开 CloudTrail，按该 role 的 ARN 过滤，定期核对「是否出现非 Get/List/Describe 调用」 | 验证前面几条真的生效（可作为 eval 的一项） |
| H7 | 设一个 Budget 告警（例如 $5/月），覆盖 Cost Explorer API 调用费（$0.01/请求） | agent 循环调用把分析本身变成成本 |
