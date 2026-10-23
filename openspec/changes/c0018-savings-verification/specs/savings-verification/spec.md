## ADDED Requirements

### Requirement: Realized savings per resolved finding
For every finding that period N+1 reports as resolved, the verifier SHALL report predicted savings, counterfactual cost, actual cost, realized savings and realization rate, all in 30-day standard-month dollars, from Cost Explorer data of each period.

#### Scenario: Deletion
- **WHEN** an unattached volume or idle EIP is resolved by removing the resource
- **THEN** realized savings equals its N-period daily cost x 30 within 2%, and the row is marked as realized

#### Scenario: Reverted change
- **WHEN** a resolved finding returns as regressed in period N+2
- **THEN** realized savings in N+1 is positive, retained savings in N+2 is zero, and the final verdict is "realized then lost"

### Requirement: Counterfactual baseline with a control group
Realized savings SHALL be measured against N-period daily cost moved by the drift of untouched control resources of the same usage-type stratum, not against the raw N-period invoice.

#### Scenario: Usage drift
- **WHEN** control resources of the stratum change usage between periods
- **THEN** the naive saving and the adjusted saving differ by exactly that drift, and a decline in usage does not inflate the saving

### Requirement: Exact bill decomposition
The bill delta between consecutive periods SHALL equal the sum of verified savings, regression loss, new waste, calendar/proration effect, usage drift, other removed and other new, with zero difference in exact rational arithmetic.

#### Scenario: Three periods
- **WHEN** the verifier runs on the base world, next_month and month_after
- **THEN** both decompositions have sum == delta

### Requirement: Generated document
`python3 -m finops_agent.verify_savings --out-md ... --out-html ...` SHALL produce the Chinese document and HTML page; every number in them comes from code, and two runs produce identical text.

#### Scenario: Determinism
- **WHEN** the command runs twice
- **THEN** the Markdown output is byte-identical
