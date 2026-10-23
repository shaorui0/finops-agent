## ADDED Requirements

### Requirement: Read-only AWS CLI
The project hook SHALL allow an AWS CLI call only when its operation is a read verb (`describe-*`, `get-*`, `list-*`, `lookup-*`, `search-*`, `batch-get-*`, `head-*`) or on an explicit allowlist (`s3 ls`, `sts get-caller-identity`, `configure list`).

#### Scenario: Read call passes
- **WHEN** the agent runs `aws ce get-cost-and-usage ...`
- **THEN** the hook exits 0

#### Scenario: Write call blocked
- **WHEN** the agent runs `aws ec2 terminate-instances ...` or `aws s3 rm ...`
- **THEN** the hook exits 2 and prints the reason to stderr

### Requirement: Secret-reading verbs blocked
The hook SHALL block read verbs that return secrets or credentials (e.g. `secretsmanager get-secret-value`, `ssm get-parameter`, `ssm --with-decryption`).

#### Scenario: Secret read blocked
- **WHEN** the agent runs `aws secretsmanager get-secret-value --secret-id s`
- **THEN** the hook exits 2

### Requirement: Fail closed
The hook SHALL block any command that mentions `aws` but cannot be verified: command substitution, `eval`, `xargs`, `sh -c`, unparseable quoting, or a missing operation.

#### Scenario: Wrapped write blocked
- **WHEN** the agent runs `bash -c 'aws ec2 terminate-instances ...'`
- **THEN** the hook exits 2
