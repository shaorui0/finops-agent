## ADDED Requirements

### Requirement: Protocol compatible
The server SHALL answer boto3 and the aws CLI unmodified when given `endpoint_url`, for EC2, Auto Scaling, STS, Cost Explorer, Resource Groups Tagging and Savings Plans read operations.

#### Scenario: boto3 round trip
- **WHEN** boto3 calls `ec2.describe_instances()` against the server
- **THEN** it returns every instance in world.yaml with its tags and state

### Requirement: Read-only
The server SHALL reject any operation whose name is not a read verb with `UnauthorizedOperation`.

#### Scenario: Write rejected
- **WHEN** a client calls `TerminateInstances`
- **THEN** the call fails with error code `UnauthorizedOperation`

### Requirement: Realistic Cost Explorer limits
`GetCostAndUsage` SHALL reject `RESOURCE_ID` grouping, and `GetCostAndUsageWithResources` SHALL reject periods longer than 14 days.

#### Scenario: Resource-level window
- **WHEN** a client asks for 30 days of resource-level cost
- **THEN** it receives `DataUnavailableException`
