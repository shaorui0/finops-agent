## ADDED Requirements

### Requirement: A scenario chain with real deviations
The repository SHALL provide `testenv/scenarios/verify_base.yaml`, `verify_month1.yaml`, `verify_month2.yaml` (overlays on the base world) in which realized savings genuinely differ from predicted savings, without changing the base world or any existing scenario.

#### Scenario: Base output unchanged
- **WHEN** the world features `deleted`, `uptime` and gp3 `iops`/`throughput` are added to `testenv/world.py`
- **THEN** the sha256 of `World.lines` for the base world, `next_month.yaml` and `month_after.yaml` is identical before and after

### Requirement: Deviations classified by cause
For every verified item the verifier SHALL report predicted savings, realized savings, realization rate, first-month cash realization rate, next-month cash realization rate, a cause class and a conclusion. The cause classes are commitment absorption, usage drift (control-group correction), prediction-basis difference and part-month proration.

#### Scenario: Mid-period deletion
- **WHEN** a resource is deleted in the middle of period N+1
- **THEN** the standard-month realization is 100%, the first-month cash realization equals billed-free days over period days, the next month is 100%, and the cause class is proration

#### Scenario: Commitment absorption
- **WHEN** a resolved item stops usage that a Savings Plan covers and the plan is under-used
- **THEN** the unblended realized saving is 0 although the on-demand prediction is positive, the amortized saving equals the growth of the plan's unused commitment, and the cause class is commitment absorption

#### Scenario: Usage growth in the stratum
- **WHEN** untouched resources of the same stratum grow while the treated resource is changed
- **THEN** the naive saving and the adjusted saving differ, the document shows both, and the cause class is usage drift

#### Scenario: List-price basis
- **WHEN** a gp2-to-gp3 prediction made at list price meets a bill that carries provisioned IOPS and throughput
- **THEN** the shortfall equals the new IOPS and throughput usage types and the cause class is prediction-basis difference

### Requirement: Claims are not agent findings
A scenario-declared claim SHALL be verified like a finding but listed with source `claim`, never added to the agent's state diff, and reported separately from the agent-only portfolio.

#### Scenario: Dev schedule claim
- **WHEN** claim C01 (on-demand price x idle hours of three Savings-Plan-covered instances) is applied in period N+1
- **THEN** C01 appears with source `claim`, is absent from the agent's resolved list, and the portfolio shows an agent-only row

### Requirement: Design-value reconciliation
The document SHALL compare each deviation item's realized saving with a value computed from the world spec and price table only, and every difference SHALL be within one cent.

#### Scenario: Four deviations
- **WHEN** the scenario chain is verified
- **THEN** the design values for proration, absorption, drift-corrected saving and IOPS-and-throughput saving each match the verifier within one cent

### Requirement: Primary evidence and null control in one document
`docs/SAVINGS_VERIFICATION.md` SHALL present the scenario chain as primary evidence and keep the c0018 chain as a null-hypothesis control that explains why 100% is expected there. Every number SHALL come from code and two runs SHALL produce identical text.

#### Scenario: Determinism
- **WHEN** both chains are collected twice
- **THEN** the generated Markdown is byte-identical

#### Scenario: Portfolio
- **WHEN** the scenario chain is verified
- **THEN** total realized savings are below total predicted savings and the bill decomposition still sums exactly to the bill delta

## MODIFIED Requirements

### Requirement: Exact bill decomposition
The bill delta between consecutive periods SHALL equal the sum of verified savings, regression loss, new waste, calendar/proration effect, usage drift, carry-over of earlier part-month savings, other removed and other new, with zero difference in exact rational arithmetic.

#### Scenario: Two chains
- **WHEN** the verifier runs on the scenario chain and on the control chain
- **THEN** every decomposition has sum == delta
