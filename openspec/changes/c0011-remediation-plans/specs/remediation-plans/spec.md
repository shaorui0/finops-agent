## ADDED Requirements

### Requirement: Every saving has a plan
Every finding with `monthly_savings_usd > 0` SHALL produce a plan carrying steps (command text), reversal cost with reason, rollback, preconditions, owner and evidence.

#### Scenario: Fixture run
- **WHEN** plans are built from a real `findings.json`
- **THEN** each finding with savings has a plan with all of those fields

### Requirement: Reversal cost gates the output
Deleting a volume or instance SHALL be preceded by a backup step; irreversible deletions of snapshots SHALL NOT appear as commands; commitments SHALL have advice only and no commands (FA06).

#### Scenario: Commitment
- **WHEN** the finding is a Savings Plan finding
- **THEN** the plan is `advice_only` with empty steps and `reversal_cost` high

### Requirement: Method order
Plans SHALL be ordered delete, then downsize, then commit.

#### Scenario: Ordering
- **WHEN** plans.json is written
- **THEN** M3 plans precede M4 plans, which precede M5 plans

### Requirement: Nothing executes
The module SHALL NOT execute any command. `apply` SHALL refuse without `--approve <plan_id>` and, with it, SHALL only print or write a script.

#### Scenario: No approval
- **WHEN** `apply plans.json` is run with no `--approve`
- **THEN** it exits non-zero and prints no commands
