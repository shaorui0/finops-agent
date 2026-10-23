## ADDED Requirements

### Requirement: Rules are tested
Alert rules SHALL pass `promtool check rules`, and the behaviour of the SLO, burn, regression, staleness and busy-but-useless alerts SHALL be covered by `promtool test rules`.

#### Scenario: CI
- **WHEN** CI runs `make alerts-test`
- **THEN** both commands succeed

### Requirement: SLO alerts are not noisy
An SLO violation SHALL alert only after persisting for one day; a regression SHALL alert immediately.

#### Scenario: Short violation
- **WHEN** commitment utilization has been below target for 12 hours
- **THEN** FinOpsSLOViolated is not firing

### Requirement: The inspector is watched
An alert SHALL fire when no inspection run has completed for more than two days.

#### Scenario: Stale
- **WHEN** `finops_last_run_timestamp_seconds` is 49 hours old
- **THEN** FinOpsInspectionStale fires
