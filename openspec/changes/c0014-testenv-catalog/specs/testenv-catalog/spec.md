## ADDED Requirements

### Requirement: Five-part ground truth
Every `ground_truth` finding and trap, and every entry in `scenario.expect.details`, SHALL carry non-empty `status`, `spec`, `diff`, `runbook` (an ordered list) and `prevention`.

#### Scenario: Completeness
- **WHEN** `python3 -m unittest testenv.test_catalog` runs
- **THEN** all 12 findings, 4 traps and every scenario expectation have the five fields, and every `alert:<Name>` in a `prevention` exists in `config/alerts/finops.rules.yml`

### Requirement: Numbers are computed
Numbers in the five fields SHALL come from placeholders resolved against `testenv.world.load()`, not from literals.

#### Scenario: No literal money
- **WHEN** the raw text of `status`, `spec`, `diff` is scanned
- **THEN** it contains no literal `$<digits>`, and every placeholder resolves

### Requirement: Catalog page
`python3 -m testenv.catalog --out <file>` SHALL write one self-contained HTML file (inline CSS with light and dark tokens, no external scripts) with an overview table, one card per finding, a traps section, a rot timeline and the visibility gaps.

#### Scenario: Contents
- **WHEN** the page is generated
- **THEN** it contains every GT and TR id, and the base world's `lines` are unchanged (sha256 of `json.dumps(World.lines)` before and after)
