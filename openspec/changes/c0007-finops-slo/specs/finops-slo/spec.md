## ADDED Requirements

### Requirement: SLIs every run
Each run SHALL compute the SLIs defined in `config/finops_slo.yaml`, evaluate them against their targets, and record each value with the evidence it came from; an SLI that cannot be computed SHALL be `no_data`, not omitted.

#### Scenario: Neglected account
- **WHEN** the pipeline runs against testenv
- **THEN** waste_ratio, commitment_utilization, useful_work_ratio, anomaly_time_to_detect_days and orphan_max_age_days are `violated`, and anomaly_time_to_detect_days is 27

### Requirement: Rot detection across runs
The pipeline SHALL keep cross-run state and classify each finding as new, persisting, resolved or regressed, where regressed means a finding that a previous run marked resolved has reappeared.

#### Scenario: Regression
- **WHEN** a finding disappears in run 2 and reappears in run 3
- **THEN** run 3 reports it as regressed with the run in which it was resolved

### Requirement: Metrics export
Each run SHALL write `finops_metrics.prom` in Prometheus text format including `finops_sli`, `finops_slo_target`, `finops_findings`, `finops_waste_usd`, `finops_waste_budget_usd` and `finops_last_run_timestamp_seconds`.

#### Scenario: Valid exposition
- **WHEN** `promtool check metrics` reads the file
- **THEN** it exits 0
