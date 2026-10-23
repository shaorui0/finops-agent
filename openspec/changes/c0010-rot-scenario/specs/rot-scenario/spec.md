## ADDED Requirements

### Requirement: Selectable world
Both test servers SHALL accept `--world <path>`; without it they SHALL serve `testenv/world.yaml` unchanged.

#### Scenario: Default
- **WHEN** a server starts without `--world`
- **THEN** its responses, cost lines and ground truth are identical to before this change

#### Scenario: Overlay
- **WHEN** `--world` names a file with `scenario.base`
- **THEN** the served world is the base world with that file's set / remove / patch / add applied, and an overlay that names a missing or duplicate id is rejected

### Requirement: Next-month scenario with its own ground truth
`testenv/scenarios/next_month.yaml` SHALL describe 2026-10 in which at least one base finding is gone and at least one new finding exists; `scenario.expect` SHALL list the finding keys (`type|sorted resources`) per lifecycle state.

#### Scenario: Two periods
- **WHEN** the agent runs on the base world then on next_month with one state file
- **THEN** the second diff equals `scenario.expect` (resolved >= 1, new >= 1)

### Requirement: Regression needs a third period
`testenv/scenarios/month_after.yaml` SHALL bring back a key resolved in next_month, so a third run shows `regressed >= 1`.

#### Scenario: Three periods
- **WHEN** a third run on month_after follows the second
- **THEN** its diff equals `scenario.expect` with regressed >= 1, resolved >= 1, new >= 1

### Requirement: One-command demo
`scripts/rot_demo.sh` SHALL run the three periods against ports 16566 / 16990 with a throw-away state file and print each diff.

#### Scenario: Run
- **WHEN** `bash scripts/rot_demo.sh` is run
- **THEN** it exits 0, leaves no processes or state behind, and prints resolved / regressed / new keys
