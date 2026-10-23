## ADDED Requirements

### Requirement: Contributor docs match the code
`CONTRIBUTING.md` and `docs/ARCHITECTURE.md` SHALL describe only what the current code does, and every relative link and repo path they cite SHALL exist.

#### Scenario: Link check
- **WHEN** a script extracts relative links and backticked repo paths from both files
- **THEN** each one resolves to an existing file or directory, except generated `runs/` paths

#### Scenario: Artifact fields
- **WHEN** the pipeline runs once against the test environment
- **THEN** the field lists documented for each artifact match the keys in the produced files

### Requirement: In-progress work is not specified
Features under development in other changes SHALL be marked as in progress, without interface details.

#### Scenario: Judgment layer
- **WHEN** `docs/ARCHITECTURE.md` mentions the judgment layer or remediation plans
- **THEN** it labels them as in progress and describes no fields or commands for them
