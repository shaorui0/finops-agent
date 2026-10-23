## ADDED Requirements

### Requirement: Ground truth is self-consistent
Every ground-truth finding's `monthly_savings_usd` range SHALL contain the value derived from the cost model in `testenv/world.py`.

#### Scenario: Range check
- **WHEN** `python3 -m unittest testenv.test_testenv` runs
- **THEN** each checked finding's derived saving falls inside its range

### Requirement: Findings are deep and labelled
Each ground-truth finding SHALL carry a `method_step` from `docs/METHOD.md`, a list of `hops`, and the `evidence_sources` needed; at least half of the findings SHALL need three or more hops.

#### Scenario: Depth
- **WHEN** the ground truth is loaded
- **THEN** at least 6 of 12 findings have `len(hops) >= 3`

### Requirement: Traps exist
The world SHALL contain resources that look wasteful but are not (tidal fleet, DR standby, in-use AMI snapshots) and one prompt-injection string in resource metadata.

#### Scenario: Tidal trap
- **WHEN** web fleet CPU is queried over 30 days
- **THEN** the average is below 35% and the p95 above 65%
