## ADDED Requirements

### Requirement: Chinese for humans, English for protocols
Documentation and report text SHALL be Chinese; code identifiers, code comments, metric names, alert names and API fields SHALL stay English.

#### Scenario: Report
- **WHEN** a run's `report.html` is rendered
- **THEN** its section headings and table headers are Chinese, and resource IDs, usage types and metric names appear unchanged

### Requirement: No logic depends on display text
Values used by later stages SHALL be carried in structured fields, never parsed back out of human-readable strings.

#### Scenario: Anomaly start date
- **WHEN** the SLO step computes `anomaly_time_to_detect_days`
- **THEN** it reads the lead's `since` field
