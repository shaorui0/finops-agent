## ADDED Requirements

### Requirement: Goal-first visibility requirements
Ring 1 SHALL derive the required visibility from cost goals: for each cost objective, name the SLI that measures it and the SLO target, before looking at any existing metric.

#### Scenario: Requirements produced without inspecting the system
- **WHEN** ring 1 runs
- **THEN** it outputs `visibility_requirements` listing objective → SLI → SLO, and has made no metric queries

### Requirement: Metric search is a planned task
Ring 2 SHALL produce a search plan (which data source, which query, what counts as found) for every SLI from ring 1, and ring 3 SHALL execute exactly that plan.

#### Scenario: Plan precedes search
- **WHEN** ring 3 starts
- **THEN** a ring-2 plan file exists and every query ring 3 runs is listed in it

#### Scenario: Search results carry evidence
- **WHEN** ring 3 reports a metric as found or missing
- **THEN** the report includes the query that was run and its raw result

### Requirement: Metric-to-SLI adequacy
Ring 4 SHALL judge, for each SLI, whether the found metrics can compute it, and output a gap table.

#### Scenario: Gap table rows are traceable
- **WHEN** the gap table is produced
- **THEN** every row names the SLI it serves and links to the ring-3 evidence
