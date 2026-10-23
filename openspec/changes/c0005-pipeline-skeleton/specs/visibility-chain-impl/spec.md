## ADDED Requirements

### Requirement: Ring outputs are persisted
A run SHALL write `visibility.json` with the ring-1 requirements, ring-2 plan, ring-3 search results (including each query) and ring-4 gaps.

#### Scenario: Plan precedes search
- **WHEN** `visibility.json` is read
- **THEN** every ring-3 result id matches a ring-2 plan step

### Requirement: Gap status is scope-aware
Ring 4 SHALL mark a signal `covered` only when every expected scope value (instance, gateway or service) has a series; otherwise `partial` or `missing`.

#### Scenario: Planted gaps
- **WHEN** the pipeline runs against testenv
- **THEN** `rightsizing_headroom` and `unit_cost_per_job` are `missing` and `cross_az_attribution` is `partial`
