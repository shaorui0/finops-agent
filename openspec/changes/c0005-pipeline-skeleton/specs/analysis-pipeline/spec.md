## ADDED Requirements

### Requirement: Analyze only a frozen snapshot
Detectors SHALL read only the snapshot produced by the collector, and a run SHALL be reproducible from `snapshot.json` alone via `--snapshot`.

#### Scenario: Re-analysis
- **WHEN** `python3 -m finops_agent run --snapshot runs/<id>/snapshot.json` runs
- **THEN** it produces findings without calling AWS (visibility search still queries metrics)

### Requirement: Every finding is traceable
Each finding SHALL carry `method_step`, `hops`, at least one evidence item naming the API call or query it came from, a savings `basis`, and the resource's own spend.

#### Scenario: Evidence present
- **WHEN** a run completes
- **THEN** every finding has non-empty `evidence` and a `method_step` starting with `M`

### Requirement: Invariants are enforced
The pipeline SHALL report a violation when savings exceed resource spend, when non-zero savings have basis `none`, or when a finding has no evidence.

#### Scenario: Clean run
- **WHEN** the pipeline runs against testenv
- **THEN** `invariants` is empty

### Requirement: Judgment is not faked
Signals that need cross-source judgment SHALL be emitted as leads with open questions, not as findings with guessed savings.

#### Scenario: NAT spike
- **WHEN** `NatGateway-Bytes` daily cost rises more than 2x within the period
- **THEN** a lead names the usage type and the first day of the rise, and no finding claims a cause

### Requirement: Traps are not flagged
The deterministic detectors SHALL NOT flag the tidal web fleet, the warm DR standby, or snapshots behind in-use AMIs.

#### Scenario: Trap resources
- **WHEN** a run completes
- **THEN** none of `web-asg`, `i-0a1b2c3d4e5f60701`, `ami-ingest-v7`, `ami-web-v12` appears in any finding's resources

### Requirement: Read-only trace
Every call made during a run SHALL be recorded in `trace.jsonl`, and all of them SHALL be read operations.

#### Scenario: Trace audit
- **WHEN** `trace.jsonl` is read
- **THEN** every `op` starts with `describe_`, `get_` or `/api/v1/`
