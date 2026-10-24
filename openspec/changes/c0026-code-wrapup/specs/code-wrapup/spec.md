## ADDED Requirements

### Requirement: Docs link check
With `--docs`, `tools/check_rules.py` SHALL fail on every relative markdown link (relative to the file) and backticked repo path (relative to the repo root) that does not resolve in README.md, CONTRIBUTING.md, docs/**/*.md, rules/**/*.md, testenv/README.md and eval/EXPERIMENTS.md, reporting file:line. http(s) links, pure anchors, runs/ paths, paths containing < > or *, and the openspec/ tree SHALL be ignored.

#### Scenario: Dangling link
- **WHEN** a doc contains a link to a missing file
- **THEN** the check reports `<file>:<line>` and exits 1

### Requirement: Heading language check
With `--docs`, a heading that, after removing backticked spans, has at least 2 ASCII words of 2 or more letters and no CJK character SHALL fail with file:line.

#### Scenario: English heading
- **WHEN** a doc has the heading `## Waste budget`
- **THEN** the check reports its file:line

### Requirement: make test runs every test module
`make test` SHALL run every `test_*.py` under finops_agent, eval, testenv, tools and hooks, and pass with its ports free.

### Requirement: Explicit snapshot
`slo.diff_state` SHALL receive the snapshot as an argument; `slo.py` SHALL hold no module-level snapshot state. Behavior is unchanged.

### Requirement: not_redetected in the report
The SLO section of report.html SHALL show the `not_redetected` count and list, with the reason 资源仍在，但本次未再检出.
